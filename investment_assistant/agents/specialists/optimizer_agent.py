"""Agente especialista en optimización de parámetros de estrategias técnicas."""
import json
from datetime import datetime
from typing import Dict, List, Optional

from agents.base import BaseAgent
from tools.optimizer import ParameterOptimizer
from memory.database import save_lesson, get_lessons
from config.settings import DEFAULT_STOCKS

SYSTEM_PROMPT = """Eres un analista cuantitativo especializado en la optimización de parámetros
de estrategias de trading técnico como RSI, MACD y medias móviles.

Tu rol es interpretar los resultados de optimización y extraer conclusiones sobre
el comportamiento del mercado de cada activo.

Cuando analices parámetros óptimos:
1. Explica qué revelan sobre el régimen del mercado (tendencial vs oscilante)
2. Identifica qué activos se benefician más de la optimización frente a los defaults
3. Advierte sobre overfitting cuando los parámetros son muy específicos
4. Sugiere si el activo es mejor para estrategias de momentum o reversión a la media
5. Conecta los parámetros óptimos con la liquidez y volatilidad del activo

Responde siempre en español. Sé técnico pero didáctico.
Responde en formato JSON con claves:
"market_regime_insights" (dict por símbolo), "best_optimizations" (lista),
"overfitting_warnings" (lista), "trading_style_recommendations" (dict por símbolo),
"summary"
"""

# Parámetros default para comparación
DEFAULT_RSI = {"period": 14, "oversold": 30, "overbought": 70}
DEFAULT_MACD = {"fast": 12, "slow": 26, "signal": 9}


