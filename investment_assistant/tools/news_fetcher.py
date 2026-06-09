"""Noticias financieras via RSS feeds (100% gratuito, usa stdlib XML)."""
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import Dict, List, Optional
from config.settings import NEWS_FEEDS

# Palabras clave para análisis de sentimiento simple (sin IA)
POSITIVE_WORDS = {
    "surge", "gain", "rally", "bull", "growth", "profit", "beat", "rise",
    "soar", "jump", "climb", "boost", "record", "strong", "outperform",
    "upgrade", "buy", "positive", "success", "improve", "recover",
    "sube", "gana", "rally", "alcista", "crecimiento", "beneficio",
    "supera", "sólido", "mejora", "recupera", "positivo"
}

NEGATIVE_WORDS = {
    "crash", "fall", "drop", "bear", "loss", "miss", "decline", "plunge",
    "tumble", "sink", "weak", "downgrade", "sell", "negative", "fear",
    "recession", "layoff", "debt", "crisis", "collapse", "risk", "fail",
    "cae", "baja", "pérdida", "bajista", "recesión", "crisis", "riesgo",
    "quiebra", "débil", "negativo", "hundimiento"
}

# Símbolos de empresas conocidas en noticias
SYMBOL_KEYWORDS = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "meta": "META", "facebook": "META", "nvidia": "NVDA",
    "tesla": "TSLA", "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
    "asml": "ASML", "sap": "SAP", "samsung": "005930.KS",
    "fed": "MARKET", "federal reserve": "MARKET", "ecb": "MARKET",
    "interest rate": "MARKET", "inflation": "MARKET",
    "real estate": "REAL_ESTATE", "housing": "REAL_ESTATE",
    "inmobiliario": "REAL_ESTATE", "vivienda": "REAL_ESTATE",
}


def analyze_sentiment(text: str) -> tuple[str, float]:
    """Análisis de sentimiento simple basado en keywords."""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos_count + neg_count

    if total == 0:
        return "NEUTRAL", 0.0

    score = (pos_count - neg_count) / total
    if score > 0.2:
        return "POSITIVE", round(score, 2)
    elif score < -0.2:
        return "NEGATIVE", round(score, 2)
    else:
        return "NEUTRAL", round(score, 2)


def extract_symbols(text: str) -> List[str]:
    """Extrae símbolos financieros mencionados en el texto."""
    text_lower = text.lower()
    found = set()
    for keyword, symbol in SYMBOL_KEYWORDS.items():
        if keyword in text_lower:
            found.add(symbol)
    # Buscar ticker symbols directos ($AAPL, etc.)
    tickers = re.findall(r'\$([A-Z]{2,5})\b', text)
    found.update(tickers)
    return list(found)


def _parse_rss(feed_url: str, limit: int = 5) -> List[Dict]:
    """Parsea un RSS feed usando stdlib XML."""
    try:
        resp = requests.get(feed_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # Namespaces comunes en RSS/Atom
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "dc": "http://purl.org/dc/elements/1.1/",
        }

        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        source = ""
        channel = root.find(".//channel/title")
        if channel is not None and channel.text:
            source = channel.text[:40]
        if not source:
            source = feed_url.split("/")[2] if "/" in feed_url else feed_url

        entries = []
        for item in items[:limit]:
            title_el = item.find("title") or item.find("atom:title", ns)
            link_el = item.find("link") or item.find("atom:link", ns)
            desc_el = item.find("description") or item.find("summary") or item.find("atom:summary", ns)
            pub_el = item.find("pubDate") or item.find("dc:date", ns) or item.find("atom:published", ns)

            title = title_el.text if title_el is not None else ""
            url = (link_el.get("href") or link_el.text) if link_el is not None else ""
            desc = desc_el.text if desc_el is not None else ""
            pub = pub_el.text if pub_el is not None else ""

            # Limpiar HTML
            desc_clean = re.sub(r'<[^>]+>', '', desc or "")[:400]
            entries.append({
                "title": title or "",
                "url": url or "",
                "source": source,
                "summary": desc_clean,
                "published_at": pub,
            })
        return entries
    except Exception:
        return []


def fetch_news_from_feeds(feeds: List[str] = None, limit_per_feed: int = 5) -> List[Dict]:
    """Obtiene noticias de múltiples RSS feeds."""
    feeds = feeds or NEWS_FEEDS
    articles = []

    for feed_url in feeds:
        entries = _parse_rss(feed_url, limit_per_feed)
        for entry in entries:
            full_text = f"{entry['title']} {entry['summary']}"
            sentiment, score = analyze_sentiment(full_text)
            symbols = extract_symbols(full_text)
            articles.append({
                **entry,
                "sentiment": sentiment,
                "sentiment_score": score,
                "related_symbols": symbols,
            })

    # Ordenar por relevancia (sentimiento más extremo primero)
    articles.sort(key=lambda x: abs(x["sentiment_score"]), reverse=True)
    return articles


def get_trending_topics(articles: List[Dict]) -> Dict:
    """Analiza los temas más mencionados."""
    symbol_sentiment: Dict[str, List[float]] = {}

    for article in articles:
        for sym in article.get("related_symbols", []):
            if sym not in symbol_sentiment:
                symbol_sentiment[sym] = []
            symbol_sentiment[sym].append(article["sentiment_score"])

    result = {}
    for sym, scores in symbol_sentiment.items():
        avg = sum(scores) / len(scores)
        result[sym] = {
            "mentions": len(scores),
            "avg_sentiment": round(avg, 2),
            "sentiment": "POSITIVE" if avg > 0.1 else "NEGATIVE" if avg < -0.1 else "NEUTRAL"
        }

    return dict(sorted(result.items(), key=lambda x: x[1]["mentions"], reverse=True))


def get_market_mood(articles: List[Dict]) -> Dict:
    """Evalúa el mood general del mercado."""
    if not articles:
        return {"mood": "NEUTRAL", "score": 0, "description": "Sin datos"}

    scores = [a["sentiment_score"] for a in articles]
    avg = sum(scores) / len(scores)
    positive = sum(1 for s in scores if s > 0.2)
    negative = sum(1 for s in scores if s < -0.2)
    total = len(scores)

    if avg > 0.2:
        mood = "BULLISH"
        desc = f"Sentimiento positivo: {positive}/{total} noticias favorables"
    elif avg < -0.2:
        mood = "BEARISH"
        desc = f"Sentimiento negativo: {negative}/{total} noticias desfavorables"
    else:
        mood = "NEUTRAL"
        desc = "Mercado sin dirección clara"

    return {
        "mood": mood,
        "score": round(avg, 2),
        "positive_count": positive,
        "negative_count": negative,
        "total_articles": total,
        "description": desc,
    }
