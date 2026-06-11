"""
Coordinador central del sistema de inversión personal.

Arquitectura de 3 capas:
  Especialistas (9) → Managers (3) → Coordinador (1)

  AnalysisManager  – inteligencia de mercado (acciones, cripto, noticias, sentimiento, macro, inmobiliario)
  ExecutionManager – ejecución y riesgo (sizing, backtest, portfolio, opciones, paper trading)
  SystemManager    – salud del sistema (aprendizaje, alertas, tech scout, informe final)
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from agents.base import BaseAgent
from agents.managers.analysis_manager import AnalysisManager
from agents.managers.execution_manager import ExecutionManager
from agents.managers.system_manager import SystemManager
from memory.database import save_report, get_portfolio, get_pending_signals

SYSTEM_PROMPT = """Eres el director de inversiones personal de un inversor particular.
Recibes los informes de 3 managers especializados y produces la directiva final del día.

Tu estilo:
- Directo y práctico: qué hacer, cuándo, por qué
- Honesto sobre incertidumbres y riesgos
- Prioriza la preservación del capital sobre las ganancias
- Considera siempre el perfil del inversor (particular, no institucional)
- Piensa a largo plazo pero aprovecha oportunidades a corto

Nunca das consejos como si fueras un asesor financiero certificado.
Siempre recuerdas que esto es análisis asistido por IA, no asesoramiento financiero oficial.
Responde siempre en español.
"""


class InvestmentCoordinator(BaseAgent):
    name = "coordinator"
    description = "Orquesta los 3 managers y produce el informe ejecutivo definitivo"

    def __init__(self):
        super().__init__()
        self.analysis_mgr = AnalysisManager()
        self.execution_mgr = ExecutionManager()
        self.system_mgr = SystemManager()

    # ------------------------------------------------------------------
    # Pipeline principal (3 managers en secuencia)
    # ------------------------------------------------------------------

    def run_full_analysis(
        self,
        capital: float = 10000.0,
        include_tech: bool = True,
        include_learning: bool = True,
        include_backtest: bool = False,
        scope: str = "full",
    ) -> Dict:
        """
        Ciclo completo de análisis usando la arquitectura de 3 managers.

        Flujo:
          1. AnalysisManager  → inteligencia de mercado
          2. ExecutionManager → riesgo, sizing y ejecución
          3. SystemManager    → aprendizaje, alertas y reporte
          4. Coordinator      → síntesis ejecutiva final
        """
        print("\n" + "=" * 60)
        print("   ASISTENTE DE INVERSIÓN PERSONAL v3.0")
        print("   Arquitectura: 9 Especialistas | 3 Managers | 1 Coordinador")
        print(f"   {datetime.now().strftime('%A %d/%m/%Y %H:%M')}")
        print("=" * 60)

        # ── 1. ANALYSIS MANAGER ──────────────────────────────────────
        print("\n[1/3] ANALYSIS MANAGER: Inteligencia de mercado...")
        analysis_result = self.analysis_mgr.run(scope=scope)

        # Extraer señales consolidadas de todos los agentes de análisis
        all_signals: List[Dict] = []
        for agent_key, agent_data in analysis_result.get("agent_results", {}).items():
            if isinstance(agent_data, dict) and "error" not in agent_data:
                sigs = agent_data.get("actionable_signals", agent_data.get("signals", []))
                if isinstance(sigs, list):
                    all_signals.extend(sigs)

        print(
            f"       → Dirección: {analysis_result.get('market_direction', 'NEUTRAL')} | "
            f"Señales: {len(all_signals)}"
        )

        # ── 2. EXECUTION MANAGER ─────────────────────────────────────
        print("\n[2/3] EXECUTION MANAGER: Riesgo, sizing y ejecución...")
        execution_result = self.execution_mgr.run(
            signals=all_signals,
            capital=capital,
            run_backtest=include_backtest,
        )

        sized_signals = execution_result.get("sized_signals", [])
        approved = execution_result.get("approved_count", 0)
        print(
            f"       → Señales aprobadas: {approved} | "
            f"Capital desplegable: EUR {execution_result.get('deployable_capital', 0):.0f}"
        )

        # ── 3. SYSTEM MANAGER ────────────────────────────────────────
        print("\n[3/3] SYSTEM MANAGER: Aprendizaje, alertas y reporte...")
        all_intermediate = {
            **analysis_result.get("agent_results", {}),
            **execution_result.get("agent_results", {}),
            "market_direction": analysis_result.get("market_direction"),
            "top_opportunities": analysis_result.get("top_opportunities", []),
        }
        system_result = self.system_mgr.run(
            all_results=all_intermediate,
            send_report=True,
        )

        lessons_new = system_result.get("agent_results", {}).get("learning", {}).get("new_lessons", 0)
        print(f"       → Nuevas lecciones: {lessons_new}")

        # ── SÍNTESIS FINAL DEL COORDINADOR ───────────────────────────
        print("\n[COORDINADOR] Generando directiva ejecutiva final...")
        synthesis = self._generate_coordinator_synthesis(
            analysis_result=analysis_result,
            execution_result=execution_result,
            system_result=system_result,
            capital=capital,
        )

        save_report(
            "daily",
            synthesis,
            {
                "architecture": "3-manager",
                "capital": capital,
                "signals_total": len(all_signals),
                "signals_approved": approved,
                "market_direction": analysis_result.get("market_direction"),
            },
        )

        return {
            "synthesis": synthesis,
            "analysis": analysis_result,
            "execution": execution_result,
            "system": system_result,
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Análisis rápido (solo Analysis Manager)
    # ------------------------------------------------------------------

    def run_quick_scan(self) -> Dict:
        """Análisis rápido: solo mercado, cripto y noticias."""
        print("\n[QUICK SCAN] Análisis rápido iniciado...")
        analysis_result = self.analysis_mgr.run(scope="quick")
        synthesis = self._rules_quick_report(analysis_result)
        return {"results": analysis_result, "synthesis": synthesis}

    # ------------------------------------------------------------------
    # Síntesis ejecutiva del coordinador
    # ------------------------------------------------------------------

    def _generate_coordinator_synthesis(
        self,
        analysis_result: Dict,
        execution_result: Dict,
        system_result: Dict,
        capital: float,
    ) -> str:
        market_direction = analysis_result.get("market_direction", "NEUTRAL")
        top_opps = analysis_result.get("top_opportunities", [])
        main_risks = analysis_result.get("main_risks", [])
        sized_signals = execution_result.get("sized_signals", [])
        portfolio_data = execution_result.get("agent_results", {}).get("portfolio", {})
        learning_data = system_result.get("agent_results", {}).get("learning", {})
        pending_signals = get_pending_signals(days_old=7)

        if self.provider == "rules":
            return self._rules_based_report(
                top_opps, main_risks, market_direction, portfolio_data
            )

        lessons = self.get_lessons_context()

        # Construir contexto del portfolio
        portfolio = get_portfolio()
        portfolio_ctx = ""
        if portfolio:
            portfolio_ctx = "PORTFOLIO ACTUAL:\n" + "\n".join(
                f"  {p['symbol']}: {p['quantity']} u @ {p['avg_buy_price']} avg"
                for p in portfolio
            )

        # Top señales con sizing
        sizing_ctx = "\n".join(
            f"  {s.get('symbol','?')}: {s.get('recommended_shares', 0):.2f} acc "
            f"(EUR {s.get('recommended_value', 0):.0f}) "
            f"| stop={s.get('stop_loss_price', '?')} | target={s.get('take_profit_price', '?')}"
            for s in sized_signals[:3]
        ) or "  Sin señales dimensionadas"

        # Resumen de aprendizaje
        learning_ctx = ""
        if learning_data and learning_data.get("agent_accuracy"):
            acc = learning_data["agent_accuracy"]
            try:
                best = max(acc.items(), key=lambda x: x[1].get("win_rate", 0))
                learning_ctx = f"Mejor agente: {best[0]} ({best[1].get('win_rate', 0):.0f}% acierto)"
            except Exception:
                pass

        full_response = self.ask_ai(
            SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
            f"""Genera el informe ejecutivo final del día como director de inversiones.

