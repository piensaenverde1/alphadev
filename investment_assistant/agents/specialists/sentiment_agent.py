"""Agente especialista en análisis de sentimiento avanzado."""
import json
from collections import Counter
from typing import Dict, List, Optional
from agents.base import BaseAgent
from tools.sentiment_advanced import AdvancedSentiment
from memory.database import save_lesson, get_portfolio

SYSTEM_PROMPT = """Eres un experto en finanzas conductuales que interpreta el sentimiento del mercado
para predecir movimientos de precios. Tu especialidad es leer entre líneas en las noticias
financieras y detectar cambios de sentimiento antes de que se reflejen en los precios.

Analiza los patrones de sentimiento con la siguiente metodología:
1. Identifica el estado emocional dominante del mercado (miedo, codicia, incertidumbre)
2. Detecta divergencias entre el sentimiento mediático y la realidad fundamental
3. Evalúa qué activos del portfolio están siendo más mencionados y con qué tono
4. Predice posibles movimientos basándote en ciclos de sentimiento históricos
5. Alerta sobre noticias de alto impacto que puedan mover el mercado esta semana

Responde siempre en español. Sé específico sobre qué activos comprar, mantener o vender
basándote únicamente en el análisis de sentimiento. Incluye niveles de convicción.
"""


class SentimentAgent(BaseAgent):
    name = "sentiment_specialist"
    description = "Análisis avanzado de sentimiento de mercado con NLP y finanzas conductuales"

    def run(self, texts: List[str] = None, articles: List[Dict] = None) -> Dict:
        self.log("Iniciando análisis de sentimiento avanzado...")

        # 1. Obtener textos si no se proporcionan
        if not texts and not articles:
            self.log("Obteniendo noticias recientes de la base de datos...")
            try:
                from memory.database import get_recent_news
                raw_news = get_recent_news(hours=24, limit=30)
                articles = raw_news if raw_news else []
                texts = [
                    f"{n.get('title', '')} {n.get('summary', '')}"
                    for n in articles if n.get('title')
                ]
            except Exception as e:
                self.log(f"Error obteniendo noticias: {e}")
                texts = []
                articles = []

        texts = texts or []
        articles = articles or []

        if not texts and articles:
            texts = [
                f"{a.get('title', '')} {a.get('summary', a.get('description', ''))}"
                for a in articles if a.get('title')
            ]

        self.log(f"Analizando sentimiento de {len(texts)} textos...")

        # 2. Análisis de sentimiento en lote
        sentiment_engine = AdvancedSentiment()
        batch_results = []
        if texts:
            try:
                batch_results = sentiment_engine.analyze_batch(texts)
            except Exception as e:
                self.log(f"Error en analyze_batch: {e}")
                batch_results = []

        # 3. Calcular puntuación general
        overall_score = 0.0
        if batch_results:
            scores = [r.get("score", 0.0) for r in batch_results]
            overall_score = round(sum(scores) / len(scores), 4)

        # Determinar sentimiento dominante
        if overall_score >= 0.15:
            dominant_sentiment = "BULLISH"
        elif overall_score <= -0.15:
            dominant_sentiment = "BEARISH"
        else:
            dominant_sentiment = "NEUTRAL"

        # 4. Extraer entidades financieras de todos los artículos
        all_tickers = []
        all_companies = []
        all_events = []

        for text in texts:
            try:
                entities = sentiment_engine.extract_financial_entities(text)
                all_tickers.extend(entities.get("tickers", []))
                all_companies.extend(entities.get("companies", []))
                all_events.extend(entities.get("events", []))
            except Exception as e:
                self.log(f"Error extrayendo entidades: {e}")

        # Mapa de frecuencia de entidades
        entity_map = {
            "tickers": dict(Counter(all_tickers).most_common(15)),
            "companies": dict(Counter(all_companies).most_common(10)),
            "events": dict(Counter(all_events).most_common(10)),
        }

        # 5. Comparar con holdings del portfolio
        portfolio_impact = {}
        try:
            portfolio = get_portfolio()
            portfolio_symbols = [p["symbol"].upper() for p in portfolio]

            for symbol in portfolio_symbols:
                # Buscar menciones directas
                mention_count = entity_map["tickers"].get(symbol, 0)

                # Calcular sentimiento específico para este símbolo
                symbol_texts = [
                    t for t in texts
                    if symbol.lower() in t.lower()
                ]
                symbol_sentiment = 0.0
                if symbol_texts:
                    symbol_results = sentiment_engine.analyze_batch(symbol_texts)
                    if symbol_results:
                        symbol_sentiment = round(
                            sum(r.get("score", 0) for r in symbol_results) / len(symbol_results),
                            4
                        )

                impact_label = "POSITIVO" if symbol_sentiment > 0.1 else \
                               "NEGATIVO" if symbol_sentiment < -0.1 else "NEUTRAL"

                portfolio_impact[symbol] = {
                    "mentions": mention_count,
                    "sentiment_score": symbol_sentiment,
                    "impact": impact_label,
                }
        except Exception as e:
            self.log(f"Error comparando con portfolio: {e}")

        # 6. Análisis de IA
        self.log("Generando análisis de IA sobre patrones de sentimiento...")
        lessons_ctx = self.get_lessons_context()

        top_events_str = ", ".join(
            f"{ev} ({cnt}x)" for ev, cnt in list(entity_map["events"].items())[:5]
        ) or "ninguno detectado"

        top_tickers_str = ", ".join(
            f"{tk} ({cnt}x)" for tk, cnt in list(entity_map["tickers"].items())[:8]
        ) or "ninguno detectado"

        portfolio_impact_str = json.dumps(portfolio_impact, ensure_ascii=False, indent=2) \
            if portfolio_impact else "Portfolio vacío"

        user_message = f"""Datos de análisis de sentimiento del mercado:

PUNTUACIÓN GENERAL DE SENTIMIENTO: {overall_score:+.4f}
SENTIMIENTO DOMINANTE: {dominant_sentiment}
ARTÍCULOS ANALIZADOS: {len(texts)}

EVENTOS FINANCIEROS DETECTADOS: {top_events_str}
TICKERS MÁS MENCIONADOS: {top_tickers_str}

IMPACTO EN PORTFOLIO:
{portfolio_impact_str}

DISTRIBUCIÓN DE SENTIMIENTO:
- Positivos: {sum(1 for r in batch_results if r.get('sentiment') == 'POSITIVE')}
- Negativos: {sum(1 for r in batch_results if r.get('sentiment') == 'NEGATIVE')}
- Neutrales: {sum(1 for r in batch_results if r.get('sentiment') == 'NEUTRAL')}

{lessons_ctx}

¿Qué nos dicen estos patrones de sentimiento sobre los movimientos del mercado esta semana?
¿Qué activos del portfolio deberían monitorearse más de cerca?"""

        ai_analysis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=800)

        # 7. Guardar lección si el sentimiento es extremo
        if abs(overall_score) > 0.4:
            direction = "alcista" if overall_score > 0 else "bajista"
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Sentimiento extremo detectado: {overall_score:+.4f}",
                    lesson=f"Sentimiento de mercado fuertemente {direction} ({overall_score:+.4f}). "
                           f"Eventos clave: {top_events_str[:100]}",
                    confidence=min(abs(overall_score), 1.0),
                )
            except Exception as e:
                self.log(f"Error guardando lección: {e}")

        self.log(f"Análisis completado. Sentimiento: {dominant_sentiment} ({overall_score:+.4f})")

        return {
            "overall_score": overall_score,
            "dominant_sentiment": dominant_sentiment,
            "entity_map": entity_map,
            "portfolio_impact": portfolio_impact,
            "articles_analyzed": len(texts),
            "sentiment_distribution": {
                "positive": sum(1 for r in batch_results if r.get("sentiment") == "POSITIVE"),
                "negative": sum(1 for r in batch_results if r.get("sentiment") == "NEGATIVE"),
                "neutral": sum(1 for r in batch_results if r.get("sentiment") == "NEUTRAL"),
            },
            "ai_analysis": ai_analysis,
        }
