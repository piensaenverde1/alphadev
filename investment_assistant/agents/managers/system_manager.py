"""Manager 3: Coordina salud del sistema, aprendizaje, alertas y reportes."""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from agents.base import BaseAgent
from config.settings import DB_PATH
from memory.database import save_lesson, get_agent_accuracy, get_lessons

SYSTEM_PROMPT = """Eres el Director de Tecnología de un sistema de inversión con IA.
Tu función es asegurarte de que el sistema mejore continuamente y funcione con fiabilidad.

Responsabilidades:
1. Evaluar el rendimiento histórico del sistema de señales
2. Detectar si el sistema está mejorando o degradándose
3. Identificar qué agentes necesitan ajuste o más datos
4. Coordinar las notificaciones para no saturar al usuario
5. Gestionar el descubrimiento de nuevas herramientas útiles
6. Proponer cambios concretos para mejorar el sistema

Métricas que monitorizas:
- Win rate general: objetivo >55%
- Número de señales generadas: calidad > cantidad
- Lecciones aprendidas: ¿el sistema está evolucionando?
- Uptime: ¿todos los agentes funcionan correctamente?

Responde siempre en español. Sé técnico cuando hablas del sistema pero
accesible cuando das recomendaciones al usuario final.
"""

_TECH_CADENCE_DAYS = 7  # Cada cuántos días ejecutar TechAgent