RESUMEN DE LOS 3 MANAGERS:

[ANALYSIS MANAGER]
Dirección de mercado: {market_direction}
Top oportunidades: {', '.join(top_opps[:5]) or 'ninguna'}
Principales riesgos: {'; '.join(main_risks[:3]) or 'ninguno'}

[EXECUTION MANAGER]
Capital total: EUR {capital:,.0f}
Señales con sizing:
{sizing_ctx}

[SYSTEM MANAGER]
{learning_ctx or 'Sin datos de aprendizaje'}
Señales pendientes de evaluación: {len(pending_signals)}

{portfolio_ctx}

Genera el informe en JSON con:
- "executive_summary": párrafo ejecutivo de 3-4 frases del día
- "market_diagnosis": diagnóstico del mercado actual
- "priority_actions": lista de 1-3 acciones concretas (symbol, action, reasoning, sizing)
- "risk_level": BAJO/MEDIO/ALTO con explicación
- "portfolio_advice": consejo específico para el portfolio actual
- "learning_note": nota sobre cómo el sistema está mejorando
- "disclaimer": aviso legal de rigor
""",
            max_tokens=2000,
        )
        return full_response

    # ------------------------------------------------------------------
    # Informes sin IA
    # ------------------------------------------------------------------

    def _rules_based_report(self, top_opps, main_risks, direction, portfolio_data) -> str:
        lines = [
            "=" * 60,
            "INFORME EJECUTIVO - ANÁLISIS TÉCNICO (v3.0)",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "=" * 60,
            f"\nDIRECCIÓN DE MERCADO: {direction}",
            "",
        ]
        if top_opps:
            lines.append("TOP OPORTUNIDADES:")
            for opp in top_opps[:5]:
                lines.append(f"  ▲ {opp}")
        if main_risks:
            lines.append("\nRIESGOS PRINCIPALES:")
            for risk in main_risks[:3]:
                lines.append(f"  ⚠ {risk[:80]}")
        lines.append(
            "\nAVISO: Este análisis es orientativo. "
            "No constituye asesoramiento financiero oficial."
        )
        return "\n".join(lines)

    def _rules_quick_report(self, analysis_result: Dict) -> str:
        direction = analysis_result.get("market_direction", "NEUTRAL")
        opps = analysis_result.get("top_opportunities", [])
        return (
            f"[QUICK SCAN] {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"Dirección: {direction}\n"
            f"Oportunidades: {', '.join(opps[:3]) or 'ninguna'}\n"
            "⚠ Análisis orientativo. No es asesoramiento financiero."
        )
