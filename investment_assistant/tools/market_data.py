"""Datos de mercado via yfinance (100% gratuito, sin API key)."""
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def get_stock_info(symbol: str) -> Dict:
    """Obtiene info básica de una acción."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "prev_close": info.get("previousClose", 0),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", "")[:300],
            "currency": info.get("currency", "USD"),
            "volume": info.get("regularMarketVolume", 0),
            "avg_volume": info.get("averageVolume", 0),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "price": 0}


def get_ohlcv(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Descarga datos OHLCV históricos."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


def get_technical_signals(symbol: str) -> Dict:
    """Calcula señales técnicas básicas: RSI, MACD, Bollinger Bands."""
    df = get_ohlcv(symbol, period="6mo")
    if df.empty or len(df) < 30:
        return {"symbol": symbol, "error": "Datos insuficientes"}

    close = df["Close"]

    # RSI (14 periodos)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9).mean()
    macd_hist = macd - signal_line

    # Bollinger Bands (20 periodos)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + (std20 * 2)
    bb_lower = sma20 - (std20 * 2)

    # SMA 50 y 200
    sma50 = close.rolling(50).mean().iloc[-1] if len(df) >= 50 else None
    sma200 = close.rolling(200).mean().iloc[-1] if len(df) >= 200 else None

    current = close.iloc[-1]
    rsi_val = rsi.iloc[-1]

    # Señal consolidada
    signals = []
    score = 0

    if rsi_val < 30:
        signals.append("RSI sobrevendido (señal de compra)")
        score += 1
    elif rsi_val > 70:
        signals.append("RSI sobrecomprado (señal de venta)")
        score -= 1

    if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2]:
        signals.append("Cruce MACD alcista")
        score += 1
    elif macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2]:
        signals.append("Cruce MACD bajista")
        score -= 1

    if current < bb_lower.iloc[-1]:
        signals.append("Precio bajo Bollinger inferior (posible rebote)")
        score += 1
    elif current > bb_upper.iloc[-1]:
        signals.append("Precio sobre Bollinger superior (posible corrección)")
        score -= 1

    if sma50 and sma200:
        if sma50 > sma200 and current > sma50:
            signals.append("Golden Cross: tendencia alcista")
            score += 1
        elif sma50 < sma200:
            signals.append("Death Cross: tendencia bajista")
            score -= 1

    # Cambio en últimos periodos
    change_5d = (current / close.iloc[-5] - 1) * 100 if len(df) >= 5 else 0
    change_20d = (current / close.iloc[-20] - 1) * 100 if len(df) >= 20 else 0

    action = "HOLD"
    if score >= 2:
        action = "BUY"
    elif score <= -2:
        action = "SELL"
    elif score == 1:
        action = "WATCH"

    return {
        "symbol": symbol,
        "current_price": round(current, 2),
        "rsi": round(rsi_val, 1),
        "macd": round(macd.iloc[-1], 4),
        "macd_signal": round(signal_line.iloc[-1], 4),
        "macd_histogram": round(macd_hist.iloc[-1], 4),
        "bb_upper": round(bb_upper.iloc[-1], 2),
        "bb_lower": round(bb_lower.iloc[-1], 2),
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "change_5d_pct": round(change_5d, 2),
        "change_20d_pct": round(change_20d, 2),
        "signals": signals,
        "technical_score": score,
        "action": action,
    }


def get_multiple_stocks(symbols: List[str]) -> List[Dict]:
    """Obtiene precios de múltiples símbolos de una vez."""
    results = []
    try:
        data = yf.download(symbols, period="2d", group_by="ticker", auto_adjust=True, progress=False)
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    close = data["Close"]
                else:
                    close = data[sym]["Close"]
                if len(close) >= 2:
                    price = close.iloc[-1]
                    prev = close.iloc[-2]
                    change_pct = (price / prev - 1) * 100
                    results.append({
                        "symbol": sym,
                        "price": round(float(price), 2),
                        "change_pct": round(float(change_pct), 2),
                    })
            except Exception:
                results.append({"symbol": sym, "price": 0, "change_pct": 0})
    except Exception as e:
        for sym in symbols:
            results.append({"symbol": sym, "price": 0, "error": str(e)})
    return results


def get_market_overview() -> Dict:
    """Resumen del mercado: índices principales."""
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW JONES": "^DJI",
        "EURO STOXX 50": "^STOXX50E",
        "DAX": "^GDAXI",
        "IBEX 35": "^IBEX",
        "NIKKEI": "^N225",
        "ORO": "GC=F",
        "PETRÓLEO WTI": "CL=F",
        "EUR/USD": "EURUSD=X",
    }
    result = {}
    for name, symbol in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                price = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                pct = (price / prev - 1) * 100
                result[name] = {
                    "price": round(float(price), 2),
                    "change_pct": round(float(pct), 2),
                    "trend": "▲" if pct > 0 else "▼",
                }
        except Exception:
            result[name] = {"price": 0, "change_pct": 0, "trend": "-"}
    return result
