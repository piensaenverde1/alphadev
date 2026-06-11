"""Manager 2: Coordina todos los agentes de ejecución y gestión de riesgo."""
import json
from typing import Dict, List, Optional
from agents.base import BaseAgent
from memory.database import save_lesson

SYSTEM_PROMPT = """Eres el Director de Riesgo y Ejecución de un sistema de inversión automatizado.
Tu responsabilidad es decidir QUÉ operaciones ejecutar, CON QUÉ tamaño y en QUÉ orden.

Principios de ejecución:
1. Capital preservation primero: si hay duda, no ejecutar
2. Solo operar con señales que pasen el filtro de riesgo
3. Backtest valida la estrategia: si una señal no funcionó históricamente, reducir tamaño
4. Paper trading confirma antes de dinero real
5. Portfolio siempre diversificado: no concentrar >20% en un activo

Para cada batch de señales debes:
1. Validar cada señal con el análisis de riesgo
2. Rechazar las que no cumplan criterios mínimos de riesgo/recompensa (>1.5x)
3. Ordenar las aprobadas por ratio riesgo/recompensa
4. Asignar capital de forma que ninguna posición supere el 2% de riesgo del portfolio

Responde siempre en español. Sé conservador con los números.
"""


class ExecutionManager(BaseAgent):
    name = "execution_manager"
    description = "Manager de ejecución y riesgo: filtra, dimensiona y ejecuta señales"

    def run(
        self,
        signals: List[Dict] = None,
        capital: float = 10000.0,
        run_backtest: bool = False,
    ) -> Dict:
        self.log(f"[MANAGER] Iniciando gestión de ejecución (capital: ${capital:,.2f})...")

        signals = signals or []
        agent_results = {}

        # -- Agente de riesgo: valida y dimensiona señales --
        self.log("[MANAGER] Ejecutando RiskAgent...")
        risk_result = {}
        sized_signals = []
        try:
            from agents.risk_agent import RiskAgent
            risk_agent = RiskAgent()
            risk_result = risk_agent.run(signals=signals, capital=capital)
            agent_results["risk"] = risk_result
            sized_signals = risk_result.get("sized_signals", signals)
            self.log(
                f"[MANAGER] RiskAgent completado. "
                f"Señales validadas: {len(sized_signals)}"
            )
        except Exception as e:
            self.log(f"[MANAGER] RiskAgent falló: {e}")
            agent_results["risk"] = {"error": str(e)}
            sized_signals = signals

        # -- Paper trading: ejecuta señales aprobadas --
        self.log("[MANAGER] Ejecutando PaperTradingAgent...")
        paper_result = {}
        try:
            from agents.specialists.paper_trading_agent import PaperTradingAgent
            paper_agent = PaperTradingAgent()
            paper_result = paper_agent.run(signals=sized_signals, execute=True)
            agent_results["paper_trading"] = paper_result
            self.log(
                f"[MANAGER] PaperTradingAgent completado. "
                f"Ejecutadas: {len(paper_result.get('executed_trades', []))}"
            )
        except Exception as e:
            self.log(f"[MANAGER] PaperTradingAgent falló: {e}")
            agent_results["paper_trading"] = {"error": str(e)}

        # -- Backtest: validación histórica (opcional) --
        if run_backtest:
            self.log("[MANAGER] Ejecutando BacktestAgent...")
            try:
                from agents.backtest_agent import BacktestAgent
                backtest_agent = BacktestAgent()
                backtest_result = backtest_agent.run(signals=signals)
                agent_results["backtest"] = backtest_result
                self.log("[MANAGER] BacktestAgent completado.")
            except Exception as e:
                self.log(f"[MANAGER] BacktestAgent falló: {e}")
                agent_results["backtest"] = {"error": str(e)}

        # -- Portfolio: salud del portfolio actual --
        self.log("[MANAGER] Ejecutando PortfolioAgent...")
        portfolio_result = {}
        try:
            from agents.specialists.portfolio_agent import PortfolioAgent
            portfolio_agent = PortfolioAgent()
            portfolio_result = portfolio_agent.run()
            agent_results["portfolio"] = portfolio_result
            self.log("[MANAGER] PortfolioAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] PortfolioAgent falló: {e}")
            agent_results["portfolio"] = {"error": str(e)}

        # -- Optimizer: optimización de portfolio (en scope full) --
        self.log("[MANAGER] Ejecutando OptimizerAgent...")
        try:
            from agents.specialists.optimizer_agent import OptimizerAgent
            optimizer_agent = OptimizerAgent()
            optimizer_result = optimizer_agent.run()
            agent_results["optimizer"] = optimizer_result
            self.log("[MANAGER] OptimizerAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] OptimizerAgent falló: {e}")
            agent_results["optimizer"] = {"error": str(e)}

        # -- Options: cobertura (opcional) --
        self.log("[MANAGER] Ejecutando OptionsAgent...")
        try:
            from agents.specialists.options_agent import OptionsAgent
            options_agent = OptionsAgent()
            options_result = options_agent.run(signals=sized_signals)
            agent_results["options"] = options_result
            self.log("[MANAGER] OptionsAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] OptionsAgent falló: {e}")
            agent_results["options"] = {"error": str(e)}

        # -- Construir plan de ejecución --
        self.log("[MANAGER] Construyendo plan de ejecución...")
        approved_signals, rejected_signals = self._filter_signals(
            sized_signals, agent_results
        )

        execution_plan = self._build_execution_plan(
            approved_signals, capital, agent_results
        )

        risk_summary = self._build_risk_summary(risk_result, portfolio_result)

        # -- Síntesis de IA --
        self.log("[MANAGER] Generando síntesis de ejecución con IA...")
        lessons_ctx = self.get_lessons_context()

        backtest_summary = ""
        if "backtest" in agent_results and "error" not in agent_results["backtest"]:
            bt = agent_results["backtest"]
            backtest_summary = (
                f"Backtest: win_rate={bt.get('win_rate', 0):.1f}%, "
                f"avg_return={bt.get('avg_return', 0):+.2f}%"
            )

        paper_summary = ""
        if paper_result and "error" not in paper_result:
            pm = paper_result.get("performance_metrics", {})
            paper_summary = (
                f"Paper trading: win_rate={pm.get('win_rate', 0):.1f}%, "
                f"total_pnl={pm.get('total_pnl', 0):+.2f}"
            )

        user_message = f"""Plan de ejecución para aprobación:

CAPITAL DISPONIBLE: ${capital:,.2f}
SEÑALES RECIBIDAS: {len(signals)}
SEÑALES APROBADAS: {len(approved_signals)}
SEÑALES RECHAZADAS: {len(rejected_signals)}

RESUMEN DE RIESGO:
{json.dumps(risk_summary, ensure_ascii=False, indent=2)}

PLAN DE EJECUCIÓN:
{json.dumps(execution_plan[:5], ensure_ascii=False, indent=2)}

{backtest_summary}
{paper_summary}

{lessons_ctx}

¿Es seguro ejecutar este plan? ¿Qué ajustes recomiendas para maximizar
la preservación de capital mientras capturamos oportunidades reales?"""

        ai_synthesis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=700)

        # Guardar lección sobre el plan de ejecución
        if approved_signals:
            try:
                save_lesson(
                    lesson_type="signal_accuracy",
                    agent=self.name,
                    context=f"Plan de ejecución con {len(approved_signals)} señales aprobadas",
                    lesson=(
                        f"Ejecutadas {len(approved_signals)} de {len(signals)} señales recibidas. "
                        f"Rechazadas {len(rejected_signals)} por criterios de riesgo. "
                        f"Capital asignado: ${sum(p.get('capital_assigned', 0) for p in execution_plan):,.2f}."
                    ),
                    confidence=0.75,
                )
            except Exception as e:
                self.log(f"Error guardando lección: {e}")

        self.log(
            f"[MANAGER] Ejecución completada. "
            f"Aprobadas: {len(approved_signals)} | "
            f"Rechazadas: {len(rejected_signals)}"
        )

        return {
            "agent_results": agent_results,
            "execution_plan": execution_plan,
            "approved_signals": approved_signals,
            "rejected_signals": rejected_signals,
            "risk_summary": risk_summary,
            "ai_synthesis": ai_synthesis,
        }

    def _filter_signals(
        self,
        signals: List[Dict],
        agent_results: Dict,
    ) -> tuple:
        """Filtra señales en aprobadas y rechazadas según criterios de riesgo."""
        approved = []
        rejected = []

        for signal in signals:
            action = signal.get("action", "HOLD").upper()
            confidence = float(signal.get("confidence", 0))
            price = float(signal.get("current_price") or signal.get("price", 0))
            target = float(signal.get("target") or signal.get("price_target", 0))
            stop = float(signal.get("stop") or signal.get("stop_loss", 0))

            reject_reason = None

            # Filtros básicos
            if action not in ("BUY", "SELL"):
                reject_reason = f"Acción '{action}' no ejecutable"
            elif action == "BUY" and confidence < 0.5:
                reject_reason = f"Confianza insuficiente: {confidence:.0%} < 50%"
            elif action == "BUY" and price > 0 and target > 0 and stop > 0:
                # Verificar ratio riesgo/recompensa mínimo 1.5x
                risk = abs(price - stop)
                reward = abs(target - price)
                rr_ratio = (reward / risk) if risk > 0 else 0
                if rr_ratio < 1.5:
                    reject_reason = f"Ratio R/R insuficiente: {rr_ratio:.2f}x < 1.5x"

            if reject_reason:
                signal_copy = dict(signal)
                signal_copy["reject_reason"] = reject_reason
                rejected.append(signal_copy)
            else:
                approved.append(signal)

        return approved, rejected

    def _build_execution_plan(
        self,
        approved_signals: List[Dict],
        capital: float,
        agent_results: Dict,
    ) -> List[Dict]:
        """Construye el plan detallado de ejecución con asignación de capital."""
        plan = []
        remaining_capital = capital

        # Ordenar por confianza descendente
        sorted_signals = sorted(
            approved_signals,
            key=lambda x: float(x.get("confidence", 0)),
            reverse=True,
        )

        for i, signal in enumerate(sorted_signals):
            action = signal.get("action", "HOLD").upper()
            symbol = signal.get("symbol", "?")
            confidence = float(signal.get("confidence", 0))
            price = float(signal.get("current_price") or signal.get("price", 0))

            # Calcular capital a asignar (max 5% por señal, reducido por confianza)
            base_pct = min(0.05, confidence * 0.06)
            capital_assigned = min(remaining_capital * base_pct, remaining_capital * 0.20)

            if action == "BUY" and capital_assigned < 10:
                continue

            plan.append({
                "order": i + 1,
                "symbol": symbol,
                "action": action,
                "price": price,
                "confidence": confidence,
                "capital_assigned": round(capital_assigned, 2),
                "priority": "HIGH" if confidence > 0.75 else "MEDIUM" if confidence > 0.6 else "LOW",
            })

            if action == "BUY":
                remaining_capital -= capital_assigned

        return plan

    def _build_risk_summary(self, risk_result: Dict, portfolio_result: Dict) -> Dict:
        """Consolida el resumen de riesgo de los agentes relevantes."""
        summary = {}

        if risk_result and "error" not in risk_result:
            summary["overall_risk"] = risk_result.get("risk_level", "MEDIO")
            summary["max_drawdown"] = risk_result.get("max_drawdown", 0)
            summary["portfolio_exposure"] = risk_result.get("total_exposure_pct", 0)

        if portfolio_result and "error" not in portfolio_result:
            summary["portfolio_health"] = portfolio_result.get("health_score", "N/A")
            summary["concentration_risk"] = portfolio_result.get("concentration_risk", "N/A")

        return summary
