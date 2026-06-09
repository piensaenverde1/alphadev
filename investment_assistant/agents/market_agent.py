"""Agente de análisis de mercado: acciones y ETFs."""
import json
from typing import Dict, List
from agents.base import BaseAgent
from tools.market_data import get_multiple_stocks, get_technical_signals, get_market_overview
from memory.database import save_signal, save_price, get_lessons
from config.settings import DEFAULT_STOCKS, DEFAULT_ETFS

SYSTEM_PROMPT = """Eres un analista financiero experto en acciones y ETFs.
Tu rol es analizar datos de mercado y generar señales de inversión claras.
Responde siempre en español. Sé conciso pero profundo.
Cuando generes recomendaciones:
1. Basa tus análisis en datos técnicos y fundamentales
2. Considera el contexto macroeconómico
3. Siempre incluye nivel de riesgo
4. Proporciona precio objetivo y stop-loss cuando sea posible
5. Horizon temporal: SHORT (días), MEDIUM (semanas), LONG (meses)
"""


class MarketAgent(BaseAgent):
    name = "market_analyst"
    description = "Analiza acciones y ETFs, genera señales de compra/venta"

    def run(self, symbols: List[str] = None) -> Dict:
        self.log("Iniciando análisis de mercado...")
        symbols = symbols or (DEFAULT_STOCKS[:5] + DEFAULT_ETFS[:3])

        # 1. Visión general del mercado
        self.log("Obteniendo overview del mercado...")
        overview = get_market_overview()

        # 2. Análisis técnico de cada activo
        self.log(f"Analizando {len(symbols)} activos...")
        tech_signals = []
        for sym in symbols:
            sig = get_technical_signals(sym)
            if "error" not in sig:
                tech_signals.append(sig)
                # Guardar precio en historial
                save_price(sym, "stock", sig["current_price"],
                           change_pct=sig.get("change_5d_pct", 0))

        # 3. Filtrar señales relevantes (no HOLD)
        actionable = [s for s in tech_signals if s["action"] in ("BUY", "SELL", "WATCH")]

        # 4. Enriquecer con IA si está disponible
        ai_analysis = ""
        if actionable and self.provider != "rules":
            lessons = self.get_lessons_context()
            market_summary = self._format_market_summary(overview)
            signals_summary = self._format_signals(actionable)

            ai_analysis = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Analiza estas señales de mercado y proporciona tu evaluación:

OVERVIEW DEL MERCADO:
{market_summary}

SEÑALES TÉCNICAS DETECTADAS:
{signals_summary}

Por favor:
1. Evalúa el contexto de mercado actual
2. Confirma o descarta cada señal técnica con razonamiento
3. Prioriza las 3 mejores oportunidades
4. Identifica el principal riesgo del mercado ahora mismo
5. Responde en formato JSON con claves: "context", "top_opportunities", "main_risk", "signals_confirmed"
""",
                max_tokens=1500
            )

        # 5. Guardar señales en BD
        saved_signals = []
        for sig in actionable:
            if sig["action"] == "BUY":
                target = sig["current_price"] * 1.10
                stop = sig["current_price"] * 0.95
            elif sig["action"] == "SELL":
                target = sig["current_price"] * 0.92
                stop = sig["current_price"] * 1.05
            else:
                target = sig["current_price"] * 1.05
                stop = sig["current_price"] * 0.97

            signal_id = save_signal(
                symbol=sig["symbol"],
                asset_type="stock",
                action=sig["action"],
                confidence=min(1.0, (abs(sig["technical_score"]) / 4)),
                reasoning=" | ".join(sig.get("signals", [])),
                price=sig["current_price"],
                target=target,
                stop=stop,
                horizon="MEDIUM",
                source=self.name
            )
            saved_signals.append({**sig, "signal_id": signal_id, "target": round(target, 2), "stop": round(stop, 2)})

        self.log(f"Análisis completado: {len(actionable)} señales generadas")
        return {
            "agent": self.name,
            "market_overview": overview,
            "technical_signals": tech_signals,
            "actionable_signals": saved_signals,
            "ai_analysis": ai_analysis,
            "total_analyzed": len(symbols),
        }

    def _format_market_summary(self, overview: Dict) -> str:
        lines = []
        for name, data in overview.items():
            trend = data.get("trend", "-")
            price = data.get("price", 0)
            pct = data.get("change_pct", 0)
            lines.append(f"  {name}: {price} {trend} {pct:+.2f}%")
        return "\n".join(lines)

    def _format_signals(self, signals: List[Dict]) -> str:
        lines = []
        for s in signals:
            reasons = "; ".join(s.get("signals", [])[:3])
            lines.append(
                f"  {s['symbol']}: {s['action']} @ ${s['current_price']} "
                f"| RSI:{s.get('rsi', 'N/A')} | Score:{s.get('technical_score', 0)} "
                f"| {reasons}"
            )
        return "\n".join(lines)
