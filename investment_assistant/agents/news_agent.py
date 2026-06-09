"""Agente de análisis de noticias financieras."""
from typing import Dict, List
from agents.base import BaseAgent
from tools.news_fetcher import fetch_news_from_feeds, get_trending_topics, get_market_mood
from memory.database import save_news, get_recent_news, save_lesson
from config.settings import NEWS_FEEDS

SYSTEM_PROMPT = """Eres un analista de noticias financieras experto en interpretar
el impacto de eventos macroeconómicos, políticos y corporativos en los mercados.

Tu objetivo:
1. Identificar noticias que pueden mover mercados significativamente
2. Distinguir entre ruido y señales reales
3. Detectar patrones y tendencias emergentes
4. Relacionar noticias con activos específicos afectados
5. Proporcionar contexto histórico cuando sea relevante

IMPORTANTE:
- Sé objetivo: no te dejes llevar por titulares alarmistas
- Considera múltiples perspectivas
- Indica el timeframe del impacto esperado
- Responde siempre en español
"""


class NewsAgent(BaseAgent):
    name = "news_analyst"
    description = "Analiza noticias financieras y evalúa su impacto en mercados"

    def run(self) -> Dict:
        self.log("Obteniendo noticias financieras...")

        # 1. Obtener noticias de todos los feeds
        articles = fetch_news_from_feeds(limit_per_feed=6)
        self.log(f"Obtenidas {len(articles)} noticias")

        # 2. Analizar mood del mercado
        mood = get_market_mood(articles)
        trending = get_trending_topics(articles)

        # 3. Guardar noticias en BD
        for art in articles:
            save_news(
                title=art["title"],
                url=art["url"],
                source=art["source"],
                sentiment=art["sentiment"],
                score=art["sentiment_score"],
                symbols=art["related_symbols"],
                summary=art["summary"],
                published=art["published_at"],
            )

        # 4. Noticias más impactantes
        high_impact = [a for a in articles if abs(a["sentiment_score"]) > 0.3]
        positive_news = [a for a in articles if a["sentiment"] == "POSITIVE"][:5]
        negative_news = [a for a in articles if a["sentiment"] == "NEGATIVE"][:5]

        # 5. Análisis con IA
        ai_analysis = ""
        event_impacts = []

        if articles and self.provider != "rules":
            lessons = self.get_lessons_context()
            top_news_text = "\n".join([
                f"  [{a['sentiment']}] {a['title']} (fuente: {a['source']})\n"
                f"  Resumen: {a['summary'][:150]}"
                for a in articles[:10]
            ])

            ai_analysis = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Analiza las siguientes noticias financieras recientes:

{top_news_text}

MOOD GENERAL: {mood['mood']} (score: {mood['score']})
TEMAS TRENDING: {', '.join(list(trending.keys())[:5])}

Proporciona análisis en JSON con:
- "summary": resumen de la situación en 2-3 frases
- "key_events": lista de 3 eventos más importantes con impacto esperado
- "affected_assets": activos más afectados y cómo
- "opportunity": si hay alguna oportunidad de inversión derivada de las noticias
- "risk_alert": alertas de riesgo detectadas
- "macro_outlook": perspectiva macro a corto plazo
""",
                max_tokens=1500
            )

            # Extraer eventos con impacto para aprendizaje
            try:
                import json
                parsed = json.loads(ai_analysis)
                for event in parsed.get("key_events", []):
                    event_impacts.append(event)
            except Exception:
                pass

        # 6. Auto-aprendizaje: guardar patrones detectados
        if mood["mood"] == "BEARISH" and mood["score"] < -0.4:
            save_lesson(
                lesson_type="news_pattern",
                agent=self.name,
                context=f"Mood muy bajista (score={mood['score']})",
                lesson="Cuando el sentiment de noticias es muy negativo (<-0.4), considerar reducir exposición a riesgo",
                confidence=0.6
            )
        elif mood["mood"] == "BULLISH" and mood["score"] > 0.4:
            save_lesson(
                lesson_type="news_pattern",
                agent=self.name,
                context=f"Mood muy alcista (score={mood['score']})",
                lesson="Mercados muy positivos en noticias pueden indicar euforia; precaución con compras en máximos",
                confidence=0.6
            )

        self.log(f"Análisis de noticias completado. Mood: {mood['mood']}")
        return {
            "agent": self.name,
            "market_mood": mood,
            "trending_topics": trending,
            "total_articles": len(articles),
            "high_impact_news": high_impact[:5],
            "positive_news": positive_news,
            "negative_news": negative_news,
            "event_impacts": event_impacts,
            "ai_analysis": ai_analysis,
        }
