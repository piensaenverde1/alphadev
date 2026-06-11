"""Agente especialista en análisis macroeconómico global."""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from agents.base import BaseAgent
from tools.market_data import get_multiple_stocks
from memory.database import save_lesson, save_price, get_lessons

SYSTEM_PROMPT = """Eres un macroeconomista experto que traduce datos macroeconómicos complejos
en insights accionables para inversores individuales.

Tu rol es analizar el entorno macroeconómico global y determinar:
1. El régimen actual de mercado (risk-on vs risk-off)
2. Las implicaciones para diferentes clases de activos
3. Los riesgos sistémicos más relevantes en este momento
4. Las oportunidades que presenta el entorno actual

Cuando analices indicadores macro:
- VIX > 30: miedo extremo, posible punto de inflexión
- VIX < 15: complacencia, riesgo de corrección
- Curva invertida (10Y-2Y < 0): señal de recesión en 12-18 meses
- Dólar fuerte + oro subiendo: huida hacia la seguridad
- Bitcoin subiendo + VIX bajo: apetito de riesgo

Responde siempre en español. Sé concreto sobre implicaciones por clase de activo.
Responde en formato JSON con claves:
"macro_regime", "asset_class_implications" (dict), "key_risks" (lista),
"opportunities" (lista), "tactical_recommendations" (lista), "summary"
"""

# Indicadores macro disponibles vía yfinance (sin API key)
MACRO_INDICATORS = {
    "VIX": "^VIX",
    "US_10Y": "^TNX",
    "US_2Y": "^IRX",
    "GOLD": "GC=F",
    "USD_INDEX": "DX-Y.NYB",
    "OIL_WTI": "CL=F",
    "EURUSD": "EURUSD=X",
    "BITCOIN": "BTC-USD",
}

# Nombre de display para cada ticker
INDICATOR_NAMES = {
    "^VIX": "Índice del Miedo VIX",
    "^TNX": "Bono EEUU 10 años",
    "^IRX": "Bono EEUU 2 años",
    "GC=F": "Oro (XAU/USD)",
    "DX-Y.NYB": "Índice Dólar (DXY)",
    "CL=F": "Petróleo WTI",
    "EURUSD=X": "EUR/USD",
    "BTC-USD": "Bitcoin (risk-on proxy)",
}


def _classify_vix(vix: float) -> Tuple[str, str]:
    """Clasifica el nivel de VIX y su interpretación."""
    if vix < 12:
        return "EXTREMA_COMPLACENCIA", "Mercado excesivamente tranquilo, riesgo de corrección"
    elif vix < 20:
        return "BAJA", "Entorno de baja volatilidad, mercado confiado"
    elif vix < 30:
        return "MODERADA", "Volatilidad moderada, cierta incertidumbre"
    elif vix < 40:
        return "ALTA", "Miedo en el mercado, posibles oportunidades de compra"
    else:
        return "EXTREMA", "Pánico de mercado, alta cautela recomendada"


