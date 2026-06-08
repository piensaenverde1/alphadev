"""Datos de criptomonedas via CoinGecko (100% gratuito, sin API key)."""
from pycoingecko import CoinGeckoAPI
from typing import Dict, List, Optional
import time

cg = CoinGeckoAPI()


def _safe_call(func, *args, retries=2, **kwargs):
    """Maneja rate limits de CoinGecko."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                time.sleep(60)
            else:
                return None
    return None


def get_top_coins(limit: int = 50, currency: str = "eur") -> List[Dict]:
    """Top N criptomonedas por capitalización."""
    data = _safe_call(
        cg.get_coins_markets,
        vs_currency=currency,
        order="market_cap_desc",
        per_page=limit,
        page=1,
        sparkline=False,
        price_change_percentage="24h,7d,30d"
    )
    if not data:
        return []
    return [{
        "id": c["id"],
        "symbol": c["symbol"].upper(),
        "name": c["name"],
        "price": c.get("current_price", 0),
        "market_cap": c.get("market_cap", 0),
        "market_cap_rank": c.get("market_cap_rank"),
        "volume_24h": c.get("total_volume", 0),
        "change_24h": c.get("price_change_percentage_24h", 0),
        "change_7d": c.get("price_change_percentage_7d_in_currency", 0),
        "change_30d": c.get("price_change_percentage_30d_in_currency", 0),
        "ath": c.get("ath", 0),
        "ath_change_pct": c.get("ath_change_percentage", 0),
    } for c in data]


def get_coin_detail(coin_id: str) -> Dict:
    """Detalles profundos de una cripto."""
    data = _safe_call(
        cg.get_coin_by_id,
        coin_id,
        localization=False,
        tickers=False,
        market_data=True,
        community_data=True,
        developer_data=True,
        sparkline=False
    )
    if not data:
        return {"id": coin_id, "error": "No encontrado"}

    market = data.get("market_data", {})
    dev = data.get("developer_data", {})
    community = data.get("community_data", {})

    return {
        "id": coin_id,
        "name": data.get("name"),
        "symbol": data.get("symbol", "").upper(),
        "description": data.get("description", {}).get("es", "")[:300]
                       or data.get("description", {}).get("en", "")[:300],
        "price_eur": market.get("current_price", {}).get("eur", 0),
        "price_usd": market.get("current_price", {}).get("usd", 0),
        "market_cap_eur": market.get("market_cap", {}).get("eur", 0),
        "volume_24h": market.get("total_volume", {}).get("eur", 0),
        "change_24h": market.get("price_change_percentage_24h", 0),
        "change_7d": market.get("price_change_percentage_7d", 0),
        "change_30d": market.get("price_change_percentage_30d", 0),
        "ath_eur": market.get("ath", {}).get("eur", 0),
        "ath_change": market.get("ath_change_percentage", {}).get("eur", 0),
        "circulating_supply": market.get("circulating_supply", 0),
        "max_supply": market.get("max_supply"),
        "github_stars": dev.get("stars", 0),
        "github_commits_4w": dev.get("commit_count_4_weeks", 0),
        "reddit_subscribers": community.get("reddit_subscribers", 0),
        "twitter_followers": community.get("twitter_followers", 0),
        "categories": data.get("categories", []),
    }


def get_crypto_history(coin_id: str, days: int = 30, currency: str = "eur") -> List[Dict]:
    """Historial de precios."""
    data = _safe_call(
        cg.get_coin_market_chart_by_id,
        coin_id,
        vs_currency=currency,
        days=days,
        interval="daily" if days > 7 else "hourly"
    )
    if not data:
        return []
    prices = data.get("prices", [])
    return [{"timestamp": p[0] / 1000, "price": p[1]} for p in prices]


def get_crypto_signals(coins: List[str]) -> List[Dict]:
    """Analiza señales de compra/venta para una lista de cryptos."""
    signals = []
    top = get_top_coins(limit=100)
    coin_map = {c["id"]: c for c in top}

    for coin_id in coins:
        coin = coin_map.get(coin_id)
        if not coin:
            continue

        score = 0
        reasons = []

        # Momentum: cambio 24h y 7d
        c24 = coin.get("change_24h", 0) or 0
        c7d = coin.get("change_7d", 0) or 0

        if c24 > 5:
            score += 1
            reasons.append(f"Momentum fuerte +{c24:.1f}% (24h)")
        elif c24 < -8:
            score -= 1
            reasons.append(f"Caída fuerte {c24:.1f}% (24h)")

        if c7d > 15:
            score += 1
            reasons.append(f"Tendencia semanal alcista +{c7d:.1f}%")
        elif c7d < -20:
            score -= 1
            reasons.append(f"Tendencia semanal bajista {c7d:.1f}%")

        # Distancia al ATH (oportunidad vs sobrecompra)
        ath_pct = coin.get("ath_change_pct", 0) or 0
        if ath_pct < -70:
            score += 1
            reasons.append(f"Muy alejado del ATH ({ath_pct:.0f}%) - potencial de recuperación")
        elif ath_pct > -10:
            score -= 1
            reasons.append(f"Cerca del ATH ({ath_pct:.0f}%) - riesgo de corrección")

        # Volumen (actividad)
        vol = coin.get("volume_24h", 0) or 0
        mcap = coin.get("market_cap", 1) or 1
        vol_ratio = vol / mcap
        if vol_ratio > 0.15:
            reasons.append(f"Volumen inusualmente alto ({vol_ratio:.1%} del market cap)")

        action = "HOLD"
        if score >= 2:
            action = "BUY"
        elif score == 1:
            action = "WATCH"
        elif score <= -2:
            action = "SELL"

        signals.append({
            "id": coin_id,
            "symbol": coin["symbol"],
            "name": coin["name"],
            "price": coin["price"],
            "change_24h": c24,
            "change_7d": c7d,
            "score": score,
            "action": action,
            "reasons": reasons,
            "rank": coin.get("market_cap_rank"),
        })

    return sorted(signals, key=lambda x: x["score"], reverse=True)


def get_global_crypto_stats() -> Dict:
    """Estadísticas globales del mercado crypto."""
    data = _safe_call(cg.get_global)
    if not data:
        return {}
    d = data.get("data", {})
    return {
        "total_market_cap_eur": d.get("total_market_cap", {}).get("eur", 0),
        "total_volume_eur": d.get("total_volume", {}).get("eur", 0),
        "btc_dominance": round(d.get("market_cap_percentage", {}).get("btc", 0), 1),
        "eth_dominance": round(d.get("market_cap_percentage", {}).get("eth", 0), 1),
        "active_coins": d.get("active_cryptocurrencies", 0),
        "market_cap_change_24h": round(d.get("market_cap_change_percentage_24h_usd", 0), 2),
    }
