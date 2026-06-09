"""Coordinador central: orquesta todos los agentes y genera el informe final."""
import json
from datetime import datetime
from typing import Dict, List, Optional
from agents.base import BaseAgent
from agents.market_agent import MarketAgent
from agents.crypto_agent import CryptoAgent
from agents.news_agent import NewsAgent
from agents.tech_agent import TechAgent
from agents.learning_engine import LearningEngine
from memory.database import save_report, get_portfolio, get_pending_signals, get_lessons

SYSTEM_PROMPT = """Eres el director de inversiones personal de un inversor particular.
Coordinas un equipo de analistas especializados y produces informes ejecutivos claros.

Tu estilo:
- Directo y práctico: qué hacer, cuándo, por qué
- Honesto sobre incertidumbres y riesgos
- Prioriza la preservación del capital sobre las ganancias
- Considera siempre el perfil del inversor (particular, no institucional)
- Piensa a largo plazo pero aprovecha oportunidades a corto

Nunca das consejos como si fueras un asesor financiero certificado.
Siempre recuerdas que esto es análisis asistido por IA, no asesoramiento financiero oficial.
Responde en español.
"""


class InvestmentCoordinator(BaseAgent):
    name = "coordinator"
    description = "Orquesta todos los agentes y produce el informe ejecutivo"

    def __init__(self):
        super().__init__()
        self.agents = {
            "market": MarketAgent(),
            "crypto": CryptoAgent(),
            "news": NewsAgent(),
            "tech": TechAgent(),
            "learning": LearningEngine(),
        }

    def run_full_analysis(self, include_tech: bool = True,
                          include_learning: bool = True) -> Dict:
        """Ejecuta el ciclo completo de análisis."""
        print("\n" + "=" * 60)
        print("   ASISTENTE DE INVERSIÓN PERSONAL - ANÁLISIS COMPLETO")
        print(f"   {datetime.now().strftime('%A %d/%m/%Y %H:%M')}")
        print("=" * 60)

        results = {}

        # 1. Noticias (primero para contexto)
        print("\n[1/5] Analizando noticias del mercado...")
        results["news"] = self.agents["news"].run()

        # 2. Mercado de acciones
        print("\n[2/5] Analizando acciones y ETFs...")
        results["market"] = self.agents["market"].run()

        # 3. Criptomonedas
        print("\n[3/5] Analizando criptomonedas...")
        results["crypto"] = self.agents["crypto"].run()

        # 4. Tech Scout (opcional, consume rate limit de GitHub)
        if include_tech:
            print("\n[4/5] Escaneando herramientas GitHub...")
            results["tech"] = self.agents["tech"].run()
        else:
            print("\n[4/5] Tech scout omitido")
            results["tech"] = None

        # 5. Motor de aprendizaje
        if include_learning:
            print("\n[5/5] Ejecutando ciclo de aprendizaje...")
            results["learning"] = self.agents["learning"].run()
        else:
            print("\n[5/5] Aprendizaje omitido")
            results["learning"] = None

        # 6. Síntesis final con IA
        print("\n[COORDINADOR] Generando síntesis ejecutiva...")
        synthesis = self._generate_synthesis(results)

        # 7. Guardar informe
        save_report("daily", synthesis, {"agents_run": list(results.keys())})

        return {
            "results": results,
            "synthesis": synthesis,
            "timestamp": datetime.now().isoformat(),
        }

    def run_quick_scan(self) -> Dict:
        """Análisis rápido: solo precios y noticias (sin GitHub ni aprendizaje)."""
        print("\n[QUICK SCAN] Análisis rápido iniciado...")
        results = {
            "news": self.agents["news"].run(),
            "market": self.agents["market"].run(),
            "crypto": self.agents["crypto"].run(),
        }
        synthesis = self._generate_synthesis(results)
        return {"results": results, "synthesis": synthesis}

    def _generate_synthesis(self, results: Dict) -> str:
        """Genera el informe ejecutivo unificado."""
        # Recopilar señales accionables de todos los agentes
        all_signals = []
        if results.get("market"):
            all_signals.extend(results["market"].get("actionable_signals", []))
        if results.get("crypto"):
            all_signals.extend(results["crypto"].get("actionable_signals", []))

        buy_signals = [s for s in all_signals if s.get("action") == "BUY"]
        sell_signals = [s for s in all_signals if s.get("action") == "SELL"]
        watch_signals = [s for s in all_signals if s.get("action") == "WATCH"]

        # Portfolio actual
        portfolio = get_portfolio()
        pending_signals = get_pending_signals(days_old=7)

        # Construir contexto para IA
        mood = results.get("news", {}).get("market_mood", {})
        market_overview = results.get("market", {}).get("market_overview", {})

        if self.provider != "rules":
            lessons = self.get_lessons_context()

            signals_context = "\n".join([
                f"  COMPRA: {s.get('symbol','?')} @ {s.get('current_price', s.get('price', 0))} "
                f"(target: {s.get('target', '?')}, stop: {s.get('stop', '?')})"
                for s in buy_signals[:3]
            ] + [
                f"  VENTA: {s.get('symbol','?')} @ {s.get('current_price', s.get('price', 0))}"
                for s in sell_signals[:2]
            ] + [
                f"  VIGILAR: {s.get('symbol','?')}"
                for s in watch_signals[:3]
            ])

            portfolio_context = ""
            if portfolio:
                portfolio_context = "PORTFOLIO ACTUAL:\n" + "\n".join([
                    f"  {p['symbol']}: {p['quantity']} unidades @ {p['avg_buy_price']} avg"
                    for p in portfolio
                ])

            top_news = results.get("news", {}).get("high_impact_news", [])
            news_context = "\n".join([
                f"  [{a['sentiment']}] {a['title'][:100]}"
                for a in top_news[:5]
            ])

            tech_tools = ""
            if results.get("tech"):
                top_tools = results["tech"].get("top_repos", [])[:3]
                tech_tools = "\nHERRAMIENTAS GITHUB DESCUBIERTAS:\n" + "\n".join([
                    f"  {t['full_name']} ({t['stargazers_count']}⭐): {t['description'][:80]}"
                    for t in top_tools
                ])

            learning_summary = ""
            if results.get("learning"):
                lr = results["learning"]
                accuracy = lr.get("agent_accuracy", {})
                if accuracy:
                    best = max(accuracy.items(), key=lambda x: x[1]["win_rate"], default=None)
                    if best:
                        learning_summary = f"\nSISTEMA: Mejor agente actual: {best[0]} ({best[1]['win_rate']}% acierto)"

            full_response = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Genera el informe ejecutivo de inversión del día.