class OptimizerAgent(BaseAgent):
    name = "optimizer_specialist"
    description = "Optimiza parámetros RSI y MACD por símbolo y extrae insights del comportamiento del mercado"

    def run(self, symbols: List[str] = None) -> Dict:
        self.log("Iniciando optimización de parámetros...")

        if symbols is None:
            # Tomar símbolos del portfolio + algunos por defecto
            try:
                from core.portfolio import Portfolio
                portfolio = Portfolio()
                positions = portfolio.get_positions(refresh_prices=False)
                portfolio_syms = [p.symbol for p in positions if p.asset_type in ("stock", "etf")]
            except Exception:
                portfolio_syms = []
            symbols = portfolio_syms[:5] or DEFAULT_STOCKS[:5]

        self.log(f"Optimizando parámetros para {len(symbols)} símbolos: {symbols}")
        optimizer = ParameterOptimizer()

        optimized_params: Dict[str, Dict] = {}
        improvement_vs_default: Dict[str, Dict] = {}
        profiles: List[Dict] = []
        errors: List[str] = []

        for sym in symbols:
            self.log(f"Optimizando {sym}...")
            try:
                result = optimizer.get_optimal_params(sym)
            except Exception as e:
                self.log(f"Error en optimización de {sym}, usando fallback: {e}")
                errors.append(f"{sym}: {str(e)}")
                try:
                    result = optimizer.fallback_optimize(sym)
                except Exception as fe:
                    self.log(f"Error en fallback de {sym}: {fe}")
                    result = {
                        "symbol": sym,
                        "rsi_params": {"period": 14, "oversold": 30, "overbought": 70,
                                       "sharpe": None, "total_return_pct": None, "win_rate": None, "source": "error_fallback"},
                        "macd_params": {"fast": 12, "slow": 26, "signal": 9,
                                        "sharpe": None, "total_return_pct": None, "win_rate": None, "source": "error_fallback"},
                    }

            rsi = result.get("rsi_params", {})
            macd = result.get("macd_params", {})
            optimized_params[sym] = result

            # Calcular mejora vs defaults
            rsi_sharpe = rsi.get("sharpe")
            macd_sharpe = macd.get("sharpe")

            # Determinar si los parámetros difieren de los defaults
            rsi_changed = (
                rsi.get("period") != DEFAULT_RSI["period"]
                or rsi.get("oversold") != DEFAULT_RSI["oversold"]
                or rsi.get("overbought") != DEFAULT_RSI["overbought"]
            )
            macd_changed = (
                macd.get("fast") != DEFAULT_MACD["fast"]
                or macd.get("slow") != DEFAULT_MACD["slow"]
                or macd.get("signal") != DEFAULT_MACD["signal"]
            )

            improvement_vs_default[sym] = {
                "rsi_params_changed": rsi_changed,
                "macd_params_changed": macd_changed,
                "rsi_sharpe": rsi_sharpe,
                "macd_sharpe": macd_sharpe,
                "rsi_return_pct": rsi.get("total_return_pct"),
                "macd_return_pct": macd.get("total_return_pct"),
                "data_source": rsi.get("source", "unknown"),
                "optimization_beneficial": rsi_changed or macd_changed,
            }

            # Construir perfil de optimización del símbolo
            rsi_period = rsi.get("period", 14)
            rsi_os = rsi.get("oversold", 30)
            rsi_ob = rsi.get("overbought", 70)
            macd_fast = macd.get("fast", 12)
            macd_slow = macd.get("slow", 26)

            # Interpretar qué significan los parámetros
            regime = "oscilante"
            if rsi_period <= 10:
                regime = "muy volátil/rápido"
            elif rsi_period >= 18:
                regime = "tendencial/lento"

            mean_reversion = rsi_os >= 35 and rsi_ob <= 65
            momentum = macd_fast <= 10 and macd_slow <= 22

            profile = {
                "symbol": sym,
                "regime": regime,
                "mean_reversion_bias": mean_reversion,
                "momentum_bias": momentum,
                "rsi_optimal": {
                    "period": rsi_period,
                    "oversold": rsi_os,
                    "overbought": rsi_ob,
                },
                "macd_optimal": {
                    "fast": macd_fast,
                    "slow": macd_slow,
                    "signal": macd.get("signal", 9),
                },
                "sharpe_rsi": rsi_sharpe,
                "sharpe_macd": macd_sharpe,
                "best_strategy": (
                    "RSI" if (rsi_sharpe or 0) >= (macd_sharpe or 0)
                    else "MACD"
                ),
                "data_source": rsi.get("source", "unknown"),
            }
            profiles.append(profile)

            # Guardar perfil como lección si tiene datos reales y mejora es significativa
            if rsi.get("source") not in (None, "default", "error_fallback") and rsi_changed:
                try:
                    lesson_text = (
                        f"{sym}: parámetros óptimos RSI({rsi_period},{rsi_os},{rsi_ob}) "
                        f"vs default RSI(14,30,70). Régimen de mercado: {regime}. "
                        f"Sharpe optimizado: {rsi_sharpe}."
                    )
                    save_lesson(
                        lesson_type="market_pattern",
                        agent=self.name,
                        context=f"Optimización de parámetros para {sym} (fuente: {rsi.get('source')})",
                        lesson=lesson_text,
                        confidence=0.70,
                    )
                    self.log(f"Perfil de optimización guardado para {sym}")
                except Exception as e:
                    self.log(f"Error guardando lección para {sym}: {e}")

        # Identificar los símbolos que más se benefician de la optimización
        benefiting_most = sorted(
            [sym for sym, imp in improvement_vs_default.items() if imp["optimization_beneficial"]],
            key=lambda s: (
                abs((improvement_vs_default[s].get("rsi_sharpe") or 0))
                + abs((improvement_vs_default[s].get("macd_sharpe") or 0))
            ),
            reverse=True,
        )

        # 4. Análisis IA
        self.log("Generando análisis IA de optimización...")
        ai_analysis = ""
        if self.provider != "rules":
            lessons_ctx = self.get_lessons_context()

            profiles_summary = "\n".join([
                f"  {p['symbol']}: régimen={p['regime']}, "
                f"RSI óptimo=({p['rsi_optimal']['period']},{p['rsi_optimal']['oversold']},{p['rsi_optimal']['overbought']}), "
                f"MACD óptimo=({p['macd_optimal']['fast']},{p['macd_optimal']['slow']},{p['macd_optimal']['signal']}), "
                f"mejor_estrategia={p['best_strategy']}, fuente_datos={p['data_source']}"
                for p in profiles
            ])

            improvement_summary = "\n".join([
                f"  {sym}: cambiados={'RSI+MACD' if imp['rsi_params_changed'] and imp['macd_params_changed'] else 'RSI' if imp['rsi_params_changed'] else 'MACD' if imp['macd_params_changed'] else 'ninguno'}, "
                f"Sharpe RSI={imp.get('rsi_sharpe')}, Sharpe MACD={imp.get('macd_sharpe')}"
                for sym, imp in improvement_vs_default.items()
            ])

            user_message = f"""Analiza los resultados de optimización de parámetros técnicos:

PERFILES DE OPTIMIZACIÓN POR SÍMBOLO:
{profiles_summary}

MEJORA VS PARÁMETROS DEFAULT:
{improvement_summary}

SÍMBOLOS QUE MÁS SE BENEFICIAN DE OPTIMIZACIÓN:
{', '.join(benefiting_most) if benefiting_most else 'Ninguno significativo'}

ERRORES ENCONTRADOS:
{chr(10).join(errors) if errors else 'Ninguno'}

{lessons_ctx}

Interpreta qué nos dicen estos parámetros óptimos sobre el comportamiento de cada activo.
Responde en formato JSON con:
"market_regime_insights" (dict por símbolo con interpretación),
"best_optimizations" (top 3 optimizaciones más impactantes con justificación),
"overfitting_warnings" (símbolos donde los parámetros muy específicos sugieren overfitting),
"trading_style_recommendations" (dict por símbolo: momentum vs mean-reversion),
"summary" (párrafo ejecutivo en español)
"""
            try:
                ai_analysis = self.ask_ai(
                    SYSTEM_PROMPT + ("\n\n" + lessons_ctx if lessons_ctx else ""),
                    user_message,
                    max_tokens=1500,
                )
            except Exception as e:
                ai_analysis = f"[Error en análisis IA: {e}]"

        self.log(f"Optimización completada. {len(profiles)} perfiles generados.")

        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "symbols_analyzed": symbols,
            "optimized_params": optimized_params,
            "improvement_vs_default": improvement_vs_default,
            "profiles": profiles,
            "benefiting_most": benefiting_most,
            "default_params": {
                "rsi": DEFAULT_RSI,
                "macd": DEFAULT_MACD,
            },
            "errors": errors,
            "ai_analysis": ai_analysis,
        }
