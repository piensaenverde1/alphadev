"""Agente especialista en opciones financieras: cobertura e ingresos."""
import json
from datetime import datetime
from typing import Dict, List, Optional

from agents.base import BaseAgent
from core.portfolio import Portfolio
from tools.market_data import get_technical_signals, get_stock_info
from tools.options_analyzer import OptionsAnalyzer
from memory.database import save_lesson, save_signal, get_lessons
from config.settings import DEFAULT_STOCKS

SYSTEM_PROMPT = """Eres un estratega experto en opciones financieras que ayuda a inversores
individuales a proteger su capital y generar ingresos adicionales mediante opciones.

Tu enfoque principal es:
1. Protección del capital con puts protectoras en posiciones vulnerables
2. Generación de ingresos con covered calls en posiciones sobrecompradas
3. Estrategias collar para definir rangos riesgo/recompensa
4. Gestión del riesgo con spreads cuando la volatilidad implícita es alta

Responde siempre en español. Sé educativo y práctico.
Explica cada estrategia en términos simples, incluyendo:
- Coste máximo de la estrategia
- Protección máxima o ingreso esperado
- Punto de equilibrio
- Cuándo ejecutarla y cuándo salir

Responde en formato JSON con claves:
"market_context", "top_strategies" (lista), "risk_warnings" (lista), "education_tip"
"""