def _calculate_fear_greed(
    vix: float,
    yield_spread: float,
    gold_change: float,
    usd_change: float,
    btc_change: float,
) -> Tuple[int, str]:
    """
    Calcula un score de miedo/avaricia de 0 (miedo extremo) a 100 (avaricia extrema).
    Componentes:
      - VIX: peso 35% (invertido: VIX alto = miedo)
      - Curva de tipos: peso 20% (invertida = miedo)
      - Momentum oro: peso 20% (oro sube = miedo)
      - Fuerza del dólar: peso 15% (dólar sube = miedo/safe-haven)
      - Bitcoin: peso 10% (btc sube = risk-on = avaricia)
    """
    score = 50.0  # punto neutro

    # Componente VIX (35%)
    # VIX=10 -> +17.5 (avaricia), VIX=50 -> -17.5 (miedo)
    vix_norm = max(0, min(1, (50 - vix) / 40))  # 0=pánico, 1=calma
    score += (vix_norm - 0.5) * 35

    # Componente curva de tipos (20%)
    # spread > 1% positivo -> avaricia; curva invertida -> miedo
    curve_norm = max(0, min(1, (yield_spread + 2) / 4))  # mapear [-2%, +2%] a [0, 1]
    score += (curve_norm - 0.5) * 20

    # Componente oro (20%, invertido: oro sube = miedo)
    # cambio semanal +5% -> máximo miedo; -5% -> máximo avaricia
    gold_norm = max(0, min(1, (-gold_change + 5) / 10))
    score += (gold_norm - 0.5) * 20

    # Componente USD (15%, invertido: dólar fuerte = safe-haven = miedo)
    usd_norm = max(0, min(1, (-usd_change + 3) / 6))
    score += (usd_norm - 0.5) * 15

    # Componente Bitcoin (10%: btc sube = risk-on = avaricia)
    btc_norm = max(0, min(1, (btc_change + 10) / 20))
    score += (btc_norm - 0.5) * 10

    score = int(max(0, min(100, score)))

    if score <= 20:
        label = "MIEDO EXTREMO"
    elif score <= 40:
        label = "MIEDO"
    elif score <= 60:
        label = "NEUTRO"
    elif score <= 80:
        label = "AVARICIA"
    else:
        label = "AVARICIA EXTREMA"

    return score, label


