"""Agente especialista en generación de informes de inversión."""
import json
from datetime import datetime
from typing import Dict, List, Optional
from agents.base import BaseAgent
from tools.telegram_notifier import TelegramNotifier
from memory.database import (
    save_lesson, save_report, get_portfolio,
    get_recent_news, get_agent_accuracy, get_lessons,
    get_pending_signals, get_top_github_tools,
)

SYSTEM_PROMPT = """Eres un periodista financiero especializado en inversión personal.
Tu misión es sintetizar datos complejos en informes claros, accionables y motivadores.

Estilo de redacción:
1. Claridad ante todo: un inversor no técnico debe entender cada sección
2. Accionable: cada sección debe terminar con una recomendación concreta
3. Honesto sobre la incertidumbre: no exageres la confianza en las predicciones
4. Contextualiza: explica por qué algo importa, no solo qué pasó
5. Brevedad en el resumen ejecutivo, detalle en las secciones específicas

Estructura del informe:
- Resumen ejecutivo (3-4 frases)
- Estado del mercado
- Situación del portfolio personal
- Señales top del día
- Evaluación de riesgo
- Progreso del sistema de aprendizaje
- Herramientas descubiertas (si aplica)

Responde siempre en español. Usa un tono profesional pero cercano.
"""

REPORT_TYPES = ("daily", "weekly", "signal_alert", "learning_summary")