MOOD DE MERCADO: {mood.get('mood', 'NEUTRAL')} (score: {mood.get('score', 0)})
{mood.get('description', '')}

SEÑALES GENERADAS HOY:
{signals_context if signals_context else "  Sin señales accionables hoy"}

{portfolio_context}

NOTICIAS RELEVANTES:
{news_context if news_context else "  Sin noticias destacadas"}

{tech_tools}
{learning_summary}
SEÑALES PENDIENTES DE EVALUACIÓN: {len(pending_signals)}

Genera un informe ejecutivo en JSON con:
- "executive_summary": párrafo ejecutivo de 3-4 frases del día
- "market_diagnosis": diagnóstico del mercado actual
- "priority_actions": lista de 1-3 acciones prioritarias para el inversor (con símbolo, acción, razonamiento)
- "risk_level": nivel de riesgo del mercado (BAJO/MEDIO/ALTO) con explicación
- "portfolio_advice": consejo específico para el portfolio actual (si hay posiciones)
- "learning_note": nota sobre cómo el sistema está mejorando
- "disclaimer": recordatorio de que esto no es asesoramiento financiero oficial
""",
                max_tokens=2000
            )
            return full_response

        else:
            # Modo sin IA: informe basado en reglas
            return self._rules_based_report(buy_signals, sell_signals, watch_signals, mood)

    def _rules_based_report(self, buys, sells, watches, mood) -> str:
        lines = [
            "=" * 60,
            "INFORME EJECUTIVO - ANÁLISIS TÉCNICO",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "=" * 60,
            f"\nMOOD DEL MERCADO: {mood.get('mood', 'NEUTRAL')}",
            "",
        ]
        if buys:
            lines.append("SEÑALES DE COMPRA:")
            for s in buys:
                lines.append(f"  ▲ {s.get('symbol')} @ {s.get('current_price', s.get('price', 0))}")
        if sells:
            lines.append("\nSEÑALES DE VENTA:")
            for s in sells:
                lines.append(f"  ▼ {s.get('symbol')} @ {s.get('current_price', s.get('price', 0))}")
        if watches:
            lines.append("\nEN VIGILANCIA:")
            for s in watches:
                lines.append(f"  ◆ {s.get('symbol')}")

        lines.append(
            "\n⚠️ AVISO: Este análisis es orientativo. No constituye asesoramiento financiero."
        )
        return "\n".join(lines)