class MacroAgent(BaseAgent):
    name = "macro_specialist"
    description = "Analiza indicadores macroeconómicos globales y su impacto en distintas clases de activos"

    def run(self) -> Dict:
        self.log("Iniciando análisis macroeconómico...")

        # 1. Obtener todos los indicadores macro
        self.log("Fetching indicadores macro vía Yahoo Finance...")
        tickers = list(MACRO_INDICATORS.values())
        raw_data = []
        try:
            raw_data = get_multiple_stocks(tickers)
        except Exception as e:
            self.log(f"Error en fetch batch de indicadores: {e}")

        # Mapear resultados por ticker
        ticker_to_data: Dict[str, Dict] = {}
        for item in raw_data:
            sym = item.get("symbol", "")
            ticker_to_data[sym] = item

        # Construir diccionario de indicadores con datos de fallback
        indicators: Dict[str, Dict] = {}
        for name, ticker in MACRO_INDICATORS.items():
            data = ticker_to_data.get(ticker, {})
            price = data.get("price", 0.0)
            change_pct = data.get("change_pct", 0.0)

            # Guardar precio en historial si válido
            if price > 0:
                try:
                    save_price(ticker, "macro", price, change_pct=change_pct)
                except Exception:
                    pass

            indicators[name] = {
                "ticker": ticker,
                "display_name": INDICATOR_NAMES.get(ticker, name),
                "price": price,
                "change_pct_1d": round(change_pct, 2),
                "available": price > 0,
            }

        # 2. Calcular curva de tipos (spread 10Y - 2Y)
        vix_val = indicators.get("VIX", {}).get("price", 20.0)
        us10y = indicators.get("US_10Y", {}).get("price", 4.0)
        us2y = indicators.get("US_2Y", {}).get("price", 4.5)
        gold_change = indicators.get("GOLD", {}).get("change_pct_1d", 0.0)
        usd_change = indicators.get("USD_INDEX", {}).get("change_pct_1d", 0.0)
        btc_change = indicators.get("BITCOIN", {}).get("change_pct_1d", 0.0)
        gold_price = indicators.get("GOLD", {}).get("price", 0.0)
        oil_price = indicators.get("OIL_WTI", {}).get("price", 0.0)
        eurusd_price = indicators.get("EURUSD", {}).get("price", 0.0)

        # Nota: ^TNX da rendimiento en % (ej. 4.25 = 4.25%), ^IRX da rendimiento en %
        yield_spread = round(us10y - us2y, 3)
        curve_inverted = yield_spread < 0

        yield_curve = {
            "us_10y_yield": us10y,
            "us_2y_yield": us2y,
            "spread_10y_2y": yield_spread,
            "inverted": curve_inverted,
            "recession_signal": curve_inverted,
            "interpretation": (
                "CURVA INVERTIDA: señal históricamente precursora de recesión en 12-18 meses"
                if curve_inverted
                else f"Curva normal con spread +{yield_spread:.2f}%: sin señal inmediata de recesión"
            ),
        }

        # 3. Detectar entorno risk-on vs risk-off
        vix_level, vix_desc = _classify_vix(vix_val)
        risk_signals = []

        # Risk-off signals
        if vix_val > 25:
            risk_signals.append(f"VIX={vix_val:.1f} elevado (miedo en el mercado)")
        if gold_change > 1.0:
            risk_signals.append(f"Oro subiendo +{gold_change:.1f}% (huida a la seguridad)")
        if usd_change > 0.5:
            risk_signals.append(f"Dólar fortaleciéndose +{usd_change:.1f}% (safe-haven demand)")
        if curve_inverted:
            risk_signals.append(f"Curva invertida {yield_spread:.2f}% (señal recesión)")

        # Risk-on signals
        risk_on_signals = []
        if vix_val < 18:
            risk_on_signals.append(f"VIX={vix_val:.1f} bajo (complacencia/confianza)")
        if btc_change > 3:
            risk_on_signals.append(f"Bitcoin +{btc_change:.1f}% (apetito por riesgo)")
        if gold_change < -1.0:
            risk_on_signals.append(f"Oro bajando {gold_change:.1f}% (menos demanda de refugio)")

        risk_environment = "RISK-OFF" if len(risk_signals) > len(risk_on_signals) else "RISK-ON"
        if len(risk_signals) == len(risk_on_signals):
            risk_environment = "NEUTRAL"

        risk_env_data = {
            "environment": risk_environment,
            "vix_level": vix_level,
            "vix_description": vix_desc,
            "risk_off_signals": risk_signals,
            "risk_on_signals": risk_on_signals,
            "confidence": "ALTA" if abs(len(risk_signals) - len(risk_on_signals)) >= 3 else "MODERADA",
        }

        # 4. Calcular Fear & Greed score
        fear_greed_score, fear_greed_label = _calculate_fear_greed(
            vix=vix_val,
            yield_spread=yield_spread,
            gold_change=gold_change,
            usd_change=usd_change,
            btc_change=btc_change,
        )

        # 5. Construir señales macro consolidadas
        macro_signals: List[Dict] = []

        if curve_inverted:
            macro_signals.append({
                "signal": "RECESIÓN_POTENCIAL",
                "indicator": "Curva 10Y-2Y",
                "value": f"{yield_spread:.3f}%",
                "implication": "Reducir exposición a cíclicos, incrementar defensivos y bonos de calidad",
                "urgency": "MEDIA",
            })

        if vix_val > 30:
            macro_signals.append({
                "signal": "MIEDO_EXTREMO",
                "indicator": "VIX",
                "value": f"{vix_val:.1f}",
                "implication": "Potencial punto de inflexión alcista. Considerar compras escalonadas en índices",
                "urgency": "ALTA",
            })
        elif vix_val < 13:
            macro_signals.append({
                "signal": "COMPLACENCIA",
                "indicator": "VIX",
                "value": f"{vix_val:.1f}",
                "implication": "Mercado muy tranquilo. Reducir riesgo y añadir coberturas put",
                "urgency": "MEDIA",
            })

        if gold_change > 2.0:
            macro_signals.append({
                "signal": "HUIDA_A_SEGURIDAD",
                "indicator": "Oro",
                "value": f"+{gold_change:.1f}%",
                "implication": "Dólar y bonos pueden beneficiarse. Reducir posiciones especulativas",
                "urgency": "MEDIA",
            })

        if abs(usd_change) > 1.0:
            direction = "fortalecimiento" if usd_change > 0 else "debilitamiento"
            implication = (
                "Presión sobre emergentes y commodities denominados en USD"
                if usd_change > 0
                else "Favorable para commodities y mercados emergentes"
            )
            macro_signals.append({
                "signal": f"DÓLAR_{direction.upper()}",
                "indicator": "USD Index",
                "value": f"{usd_change:+.1f}%",
                "implication": implication,
                "urgency": "BAJA",
            })

        # Guardar lección si se detecta un régimen importante
        if curve_inverted:
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Curva de tipos invertida: spread 10Y-2Y = {yield_spread:.3f}%",
                    lesson=(
                        f"Curva de tipos invertida detectada (spread={yield_spread:.3f}%). "
                        "Históricamente precede recesiones en 12-18 meses. "
                        "Incrementar bonos de calidad y reducir cíclicos."
                    ),
                    confidence=0.80,
                )
            except Exception:
                pass

        if fear_greed_score <= 20:
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Fear & Greed = {fear_greed_score} ({fear_greed_label})",
                    lesson=(
                        f"Score de miedo extremo ({fear_greed_score}/100). "
                        "Históricamente estas zonas ofrecen mejores puntos de entrada a largo plazo. "
                        "Acumular posiciones en índices diversificados."
                    ),
                    confidence=0.75,
                )
            except Exception:
                pass

        # 6. Análisis IA
        self.log("Generando análisis IA macro...")
        ai_analysis = ""
        if self.provider != "rules":
            lessons_ctx = self.get_lessons_context()

            indicators_summary = "\n".join([
                f"  {name} ({data['ticker']}): {data['price']} | cambio 1d: {data['change_pct_1d']:+.2f}%"
                for name, data in indicators.items()
                if data["available"]
            ])
            unavailable = [name for name, d in indicators.items() if not d["available"]]

            user_message = f"""Analiza el entorno macroeconómico actual con estos datos:

INDICADORES MACRO:
{indicators_summary}
{f"Sin datos para: {', '.join(unavailable)}" if unavailable else ""}

CURVA DE TIPOS:
  Bono 10Y: {us10y:.3f}%
  Bono 2Y: {us2y:.3f}%
  Spread 10Y-2Y: {yield_spread:+.3f}% {'⚠️ INVERTIDA' if curve_inverted else '(normal)'}

ENTORNO RISK-ON/OFF: {risk_environment}
  Señales risk-off: {'; '.join(risk_signals) if risk_signals else 'ninguna'}
  Señales risk-on: {'; '.join(risk_on_signals) if risk_on_signals else 'ninguna'}

FEAR & GREED SCORE: {fear_greed_score}/100 → {fear_greed_label}
  VIX: {vix_val:.1f} ({vix_level})
  Oro: {gold_price:.2f} ({gold_change:+.2f}%)
  Petróleo WTI: {oil_price:.2f}
  EUR/USD: {eurusd_price:.4f}
  Bitcoin: {btc_change:+.2f}%

SEÑALES MACRO DETECTADAS:
{json.dumps(macro_signals, ensure_ascii=False, indent=2)}

{lessons_ctx}

Proporciona análisis en formato JSON con:
"macro_regime" (descripción del régimen actual),
"asset_class_implications" (dict: acciones, bonos, oro, crypto, inmobiliario, efectivo),
"key_risks" (lista de 3-5 riesgos principales),
"opportunities" (lista de 3 oportunidades en este entorno),
"tactical_recommendations" (lista de 3-5 acciones concretas),
"summary" (párrafo ejecutivo en español, 3-4 frases)
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
            f"Análisis macro completado. "
            f"Entorno: {risk_environment}, Fear&Greed: {fear_greed_score}/100 ({fear_greed_label})"
        )

        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "indicators": indicators,
            "yield_curve": yield_curve,
            "risk_environment": risk_env_data,
            "fear_greed_score": {
                "score": fear_greed_score,
                "label": fear_greed_label,
                "components": {
                    "vix": vix_val,
                    "yield_spread": yield_spread,
                    "gold_change_1d": gold_change,
                    "usd_change_1d": usd_change,
                    "btc_change_1d": btc_change,
                },
            },
            "macro_signals": macro_signals,
            "ai_analysis": ai_analysis,
        }
