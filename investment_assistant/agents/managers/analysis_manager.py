"""Manager 1: Coordina todos los agentes de inteligencia de mercado."""
import json
from typing import Dict, List, Optional
from agents.base import BaseAgent
from memory.database import save_lesson

SYSTEM_PROMPT = """Eres el Director de Inteligencia de Mercado de un sistema de inversión automatizado.
Tu función es sintetizar los informes de múltiples analistas especializados en una tesis
de inversión clara y accionable.

Proceso de síntesis:
1. Consolida datos de mercado de acciones, cripto, noticias, sentimiento y macro
2. Identifica convergencias y divergencias entre los diferentes análisis
3. Determina la dirección general del mercado con alta convicción
4. Selecciona las 5 mejores oportunidades priorizando riesgo/recompensa
5. Identifica los 3 riesgos principales que podrían invalidar el análisis
6. Rankea clases de activos por oportunidad actual

Lo más importante que debes comunicar al inversor es UNA idea central:
¿Qué debería hacer hoy con su dinero y por qué?

Responde siempre en español. Sé directo y evita la ambigüedad.
Nunca digas "depende" sin especificar de qué depende exactamente.
"""


class AnalysisManager(BaseAgent):
    name = "analysis_manager"
    description = "Manager de inteligencia de mercado: coordina análisis multi-activo"

    def run(self, scope: str = "full") -> Dict:
        self.log(f"[MANAGER] Iniciando análisis de mercado (scope: {scope})...")

        agent_results = {}

        # -- Agente de mercado (acciones/ETFs) --
        self.log("[MANAGER] Ejecutando MarketAgent...")
        try:
            from agents.market_agent import MarketAgent
            market_agent = MarketAgent()
            agent_results["market"] = market_agent.run()
            self.log("[MANAGER] MarketAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] MarketAgent falló: {e}")
            agent_results["market"] = {"error": str(e)}

        # -- Agente de cripto --
        self.log("[MANAGER] Ejecutando CryptoAgent...")
        try:
            from agents.crypto_agent import CryptoAgent
            crypto_agent = CryptoAgent()
            agent_results["crypto"] = crypto_agent.run()
            self.log("[MANAGER] CryptoAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] CryptoAgent falló: {e}")
            agent_results["crypto"] = {"error": str(e)}

        # -- Agente de noticias --
        self.log("[MANAGER] Ejecutando NewsAgent...")
        try:
            from agents.news_agent import NewsAgent
            news_agent = NewsAgent()
            agent_results["news"] = news_agent.run()
            self.log("[MANAGER] NewsAgent completado.")
        except Exception as e:
            self.log(f"[MANAGER] NewsAgent falló: {e}")
            agent_results["news"] = {"error": str(e)}

        # -- Agente de sentimiento (solo en scope full/deep) --
        if scope in ("full", "deep"):
            self.log("[MANAGER] Ejecutando SentimentAgent...")
            try:
                from agents.specialists.sentiment_agent import SentimentAgent
                sentiment_agent = SentimentAgent()
                agent_results["sentiment"] = sentiment_agent.run()
                self.log("[MANAGER] SentimentAgent completado.")
            except Exception as e:
                self.log(f"[MANAGER] SentimentAgent falló: {e}")
                agent_results["sentiment"] = {"error": str(e)}

            # -- Agente macro --
            self.log("[MANAGER] Ejecutando MacroAgent...")
            try:
                from agents.specialists.macro_agent import MacroAgent
                macro_agent = MacroAgent()
                agent_results["macro"] = macro_agent.run()
                self.log("[MANAGER] MacroAgent completado.")
            except Exception as e:
                self.log(f"[MANAGER] MacroAgent falló: {e}")
                agent_results["macro"] = {"error": str(e)}

            # -- Agente inmobiliario --
            self.log("[MANAGER] Ejecutando RealEstateAgent...")
            try:
                from agents.specialists.real_estate_agent import RealEstateAgent
                real_estate_agent = RealEstateAgent()
                agent_results["real_estate"] = real_estate_agent.run()
                self.log("[MANAGER] RealEstateAgent completado.")
            except Exception as e:
                self.log(f"[MANAGER] RealEstateAgent falló: {e}")
                agent_results["real_estate"] = {"error": str(e)}

        # -- Síntesis unificada --
        self.log("[MANAGER] Sintetizando resultados de todos los agentes...")

        # Recopilar todas las señales BUY de los agentes
        all_signals = []
        for agent_name, result in agent_results.items():
            if isinstance(result, dict) and "error" not in result:
                signals = result.get("signals", result.get("actionable_signals", []))
                if isinstance(signals, list):
                    all_signals.extend(signals)

        # Determinar dirección general del mercado
        market_direction = self._determine_market_direction(agent_results)

        # Top 5 oportunidades (BUY con mayor confianza)
        buy_signals = sorted(
            [s for s in all_signals if s.get("action", "").upper() == "BUY"],
            key=lambda x: float(x.get("confidence", 0)),
            reverse=True,
        )
        top_opportunities = [
            f"{s.get('symbol', '?')} ({float(s.get('confidence', 0)):.0%})"
            for s in buy_signals[:5]
        ]

        # Top 3 riesgos
        sell_signals = [s for s in all_signals if s.get("action", "").upper() == "SELL"]
        main_risks = []

        news_result = agent_results.get("news", {})
        if isinstance(news_result, dict) and "error" not in news_result:
            bearish_news = [
                n for n in news_result.get("top_news", [])
                if n.get("sentiment") == "NEGATIVE"
            ]
            for n in bearish_news[:2]:
                main_risks.append(n.get("title", "")[:80])

        for s in sell_signals[:max(0, 3 - len(main_risks))]:
            main_risks.append(f"SELL signal: {s.get('symbol', '?')} - {s.get('reasoning', '')[:60]}")

        # Ranking de clases de activos
        asset_class_rankings = self._rank_asset_classes(agent_results)

        # 7. Síntesis de IA profunda (solo en scope deep)
        self.log("[MANAGER] Generando síntesis de IA...")
        lessons_ctx = self.get_lessons_context()

        summary_data = {
            "market_direction": market_direction,
            "top_opportunities": top_opportunities,
            "main_risks": main_risks,
            "asset_class_rankings": asset_class_rankings,
            "total_buy_signals": len(buy_signals),
            "total_sell_signals": len(sell_signals),
            "agents_succeeded": [k for k, v in agent_results.items() if "error" not in v],
            "agents_failed": [k for k, v in agent_results.items() if "error" in v],
        }

        max_tokens = 1000 if scope == "deep" else 600
        user_message = f"""Como Director de Inteligencia de Mercado, sintetiza el siguiente análisis:

{json.dumps(summary_data, ensure_ascii=False, indent=2)}

Contexto adicional de análisis de mercado:
- Señales BUY disponibles: {len(buy_signals)}
- Señales SELL disponibles: {len(sell_signals)}
- Agentes de análisis activos: {len(summary_data['agents_succeeded'])}

{lessons_ctx}

¿Cuál es la información MÁS IMPORTANTE para un inversor individual hoy?
¿Qué debería hacer con su dinero en las próximas 24-48 horas?"""

        ai_synthesis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=max_tokens)

        # Síntesis adicional de análisis unificado
        unified_analysis = {
            "total_signals_analyzed": len(all_signals),
            "buy_signals_count": len(buy_signals),
            "sell_signals_count": len(sell_signals),
            "agents_active": len(summary_data["agents_succeeded"]),
            "agents_failed": summary_data["agents_failed"],
        }

        # Guardar lección si la dirección del mercado es significativa
        if market_direction in ("BULLISH", "BEARISH"):
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Dirección de mercado: {market_direction}",
                    lesson=(
                        f"Mercado identificado como {market_direction}. "
                        f"Top oportunidades: {', '.join(top_opportunities[:3])}. "
                        f"Riesgos: {', '.join(main_risks[:2])[:100] if main_risks else 'ninguno'}."
                    ),
                    confidence=0.7,
                )
            except Exception as e:
                self.log(f"Error guardando lección de mercado: {e}")

        self.log(
            f"[MANAGER] Análisis completado. "
            f"Dirección: {market_direction} | "
            f"Oportunidades: {len(top_opportunities)} | "
            f"Riesgos: {len(main_risks)}"
        )

        return {
            "agent_results": agent_results,
            "unified_analysis": unified_analysis,
            "market_direction": market_direction,
            "top_opportunities": top_opportunities,
            "main_risks": main_risks,
            "asset_class_rankings": asset_class_rankings,
            "ai_synthesis": ai_synthesis,
        }

    def _determine_market_direction(self, agent_results: Dict) -> str:
        """Determina la dirección general del mercado a partir de los resultados de los agentes."""
        bullish_votes = 0
        bearish_votes = 0

        # Voto del agente de mercado
        market_result = agent_results.get("market", {})
        if isinstance(market_result, dict) and "error" not in market_result:
            market_mood = market_result.get("market_mood", {})
            mood_name = market_mood.get("mood", "NEUTRAL") if isinstance(market_mood, dict) else "NEUTRAL"
            if mood_name in ("BULLISH",):
                bullish_votes += 2
            elif mood_name in ("BEARISH",):
                bearish_votes += 2

        # Voto del agente de sentimiento
        sentiment_result = agent_results.get("sentiment", {})
        if isinstance(sentiment_result, dict) and "error" not in sentiment_result:
            sent = sentiment_result.get("dominant_sentiment", "NEUTRAL")
            if sent == "BULLISH":
                bullish_votes += 1
            elif sent == "BEARISH":
                bearish_votes += 1

        # Voto de la ratio señales BUY vs SELL
        all_signals = []
        for result in agent_results.values():
            if isinstance(result, dict) and "error" not in result:
                sigs = result.get("signals", result.get("actionable_signals", []))
                if isinstance(sigs, list):
                    all_signals.extend(sigs)

        buys = sum(1 for s in all_signals if s.get("action", "").upper() == "BUY")
        sells = sum(1 for s in all_signals if s.get("action", "").upper() == "SELL")

        if buys > sells * 1.5:
            bullish_votes += 1
        elif sells > buys * 1.5:
            bearish_votes += 1

        if bullish_votes > bearish_votes:
            return "BULLISH"
        elif bearish_votes > bullish_votes:
            return "BEARISH"
        return "NEUTRAL"

    def _rank_asset_classes(self, agent_results: Dict) -> Dict:
        """Rankea clases de activos por oportunidad actual."""
        rankings = {}

        # Acciones
        market_result = agent_results.get("market", {})
        if isinstance(market_result, dict) and "error" not in market_result:
            buy_count = sum(
                1 for s in market_result.get("signals", [])
                if s.get("action", "").upper() == "BUY"
            )
            rankings["stocks"] = buy_count

        # Cripto
        crypto_result = agent_results.get("crypto", {})
        if isinstance(crypto_result, dict) and "error" not in crypto_result:
            buy_count = sum(
                1 for s in crypto_result.get("signals", [])
                if s.get("action", "").upper() == "BUY"
            )
            rankings["crypto"] = buy_count

        # Inmobiliario
        real_estate_result = agent_results.get("real_estate", {})
        if isinstance(real_estate_result, dict) and "error" not in real_estate_result:
            rankings["real_estate"] = real_estate_result.get("opportunity_score", 0)

        # Macro / Bonos
        macro_result = agent_results.get("macro", {})
        if isinstance(macro_result, dict) and "error" not in macro_result:
            rankings["macro"] = macro_result.get("bond_opportunity_score", 0)

        return dict(sorted(rankings.items(), key=lambda x: x[1], reverse=True))