class SystemManager(BaseAgent):
    name = "system_manager"
    description = "Manager del sistema: salud, aprendizaje, alertas y reportes integrados"

    def run(
        self,
        all_results: Dict = None,
        send_report: bool = True,
    ) -> Dict:
        self.log("[MANAGER] Iniciando gestión del sistema...")

        all_results = all_results or {}
        agent_results = {}

        # -- LearningEngine: evalúa señales pasadas y genera lecciones --
        self.log("[MANAGER] Ejecutando LearningEngine...")
        learning_result = {}
        try:
            from agents.learning_engine import LearningEngine
            learning_engine = LearningEngine()
            learning_result = learning_engine.run()
            agent_results["learning"] = learning_result
            new_lessons = learning_result.get("new_lessons", 0)
            self.log(f"[MANAGER] LearningEngine completado. Nuevas lecciones: {new_lessons}")
        except Exception as e:
            self.log(f"[MANAGER] LearningEngine falló: {e}")
            agent_results["learning"] = {"error": str(e)}

        # -- TechAgent: descubrimiento de herramientas GitHub (cadencia semanal) --
        tools_discovered = []
        should_run_tech = self._should_run_tech_agent()

        if should_run_tech:
            self.log("[MANAGER] Ejecutando TechAgent (cadencia semanal)...")
            try:
                from agents.tech_agent import TechAgent
                tech_agent = TechAgent()
                tech_result = tech_agent.run()
                agent_results["tech"] = tech_result
                tools_discovered = tech_result.get("new_tools", tech_result.get("tools", []))
                self._update_tech_last_run()
                self.log(f"[MANAGER] TechAgent completado. Herramientas: {len(tools_discovered)}")
            except Exception as e:
                self.log(f"[MANAGER] TechAgent falló: {e}")
                agent_results["tech"] = {"error": str(e)}
        else:
            self.log("[MANAGER] TechAgent omitido (ejecutado hace menos de 7 días)")
            agent_results["tech"] = {"skipped": True, "reason": "cadencia semanal no alcanzada"}

        # -- ReportAgent: genera el informe del día --
        report_result = {}
        report_generated = False
        if send_report:
            self.log("[MANAGER] Ejecutando ReportAgent...")
            try:
                from agents.specialists.report_agent import ReportAgent
                report_agent = ReportAgent()
                report_result = report_agent.run(
                    all_agent_results=all_results,
                    report_type="daily",
                )
                agent_results["report"] = report_result
                report_generated = report_result.get("saved", False)
                self.log(
                    f"[MANAGER] ReportAgent completado. "
                    f"Palabras: {report_result.get('word_count', 0)}"
                )
            except Exception as e:
                self.log(f"[MANAGER] ReportAgent falló: {e}")
                agent_results["report"] = {"error": str(e)}

        # -- AlertAgent: notificaciones de alta prioridad --
        self.log("[MANAGER] Ejecutando AlertAgent...")
        alert_result = {}
        alerts_sent = 0
        try:
            from agents.specialists.alert_agent import AlertAgent
            alert_agent = AlertAgent()

            # Extraer señales y portfolio de all_results para las alertas
            all_signals = self._extract_all_signals(all_results)
            portfolio_summary = all_results.get("portfolio_summary", {})
            market_mood = all_results.get("market_direction", "")

            alert_result = alert_agent.run(
                signals=all_signals,
                portfolio_summary=portfolio_summary if portfolio_summary else None,
                market_mood=market_mood if market_mood else None,
            )
            agent_results["alerts"] = alert_result
            alerts_sent = len(alert_result.get("alerts_sent", []))
            self.log(f"[MANAGER] AlertAgent completado. Alertas enviadas: {alerts_sent}")
        except Exception as e:
            self.log(f"[MANAGER] AlertAgent falló: {e}")
            agent_results["alerts"] = {"error": str(e)}

        # -- Calcular métricas de salud del sistema --
        self.log("[MANAGER] Calculando métricas de salud del sistema...")
        system_health = self._calculate_system_health(agent_results, all_results)

        # -- Resumen de aprendizaje --
        learning_summary = self._build_learning_summary(learning_result)

        # -- Síntesis de IA del sistema --
        self.log("[MANAGER] Generando síntesis de IA del sistema...")
        lessons_ctx = self.get_lessons_context()

        accuracy_stats = {}
        try:
            accuracy_stats = get_agent_accuracy()
        except Exception:
            pass

        user_message = f"""Revisión del estado del sistema de inversión:

SALUD DEL SISTEMA:
{json.dumps(system_health, ensure_ascii=False, indent=2)}

RESUMEN DE APRENDIZAJE:
{json.dumps(learning_summary, ensure_ascii=False, indent=2)}

PRECISIÓN POR AGENTE:
{json.dumps(accuracy_stats, ensure_ascii=False, indent=2)}

HERRAMIENTAS NUEVAS DESCUBIERTAS: {len(tools_discovered)}
INFORME GENERADO: {report_generated}
ALERTAS ENVIADAS: {alerts_sent}

AGENTES CON ERRORES: {[k for k, v in agent_results.items() if 'error' in v]}

{lessons_ctx}

¿Cómo está funcionando el sistema? ¿Está mejorando?
¿Qué cambios concretos recomiendas para mejorar el rendimiento?"""

        ai_synthesis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=800)

        # Guardar lección sobre el estado del sistema
        improving = system_health.get("trend") == "IMPROVING"
        try:
            save_lesson(
                lesson_type="market_pattern",
                agent=self.name,
                context="Revisión periódica del sistema",
                lesson=(
                    f"Sistema {'mejorando' if improving else 'estable/degradando'}. "
                    f"Señales hoy: {system_health.get('total_signals_today', 0)}. "
                    f"Nuevas lecciones: {learning_summary.get('new_lessons_count', 0)}. "
                    f"Precisión general: {system_health.get('overall_accuracy', 0):.1f}%."
                ),
                confidence=0.8 if improving else 0.5,
            )
        except Exception as e:
            self.log(f"Error guardando lección del sistema: {e}")

        self.log(
            f"[MANAGER] Sistema revisado. "
            f"Salud: {system_health.get('status', 'desconocido')} | "
            f"Tendencia: {system_health.get('trend', 'N/A')} | "
            f"Alertas: {alerts_sent}"
        )

        return {
            "agent_results": agent_results,
            "system_health": system_health,
            "learning_summary": learning_summary,
            "tools_discovered": tools_discovered,
            "report_generated": report_generated,
            "alerts_sent": alerts_sent,
            "ai_synthesis": ai_synthesis,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _should_run_tech_agent(self) -> bool:
        """Comprueba si han pasado al menos 7 días desde la última ejecución de TechAgent."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT MAX(first_seen) as last_run FROM github_tools
            """).fetchone()
            conn.close()

            if not row or not row["last_run"]:
                return True

            last_run = datetime.fromisoformat(str(row["last_run"]))
            return (datetime.now() - last_run) > timedelta(days=_TECH_CADENCE_DAYS)
        except Exception as e:
            self.log(f"Error comprobando cadencia TechAgent: {e}")
            return True  # En caso de duda, ejecutar

    def _update_tech_last_run(self):
        """No requiere acción explícita: TechAgent actualiza github_tools con last_updated."""
        pass

    def _extract_all_signals(self, all_results: Dict) -> List[Dict]:
        """Extrae todas las señales de todos los resultados de agentes."""
        signals = []
        for key, result in all_results.items():
            if not isinstance(result, dict):
                continue
            # Buscar señales en los resultados
            for signals_key in ("signals", "actionable_signals", "approved_signals"):
                found = result.get(signals_key, [])
                if isinstance(found, list):
                    signals.extend(found)
            # También buscar en agent_results anidados
            nested = result.get("agent_results", {})
            if isinstance(nested, dict):
                for nested_result in nested.values():
                    if isinstance(nested_result, dict):
                        for signals_key in ("signals", "actionable_signals"):
                            found = nested_result.get(signals_key, [])
                            if isinstance(found, list):
                                signals.extend(found)
        return signals

    def _calculate_system_health(
        self,
        agent_results: Dict,
        all_results: Dict,
    ) -> Dict:
        """Calcula métricas de salud del sistema."""
        total_agents = len(agent_results)
        failed_agents = [k for k, v in agent_results.items() if "error" in v]
        success_rate = ((total_agents - len(failed_agents)) / total_agents * 100) if total_agents > 0 else 0

        # Señales generadas hoy
        all_signals = self._extract_all_signals(all_results)
        total_signals_today = len(all_signals)

        # Precisión general
        overall_accuracy = 0.0
        try:
            accuracy = get_agent_accuracy()
            if accuracy:
                win_rates = [v.get("win_rate", 0) for v in accuracy.values()]
                overall_accuracy = sum(win_rates) / len(win_rates) if win_rates else 0.0
        except Exception:
            pass

        # Tendencia: ¿mejorando o degradando?
        trend = "STABLE"
        if overall_accuracy > 55:
            trend = "IMPROVING"
        elif overall_accuracy < 40:
            trend = "DEGRADING"

        # Estado general
        if success_rate >= 80 and trend != "DEGRADING":
            status = "HEALTHY"
        elif success_rate >= 60:
            status = "WARNING"
        else:
            status = "CRITICAL"

        return {
            "status": status,
            "trend": trend,
            "total_agents": total_agents,
            "failed_agents": failed_agents,
            "agent_success_rate": round(success_rate, 1),
            "total_signals_today": total_signals_today,
            "overall_accuracy": round(overall_accuracy, 1),
            "checked_at": datetime.now().strftime("%H:%M:%S"),
        }

    def _build_learning_summary(self, learning_result: Dict) -> Dict:
        """Construye resumen del motor de aprendizaje."""
        if not learning_result or "error" in learning_result:
            return {"new_lessons_count": 0, "evaluated_signals": 0, "status": "error"}

        return {
            "new_lessons_count": learning_result.get("new_lessons", 0),
            "evaluated_signals": learning_result.get("evaluated", 0),
            "wins": learning_result.get("wins", 0),
            "losses": learning_result.get("losses", 0),
            "top_lesson": learning_result.get("top_lesson", ""),
            "status": "ok",
        }