class OptionsAgent(BaseAgent):
    name = "options_specialist"
    description = "Analiza opciones para cobertura e ingresos sobre posiciones del portfolio"

    def run(self, symbols: List[str] = None) -> Dict:
        self.log("Iniciando análisis de opciones...")

        analyzer = OptionsAnalyzer()
        portfolio = Portfolio()

        # Determinar símbolos a analizar
        portfolio_symbols = []
        try:
            positions = portfolio.get_positions(refresh_prices=True)
            portfolio_symbols = [p.symbol for p in positions if p.asset_type in ("stock", "etf")]
        except Exception as e:
            self.log(f"Error cargando portfolio: {e}")
            positions = []

        if symbols is None:
            extra = [s for s in DEFAULT_STOCKS[:3] if s not in portfolio_symbols]
            symbols = portfolio_symbols + extra
        elif not symbols:
            symbols = DEFAULT_STOCKS[:3]

        self.log(f"Analizando opciones para {len(symbols)} símbolos: {symbols}")

        # 1. Analizar opciones para cada símbolo
        options_by_symbol: Dict[str, Dict] = {}
        hedge_recommendations: List[Dict] = []
        covered_calls: List[Dict] = []
        protective_puts: List[Dict] = []

        for sym in symbols:
            self.log(f"Calculando opciones para {sym}...")
            try:
                # Obtener precio y señal técnica
                tech = get_technical_signals(sym)
                if "error" in tech:
                    info = get_stock_info(sym)
                    current_price = info.get("price", 0)
                    rsi = 50.0
                    change_20d = 0.0
                    technical_score = 0
                else:
                    current_price = tech.get("current_price", 0)
                    rsi = tech.get("rsi", 50.0)
                    change_20d = tech.get("change_20d_pct", 0.0)
                    technical_score = tech.get("technical_score", 0)

                if current_price <= 0:
                    self.log(f"Precio inválido para {sym}, omitiendo.")
                    continue

                # Calcular cadena de opciones (30/60/90 días)
                chain = analyzer.options_chain_summary(sym, current_price)
                options_by_symbol[sym] = {
                    "current_price": current_price,
                    "rsi": rsi,
                    "technical_score": technical_score,
                    "change_20d_pct": change_20d,
                    "chain": chain,
                }

                # Determinar tamaño de posición (1 contrato = 100 acciones por defecto)
                position_size = 1.0
                for p in positions:
                    if p.symbol == sym:
                        position_size = p.quantity
                        break

                # Generar estrategias de cobertura
                hedges = analyzer.suggest_hedges(
                    symbol=sym,
                    position_size=position_size,
                    current_price=current_price,
                    risk_tolerance="medium",
                )
                hedge_recommendations.append({
                    "symbol": sym,
                    "current_price": current_price,
                    "strategies": hedges,
                })

                # Covered Call: oportunidad si RSI alto (sobrecomprado) o cambio 20d positivo grande
                iv_proxy = 0.30  # volatilidad implícita estimada
                is_overbought = rsi > 65 or change_20d > 15
                if is_overbought:
                    # Strike ~5-10% sobre precio actual, 30 días
                    call_strike = round(current_price * 1.07, 2)
                    call_data = analyzer.price_option(
                        S=current_price,
                        K=call_strike,
                        T_days=30,
                        sigma=iv_proxy,
                        option_type="call",
                    )
                    premium_pct = round(call_data["price"] / current_price * 100, 2)
                    covered_calls.append({
                        "symbol": sym,
                        "current_price": current_price,
                        "strike": call_strike,
                        "expiry_days": 30,
                        "premium": round(call_data["price"], 4),
                        "premium_pct": premium_pct,
                        "delta": call_data.get("delta"),
                        "reason": f"RSI={rsi:.1f} (sobrecomprado)" if rsi > 65 else f"Subida 20d={change_20d:+.1f}%",
                        "priority": "ALTA" if rsi > 70 else "MEDIA",
                    })

                # Protective Put: oportunidad si la posición tiene ganancias importantes o mercado bajista
                has_gains = any(
                    p.symbol == sym and p.pnl_pct > 20
                    for p in positions
                )
                is_risky = change_20d > 20 or technical_score <= -1
                if has_gains or is_risky:
                    # Put al 5-10% bajo precio actual, 60 días
                    put_strike = round(current_price * 0.92, 2)
                    put_data = analyzer.price_option(
                        S=current_price,
                        K=put_strike,
                        T_days=60,
                        sigma=iv_proxy,
                        option_type="put",
                    )
                    cost_pct = round(put_data["price"] / current_price * 100, 2)
                    protective_puts.append({
                        "symbol": sym,
                        "current_price": current_price,
                        "strike": put_strike,
                        "expiry_days": 60,
                        "premium": round(put_data["price"], 4),
                        "cost_pct": cost_pct,
                        "delta": put_data.get("delta"),
                        "protection_below": put_strike,
                        "reason": (
                            f"Ganancias acumuladas altas (proteger beneficios)"
                            if has_gains
                            else f"Señal técnica débil (score={technical_score})"
                        ),
                        "priority": "ALTA" if has_gains else "MEDIA",
                    })

            except Exception as e:
                self.log(f"Error procesando {sym}: {e}")
                options_by_symbol[sym] = {"error": str(e)}

        # 2. Guardar lección si hay muchas oportunidades de covered call
        if len(covered_calls) >= 3:
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Múltiples símbolos sobrecomprados: {[c['symbol'] for c in covered_calls]}",
                    lesson=(
                        f"Mercado con {len(covered_calls)} activos sobrecomprados simultáneamente. "
                        "Condición favorable para covered calls como fuente de ingresos y cushion ante corrección."
                    ),
                    confidence=0.75,
                )
            except Exception:
                pass

        # 3. Análisis IA
        self.log("Generando análisis IA de opciones...")
        ai_analysis = ""
        if self.provider != "rules":
            lessons_ctx = self.get_lessons_context()

            covered_calls_summary = "\n".join([
                f"  {c['symbol']}: Covered Call strike ${c['strike']} | "
                f"prima {c['premium_pct']:.2f}% | Razón: {c['reason']}"
                for c in covered_calls
            ]) or "  Ninguna detectada"

            protective_puts_summary = "\n".join([
                f"  {p['symbol']}: Protective Put strike ${p['strike']} | "
                f"coste {p['cost_pct']:.2f}% | Razón: {p['reason']}"
                for p in protective_puts
            ]) or "  Ninguna detectada"

            symbols_context = "\n".join([
                f"  {sym}: precio=${data.get('current_price', 0):.2f}, "
                f"RSI={data.get('rsi', 'N/A')}, cambio20d={data.get('change_20d_pct', 0):+.1f}%"
                for sym, data in options_by_symbol.items()
                if "error" not in data
            ])

            user_message = f"""Analiza las oportunidades de opciones para este portfolio:

ACTIVOS ANALIZADOS:
{symbols_context}

OPORTUNIDADES COVERED CALLS (ingresos):
{covered_calls_summary}

OPORTUNIDADES PROTECTIVE PUTS (protección):
{protective_puts_summary}

Total coberturas calculadas: {len(hedge_recommendations)} símbolos

{lessons_ctx}

Proporciona tu análisis en formato JSON con:
"market_context" (situación actual para opciones),
"top_strategies" (lista de las 3 mejores estrategias ahora mismo, con símbolo, tipo, justificación y pasos de ejecución),
"risk_warnings" (lista de advertencias importantes),
"education_tip" (consejo educativo sobre opciones para el inversor individual)
"""
            try:
                ai_analysis = self.ask_ai(
                    SYSTEM_PROMPT + ("\n\n" + lessons_ctx if lessons_ctx else ""),
                    user_message,
                    max_tokens=1500,
                )
            except Exception as e:
                ai_analysis = f"[Error en análisis IA: {e}]"

        self.log(
            f"Análisis de opciones completado. "
            f"Covered calls: {len(covered_calls)}, Protective puts: {len(protective_puts)}"
        )

        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "symbols_analyzed": list(options_by_symbol.keys()),
            "options_by_symbol": {
                sym: {k: v for k, v in data.items() if k != "chain"}
                for sym, data in options_by_symbol.items()
            },
            "options_chains": {
                sym: data.get("chain", {})
                for sym, data in options_by_symbol.items()
                if "error" not in data
            },
            "hedge_recommendations": hedge_recommendations,
            "covered_calls": sorted(covered_calls, key=lambda x: x.get("premium_pct", 0), reverse=True),
            "protective_puts": sorted(protective_puts, key=lambda x: x.get("priority", ""), reverse=True),
            "ai_analysis": ai_analysis,
        }
