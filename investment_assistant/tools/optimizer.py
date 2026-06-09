import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except Exception:
    vbt = None
    VECTORBT_AVAILABLE = False


_FALLBACK_RSI = {
    "period": 14,
    "oversold": 30,
    "overbought": 70,
    "sharpe": None,
    "total_return_pct": None,
    "win_rate": None,
    "source": "default",
}

_FALLBACK_MACD = {
    "fast": 12,
    "slow": 26,
    "signal": 9,
    "sharpe": None,
    "total_return_pct": None,
    "win_rate": None,
    "source": "default",
}


def _fetch_close(symbol: str, period_years: int = 3) -> Optional[pd.Series]:
    if not YFINANCE_AVAILABLE:
        return None
    import datetime
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=int(period_years * 365.25))
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        col = "Close" if "Close" in df.columns else "close"
        series = df[col].dropna()
        return series if not series.empty else None
    except Exception:
        return None


def _synthetic_close(n: int = 756) -> pd.Series:
    rng = np.random.default_rng(0)
    returns = rng.normal(0.0003, 0.015, n)
    prices = 100.0 * np.exp(np.cumsum(returns))
    import datetime
    idx = pd.date_range(end=datetime.date.today(), periods=n, freq="B")
    return pd.Series(prices, index=idx, name="close")


def _rsi_series(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _macd_series(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def _portfolio_metrics_pandas(close: pd.Series, entries: pd.Series, exits: pd.Series) -> Dict:
    """Vectorised returns-based simulation; no position sizing, long-only."""
    position = pd.Series(0, index=close.index, dtype=float)
    in_pos = False
    entry_prices = []
    exit_prices = []

    for i in range(len(close)):
        if not in_pos and entries.iloc[i]:
            in_pos = True
            entry_prices.append(close.iloc[i])
        elif in_pos and exits.iloc[i]:
            in_pos = False
            exit_prices.append(close.iloc[i])
        position.iloc[i] = 1.0 if in_pos else 0.0

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0.0)
    equity = (1 + strat_ret).cumprod()

    sharpe = 0.0
    if strat_ret.std() > 0:
        sharpe = float(np.sqrt(252) * strat_ret.mean() / strat_ret.std())

    total_return_pct = float((equity.iloc[-1] - 1.0) * 100)

    pairs = list(zip(entry_prices, exit_prices))
    wins = [ep for ep, xp in pairs if xp > ep]
    win_rate = len(wins) / len(pairs) * 100 if pairs else 0.0

    return {
        "sharpe": round(sharpe, 4),
        "total_return_pct": round(total_return_pct, 4),
        "win_rate": round(win_rate, 4),
    }


def _vbt_portfolio_metrics(close: pd.Series, entries: pd.Series, exits: pd.Series) -> Dict:
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        freq="D",
        init_cash=10_000.0,
        fees=0.001,
    )
    sharpe = float(pf.sharpe_ratio() if not np.isnan(pf.sharpe_ratio()) else 0.0)
    total_return_pct = float(pf.total_return() * 100)
    trades = pf.trades.records_readable
    win_rate = 0.0
    if len(trades) > 0 and "PnL" in trades.columns:
        win_rate = float((trades["PnL"] > 0).mean() * 100)
    return {
        "sharpe": round(sharpe, 4),
        "total_return_pct": round(total_return_pct, 4),
        "win_rate": round(win_rate, 4),
    }


def _eval_metrics(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
) -> Dict:
    if VECTORBT_AVAILABLE:
        try:
            return _vbt_portfolio_metrics(close, entries, exits)
        except Exception:
            pass
    return _portfolio_metrics_pandas(close, entries, exits)


class ParameterOptimizer:
    def optimize_rsi(
        self,
        symbol: str,
        rsi_periods: List[int] = None,
        oversold: List[int] = None,
        overbought: List[int] = None,
    ) -> Dict:
        if rsi_periods is None:
            rsi_periods = [7, 10, 14, 21]
        if oversold is None:
            oversold = [20, 25, 30, 35]
        if overbought is None:
            overbought = [65, 70, 75, 80]

        close = _fetch_close(symbol)
        if close is None:
            close = _synthetic_close()
            source = "synthetic"
        else:
            source = "live"

        best: Optional[Dict] = None
        best_sharpe = float("-inf")

        for period, ob_low, ob_high in itertools.product(rsi_periods, oversold, overbought):
            if ob_low >= ob_high:
                continue
            try:
                rsi = _rsi_series(close, period)
                entries = (rsi < ob_low) & (rsi.shift(1) >= ob_low)
                exits = (rsi > ob_high) & (rsi.shift(1) <= ob_high)
                entries = entries.fillna(False)
                exits = exits.fillna(False)

                if entries.sum() < 1:
                    continue

                metrics = _eval_metrics(close, entries, exits)
                if metrics["sharpe"] > best_sharpe:
                    best_sharpe = metrics["sharpe"]
                    best = {
                        "period": period,
                        "oversold": ob_low,
                        "overbought": ob_high,
                        **metrics,
                        "source": source,
                    }
            except Exception:
                continue

        if best is None:
            result = {**_FALLBACK_RSI, "source": f"{source}_fallback"}
        else:
            result = best

        return result

    def optimize_macd(
        self,
        symbol: str,
        fast: List[int] = None,
        slow: List[int] = None,
        signal_periods: List[int] = None,
    ) -> Dict:
        if fast is None:
            fast = [8, 10, 12, 15]
        if slow is None:
            slow = [21, 26, 30]
        if signal_periods is None:
            signal_periods = [7, 9, 12]

        close = _fetch_close(symbol)
        if close is None:
            close = _synthetic_close()
            source = "synthetic"
        else:
            source = "live"

        best: Optional[Dict] = None
        best_sharpe = float("-inf")

        for f, s, sig in itertools.product(fast, slow, signal_periods):
            if f >= s:
                continue
            try:
                macd_line, signal_line = _macd_series(close, f, s, sig)
                # buy when MACD crosses above signal, sell when it crosses below
                entries = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
                exits = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
                entries = entries.fillna(False)
                exits = exits.fillna(False)

                if entries.sum() < 1:
                    continue

                metrics = _eval_metrics(close, entries, exits)
                if metrics["sharpe"] > best_sharpe:
                    best_sharpe = metrics["sharpe"]
                    best = {
                        "fast": f,
                        "slow": s,
                        "signal": sig,
                        **metrics,
                        "source": source,
                    }
            except Exception:
                continue

        if best is None:
            result = {**_FALLBACK_MACD, "source": f"{source}_fallback"}
        else:
            result = best

        return result

    def get_optimal_params(self, symbol: str) -> Dict:
        try:
            rsi_params = self.optimize_rsi(symbol)
        except Exception:
            rsi_params = {**_FALLBACK_RSI, "source": "error_fallback"}

        try:
            macd_params = self.optimize_macd(symbol)
        except Exception:
            macd_params = {**_FALLBACK_MACD, "source": "error_fallback"}

        return {
            "symbol": symbol,
            "rsi_params": rsi_params,
            "macd_params": macd_params,
        }

    def fallback_optimize(self, symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "rsi_params": {**_FALLBACK_RSI, "source": "default"},
            "macd_params": {**_FALLBACK_MACD, "source": "default"},
        }
