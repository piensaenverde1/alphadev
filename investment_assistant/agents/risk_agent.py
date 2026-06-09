"""Agente de gestión de riesgo: sizing, alertas y protección de capital."""
import json
from typing import Dict, List
from agents.base import BaseAgent
from memory.database import save_lesson, get_agent_accuracy, get_portfolio

SYSTEM_PROMPT = """Eres un gestor de riesgo experto para inversores particulares.
Tu filosofía: preservar el capital es más importante que maximizar ganancias.

Principios que aplicas:
1. Nunca arriesgar más del 2% del capital en una sola operación
2. Máximo 20% del portfolio en un solo activo
3. Diversificación real: correlaciones bajas entre posiciones
4. Stop-loss siempre definido antes de entrar
5. Si el mercado está en modo BEARISH, reducir exposición total

Para cada señal calculas:
- Tamaño óptimo de posición (Kelly ajustado)
- Stop-loss dinámico basado en volatilidad
- Precio objetivo realista
- Riesgo real en euros, no solo en porcentaje

Responde en español. Sé conservador: más vale perder una oportunidad que perder capital.
"""


class RiskAgent(BaseAgent):
    name = "risk_agent"
    description = "Gestión de riesgo, sizing de posiciones y alertas de capital"

    def run(self, signals: List[Dict] = None, capital: float = 10000.0) -> Dict:
        from core.risk_manager import RiskManager
        from tools.risk_analyzer import RiskAnalyzer
        from tools.telegram_notifier import TelegramNotifier
        from memory.database import get_price_history

        self.log("Analizando riesgo del portfolio...")

        rm = RiskManager(capital=capital)
        analyzer = RiskAnalyzer()
        telegram = TelegramNotifier()

        # 1. Accuracy histórica de los agentes para Kelly
        accuracy = get_agent_accuracy()

        # 2. Sizing para cada señal
        sized_signals = []
        if signals:
            for sig in signals:
                price = sig.get("current_price") or sig.get("price", 0)
                if not price:
                    continue

                # Obtener stats de backtest si están disponibles
                agent_stats = accuracy.get(sig.get("agent_source", ""), {})
                backtest_stats = {
                    "win_rate": agent_stats.get("win_rate", 55) / 100,
                    "avg_win_pct": agent_stats.get("avg_return", 8) if agent_stats.get("avg_return", 0) > 0 else 8,
                    "avg_loss_pct": abs(agent_stats.get("avg_return", 5)) if agent_stats.get("avg_return", 0) < 0 else 5,
                } if agent_stats else None

                sizing = rm.calculate_position(sig, price, backtest_stats)
                risk_check = rm.portfolio_risk_check(get_portfolio(), sig)

                sized_signals.append({
                    **sig,
                    "sizing": sizing,
                    "risk_check": risk_check,
                    "approved": risk_check.get("approved", True),
                })

        # 3. Análisis de riesgo del portfolio actual
        portfolio = get_portfolio()
        portfolio_risk = {}
        if portfolio:
            # Construir historial de precios para análisis
            price_histories = {}
            for pos in portfolio:
                history = get_price_history(pos["symbol"], days=90)
                if history:
                    price_histories[pos["symbol"]] = [h["price"] for h in history]

            if price_histories:
                portfolio_risk = analyzer.analyze_portfolio(portfolio, price_histories)

        # 4. Alertas automáticas por Telegram
        alerts_sent = 0
        if telegram.is_configured():
            for sig in sized_signals:
                if sig.get("approved") and sig.get("sizing"):
                    telegram.send_signal_alert({
                        **sig,
                        "recommended_value": sig["sizing"].get("recommended_value", 0),
                    })
                    alerts_sent += 1

            if portfolio_risk.get("concentration_risk", 0) > 0.7:
                telegram.send_message(
                    "⚠️ *ALERTA DE RIESGO*\n"
                    f"Concentración del portfolio muy alta (HHI={portfolio_risk['concentration_risk']:.2f})\n"
                    "Considera diversificar más tus posiciones."
                )

        # 5. Análisis IA
        ai_analysis = ""
        if sized_signals and self.provider != "rules":
            lessons = self.get_lessons_context()
            approved = [s for s in sized_signals if s.get("approved")]
            rejected = [s for s in sized_signals if not s.get("approved")]

            signals_text = "\n".join([
                f"  {s.get('symbol')}: {s.get('action')} @ {s.get('current_price', s.get('price', 0))} | "
                f"Kelly={s['sizing'].get('kelly_fraction', 0):.1%} | "
                f"Riesgo={s['sizing'].get('risk_pct_of_capital', 0):.1%} capital | "
                f"{'✓ APROBADA' if s.get('approved') else '✗ RECHAZADA: ' + s['risk_check'].get('reason', '')}"
                for s in sized_signals[:6]
            ])

            ai_analysis = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Evalúa el riesgo de estas operaciones con capital de {capital:,.0f}€:

SEÑALES CON SIZING:
{signals_text}

RIESGO DEL PORTFOLIO ACTUAL:
{json.dumps(portfolio_risk, indent=2, default=str) if portfolio_risk else "Portfolio vacío"}

APROBADAS: {len(approved)} | RECHAZADAS: {len(rejected)}

Responde en JSON con:
- "risk_summary": evaluación del riesgo total (1-2 frases)
- "priority_signals": top 3 señales más seguras para ejecutar con justificación
- "portfolio_health": salud general del portfolio (BUENA/REGULAR/MALA) + razón
- "immediate_actions": acciones urgentes si hay riesgo elevado
- "sizing_advice": consejo general sobre el tamaño de posiciones actual
""",
                max_tokens=1500
            )

        # 6. Lecciones de riesgo
        rejected_count = sum(1 for s in sized_signals if not s.get("approved"))
        if rejected_count > 0:
            save_lesson(
                lesson_type="risk_management",
                agent=self.name,
                context=f"Risk check rechazó {rejected_count} señales",
                lesson=f"El {rejected_count} señales fueron rechazadas por gestión de riesgo hoy. "
                       "El sistema protege el capital activamente ante señales de sobresconcentración.",
                confidence=0.9
            )

        self.log(f"Riesgo analizado: {len(sized_signals)} señales, {alerts_sent} alertas Telegram")
        return {
            "agent": self.name,
            "capital": capital,
            "sized_signals": sized_signals,
            "portfolio_risk": portfolio_risk,
            "alerts_sent": alerts_sent,
            "ai_analysis": ai_analysis,
        }