class ReportAgent(BaseAgent):
    name = "report_specialist"
    description = "Genera informes de inversión completos y los distribuye vía Telegram"

    def run(
        self,
        all_agent_results: Dict = None,
        report_type: str = "daily",
    ) -> Dict:
        self.log(f"Generando informe tipo: {report_type}...")

        all_agent_results = all_agent_results or {}
        if report_type not in REPORT_TYPES:
            report_type = "daily"

        # 1. Recopilar datos de todas las fuentes disponibles
        self.log("Recopilando datos del sistema...")
        portfolio = []
        recent_signals = []
        recent_news = []
        accuracy_stats = {}
        learned_lessons = []
        github_tools = []

        try:
            portfolio = get_portfolio()
        except Exception as e:
            self.log(f"Error obteniendo portfolio: {e}")

        try:
            recent_signals = get_pending_signals(days_old=3)
        except Exception as e:
            self.log(f"Error obteniendo señales: {e}")

        try:
            recent_news = get_recent_news(hours=24, limit=10)
        except Exception as e:
            self.log(f"Error obteniendo noticias: {e}")

        try:
            accuracy_stats = get_agent_accuracy()
        except Exception as e:
            self.log(f"Error obteniendo estadísticas: {e}")

        try:
            learned_lessons = get_lessons(limit=5)
        except Exception as e:
            self.log(f"Error obteniendo lecciones: {e}")

        try:
            github_tools = get_top_github_tools(limit=3)
        except Exception as e:
            self.log(f"Error obteniendo herramientas GitHub: {e}")

        # 2. Construir secciones del informe
        sections = {}

        # Resumen ejecutivo (desde resultados de otros agentes si disponibles)
        market_direction = all_agent_results.get("market_direction", "NEUTRAL")
        top_opportunities = all_agent_results.get("top_opportunities", [])
        main_risks = all_agent_results.get("main_risks", [])

        sections["executive_summary"] = self._build_executive_summary(
            market_direction, top_opportunities, main_risks, portfolio
        )

        # Visión general del mercado
        sections["market_overview"] = self._build_market_overview(
            all_agent_results, recent_news
        )

        # Estado del portfolio
        sections["portfolio_status"] = self._build_portfolio_section(portfolio)

        # Top señales
        buy_signals = [
            s for s in recent_signals
            if s.get("action") == "BUY" and float(s.get("confidence", 0)) > 0.6
        ]
        sell_signals = [s for s in recent_signals if s.get("action") == "SELL"]
        sections["top_signals"] = self._build_signals_section(buy_signals, sell_signals)

        # Evaluación de riesgo
        sections["risk_assessment"] = self._build_risk_section(
            all_agent_results, portfolio
        )

        # Progreso de aprendizaje
        sections["learning_progress"] = self._build_learning_section(
            accuracy_stats, learned_lessons
        )

        # Herramientas GitHub descubiertas
        if github_tools:
            sections["github_tools_discovered"] = self._build_tools_section(github_tools)

        # 3. Síntesis de IA de todas las secciones
        self.log("Sintetizando informe con IA...")
        sections_text = "\n\n".join(
            f"=== {k.upper().replace('_', ' ')} ===\n{v}"
            for k, v in sections.items()
        )

        lessons_ctx = self.get_lessons_context()
        user_message = f"""Genera un informe de inversión {report_type} completo y coherente
basándote en las siguientes secciones de datos:

{sections_text}

{lessons_ctx}

Sintetiza toda esta información en un informe narrativo fluido, destacando
lo más importante para un inversor individual. Incluye siempre una
recomendación de acción concreta para las próximas 24-48 horas."""

        ai_analysis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=1200)

        # 4. Construir texto completo del informe
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        report_lines = [
            f"INFORME DE INVERSIÓN [{report_type.upper()}]",
            f"Fecha: {now_str}",
            "=" * 60,
            "",
        ]

        for section_name, section_content in sections.items():
            report_lines.append(f"## {section_name.replace('_', ' ').title()}")
            report_lines.append(section_content)
            report_lines.append("")

        report_lines.append("## Análisis Integrado")
        report_lines.append(ai_analysis)
        report_lines.append("")

        report_text = "\n".join(report_lines)
        word_count = len(report_text.split())

        # 5. Guardar informe en base de datos
        saved = False
        try:
            save_report(
                report_type=report_type,
                content=report_text,
                metadata={
                    "word_count": word_count,
                    "signals_count": len(recent_signals),
                    "portfolio_count": len(portfolio),
                    "market_direction": market_direction,
                    "generated_at": now_str,
                },
            )
            saved = True
            self.log(f"Informe guardado ({word_count} palabras)")
        except Exception as e:
            self.log(f"Error guardando informe: {e}")

        # 6. Enviar versión condensada por Telegram
        telegram = TelegramNotifier()
        telegram_sent = False
        if telegram.is_configured():
            self.log("Enviando informe condensado por Telegram...")
            try:
                signals_count = len(recent_signals)
                mood = market_direction.lower() if market_direction else "neutral"
                condensed = {
                    "summary": sections.get("executive_summary", "")[:300],
                    "top_actions": [
                        f"{s.get('symbol', '?')} → {s.get('action', '?')}"
                        for s in (buy_signals + sell_signals)[:3]
                    ],
                }
                telegram_sent = telegram.send_daily_report(
                    synthesis_json=json.dumps(condensed, ensure_ascii=False),
                    signals_count=signals_count,
                    mood=mood,
                )
            except Exception as e:
                self.log(f"Error enviando por Telegram: {e}")

        # 7. Guardar lección sobre la calidad del informe
        try:
            save_lesson(
                lesson_type="market_pattern",
                agent=self.name,
                context=f"Informe {report_type} generado",
                lesson=(
                    f"Informe {report_type} generado con {word_count} palabras. "
                    f"Dirección de mercado: {market_direction}. "
                    f"Señales activas: {len(recent_signals)}."
                ),
                confidence=0.6,
            )
        except Exception as e:
            self.log(f"Error guardando lección: {e}")

        self.log(f"Informe completado: {word_count} palabras | Guardado: {saved} | Telegram: {telegram_sent}")

        return {
            "report_text": report_text,
            "sections": sections,
            "report_type": report_type,
            "word_count": word_count,
            "saved": saved,
            "telegram_sent": telegram_sent,
        }

    # ------------------------------------------------------------------
    # Constructores de secciones
    # ------------------------------------------------------------------

    def _build_executive_summary(
        self,
        market_direction: str,
        opportunities: List,
        risks: List,
        portfolio: List,
    ) -> str:
        lines = [f"Mercado: {market_direction}"]
        if opportunities:
            tops = ", ".join(str(o) for o in opportunities[:3])
            lines.append(f"Oportunidades principales: {tops}")
        if risks:
            top_risks = ", ".join(str(r) for r in risks[:2])
            lines.append(f"Riesgos a vigilar: {top_risks}")
        lines.append(f"Activos en portfolio: {len(portfolio)}")
        return " | ".join(lines)

    def _build_market_overview(
        self,
        agent_results: Dict,
        news: List[Dict],
    ) -> str:
        lines = []
        asset_rankings = agent_results.get("asset_class_rankings", {})
        if asset_rankings:
            lines.append("Ranking de clases de activos:")
            for asset, score in sorted(
                asset_rankings.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  - {asset}: {score}")

        if news:
            lines.append(f"Noticias recientes ({len(news)}):")
            for n in news[:3]:
                sentiment = n.get("sentiment", "NEUTRAL")
                lines.append(f"  [{sentiment}] {n.get('title', '')[:80]}")

        return "\n".join(lines) if lines else "Sin datos de mercado disponibles"

    def _build_portfolio_section(self, portfolio: List[Dict]) -> str:
        if not portfolio:
            return "Portfolio vacío. Añade posiciones para seguimiento."
        lines = [f"Total de posiciones: {len(portfolio)}"]
        for p in portfolio[:5]:
            symbol = p.get("symbol", "?")
            qty = p.get("quantity", 0)
            avg_price = p.get("avg_buy_price", 0)
            lines.append(f"  - {symbol}: {qty:.4f} unidades @ {avg_price:.4f}")
        if len(portfolio) > 5:
            lines.append(f"  ... y {len(portfolio) - 5} más")
        return "\n".join(lines)

    def _build_signals_section(
        self,
        buy_signals: List[Dict],
        sell_signals: List[Dict],
    ) -> str:
        lines = []
        if buy_signals:
            lines.append(f"Señales de COMPRA ({len(buy_signals)}):")
            for s in buy_signals[:5]:
                conf = float(s.get("confidence", 0))
                price = s.get("price_at_signal", 0)
                lines.append(
                    f"  BUY {s.get('symbol', '?')} @ ${price:.2f} | "
                    f"Confianza: {conf:.0%} | {s.get('time_horizon', 'N/A')}"
                )

        if sell_signals:
            lines.append(f"Señales de VENTA ({len(sell_signals)}):")
            for s in sell_signals[:3]:
                lines.append(
                    f"  SELL {s.get('symbol', '?')} | "
                    f"Razón: {s.get('reasoning', 'N/A')[:60]}"
                )

        return "\n".join(lines) if lines else "Sin señales accionables actualmente"

    def _build_risk_section(self, agent_results: Dict, portfolio: List[Dict]) -> str:
        risk_summary = agent_results.get("risk_summary", {})
        lines = []

        if risk_summary:
            overall_risk = risk_summary.get("overall_risk", "MEDIO")
            lines.append(f"Nivel de riesgo general: {overall_risk}")

        concentration = {}
        for p in portfolio:
            asset_type = p.get("asset_type", "desconocido")
            concentration[asset_type] = concentration.get(asset_type, 0) + 1

        if concentration:
            lines.append("Concentración por tipo de activo:")
            for asset_type, count in concentration.items():
                lines.append(f"  - {asset_type}: {count} posiciones")

        return "\n".join(lines) if lines else "Análisis de riesgo no disponible"

    def _build_learning_section(
        self,
        accuracy: Dict,
        lessons: List[Dict],
    ) -> str:
        lines = []

        if accuracy:
            lines.append("Precisión de agentes:")
            for agent, stats in accuracy.items():
                win_rate = stats.get("win_rate", 0)
                total = stats.get("total", 0)
                lines.append(f"  - {agent}: {win_rate}% ({total} señales)")

        if lessons:
            lines.append(f"Últimas lecciones aprendidas ({len(lessons)}):")
            for lesson in lessons[:3]:
                lines.append(f"  - {lesson.get('lesson', '')[:80]}")

        return "\n".join(lines) if lines else "Sin datos de aprendizaje disponibles"

    def _build_tools_section(self, tools: List[Dict]) -> str:
        lines = ["Herramientas GitHub descubiertas:"]
        for tool in tools:
            name = tool.get("full_name") or tool.get("repo_name", "?")
            stars = tool.get("stars", 0)
            desc = tool.get("description", "")[:70]
            lines.append(f"  - {name} (⭐ {stars}): {desc}")
        return "\n".join(lines)
