import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
except ImportError:
    bt = None
    BACKTRADER_AVAILABLE = False

try:
    from memory.database import save_lesson
except ImportError:
    def save_lesson(*args, **kwargs):
        pass


def _compute_sharpe(daily_returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    if daily_returns.empty or daily_returns.std() == 0:
        return 0.0
    excess = daily_returns - risk_free_rate / 252
    return float(np.sqrt(252) * excess.mean() / excess.std())


def _compute_max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return float(drawdown.min() * 100)


def _fetch_data(symbol: str, period_years: int) -> Optional[pd.DataFrame]:
    if not YFINANCE_AVAILABLE:
        return None
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=int(period_years * 365.25))
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={c: c.lower() for c in df.columns})
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            return None
        return df.dropna()
    except Exception:
        return None


def _synthetic_data(period_years: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = int(period_years * 252)
    returns = rng.normal(0.0003, 0.015, n)
    close = 100.0 * np.exp(np.cumsum(returns))
    idx = pd.date_range(end=datetime.date.today(), periods=n, freq="B")
    df = pd.DataFrame(
        {
            "open": close * (1 - rng.uniform(0, 0.005, n)),
            "high": close * (1 + rng.uniform(0, 0.01, n)),
            "low": close * (1 - rng.uniform(0, 0.01, n)),
            "close": close,
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
        },
        index=idx,
    )
    return df


if BACKTRADER_AVAILABLE:
    class RSIMACDStrategy(bt.Strategy):
        params = (
            ("rsi_period", 14),
            ("macd_fast", 12),
            ("macd_slow", 26),
            ("macd_signal", 9),
            ("rsi_oversold", 30),
            ("rsi_overbought", 70),
        )

        def __init__(self):
            self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
            self.macd = bt.indicators.MACD(
                self.data.close,
                period1=self.params.macd_fast,
                period2=self.params.macd_slow,
                period_signal=self.params.macd_signal,
            )
            self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
            self.order = None

        def notify_order(self, order):
            if order.status in (order.Completed, order.Canceled, order.Margin):
                self.order = None

        def next(self):
            if self.order:
                return
            if not self.position:
                if self.rsi[0] < self.params.rsi_oversold and self.macd_cross[0] > 0:
                    self.order = self.buy()
            else:
                if self.rsi[0] > self.params.rsi_overbought or self.macd_cross[0] < 0:
                    self.order = self.sell()

    class BollingerStrategy(bt.Strategy):
        params = (
            ("period", 20),
            ("devfactor", 2.0),
            ("rsi_period", 14),
            ("rsi_oversold", 35),
        )

        def __init__(self):
            self.bbands = bt.indicators.BollingerBands(
                self.data.close,
                period=self.params.period,
                devfactor=self.params.devfactor,
            )
            self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
            self.order = None

        def notify_order(self, order):
            if order.status in (order.Completed, order.Canceled, order.Margin):
                self.order = None

        def next(self):
            if self.order:
                return
            if not self.position:
                if (
                    self.data.close[0] <= self.bbands.lines.bot[0]
                    and self.rsi[0] < self.params.rsi_oversold
                ):
                    self.order = self.buy()
            else:
                if self.data.close[0] >= self.bbands.lines.top[0]:
                    self.order = self.sell()

    class GoldenCrossStrategy(bt.Strategy):
        params = (
            ("fast_period", 50),
            ("slow_period", 200),
        )

        def __init__(self):
            self.sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
            self.sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
            self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
            self.order = None

        def notify_order(self, order):
            if order.status in (order.Completed, order.Canceled, order.Margin):
                self.order = None

        def next(self):
            if self.order:
                return
            if not self.position:
                if self.crossover[0] > 0:
                    self.order = self.buy()
            else:
                if self.crossover[0] < 0:
                    self.order = self.sell()

    class _TradeAnalyzer(bt.Analyzer):
        def __init__(self):
            self.trades = []

        def notify_trade(self, trade):
            if trade.isclosed:
                self.trades.append(trade.pnlcomm)

        def get_analysis(self):
            return self.trades

    class _EquityRecorder(bt.Analyzer):
        def __init__(self):
            self.equity = []

        def next(self):
            self.equity.append(self.strategy.broker.getvalue())

        def get_analysis(self):
            return self.equity

else:
    class RSIMACDStrategy:
        pass

    class BollingerStrategy:
        pass

    class GoldenCrossStrategy:
        pass

    class _TradeAnalyzer:
        pass

    class _EquityRecorder:
        pass


STRATEGIES: Dict[str, type] = {
    "rsi_macd": RSIMACDStrategy,
    "bollinger": BollingerStrategy,
    "golden_cross": GoldenCrossStrategy,
}


def _results_from_cerebro(
    cerebro: "bt.Cerebro",
    initial_cash: float,
    strategy_name: str,
    symbol: str,
) -> Dict:
    strat = cerebro.strats[0][0]
    trade_analyzer = strat.analyzers.trades
    equity_recorder = strat.analyzers.equity

    final_value = cerebro.broker.getvalue()
    total_return_pct = (final_value - initial_cash) / initial_cash * 100

    equity = pd.Series(equity_recorder.get_analysis(), dtype=float)
    daily_returns = equity.pct_change().dropna()
    sharpe = _compute_sharpe(daily_returns)
    max_dd = _compute_max_drawdown(equity)

    trading_days = len(equity)
    annual_return_pct = (
        ((final_value / initial_cash) ** (252 / max(trading_days, 1)) - 1) * 100
        if trading_days > 0
        else 0.0
    )

    trades = trade_analyzer.get_analysis()
    total_trades = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0.0
    avg_win_pct = float(np.mean(wins)) if wins else 0.0
    avg_loss_pct = float(np.mean(losses)) if losses else 0.0

    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "total_return_pct": round(total_return_pct, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "avg_win_pct": round(avg_win_pct, 4),
        "avg_loss_pct": round(avg_loss_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
    }


class BacktestEngine:
    def run(
        self,
        symbol: str,
        strategy_name: str,
        period_years: int = 2,
        cash: float = 10_000.0,
    ) -> Dict:
        if not BACKTRADER_AVAILABLE:
            return {
                "error": "backtrader not available",
                "symbol": symbol,
                "strategy": strategy_name,
            }

        strategy_cls = STRATEGIES.get(strategy_name)
        if strategy_cls is None:
            return {
                "error": f"unknown strategy '{strategy_name}'; choices: {list(STRATEGIES)}",
                "symbol": symbol,
            }

        df = _fetch_data(symbol, period_years)
        used_synthetic = False
        if df is None:
            df = _synthetic_data(period_years)
            used_synthetic = True

        try:
            data_feed = bt.feeds.PandasData(dataname=df)
            cerebro = bt.Cerebro()
            cerebro.adddata(data_feed)
            cerebro.addstrategy(strategy_cls)
            cerebro.broker.setcash(cash)
            cerebro.broker.setcommission(commission=0.001)
            cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
            cerebro.addanalyzer(_TradeAnalyzer, _name="trades")
            cerebro.addanalyzer(_EquityRecorder, _name="equity")
            cerebro.run()

            result = _results_from_cerebro(cerebro, cash, strategy_name, symbol)
            result["synthetic_data"] = used_synthetic

            try:
                save_lesson(
                    f"backtest_{symbol}_{strategy_name}",
                    f"Backtest result: {result}",
                )
            except Exception:
                pass

            return result

        except Exception as exc:
            return {"error": str(exc), "symbol": symbol, "strategy": strategy_name}

    def run_all_strategies(self, symbol: str) -> Dict[str, Dict]:
        results = {}
        for name in STRATEGIES:
            results[name] = self.run(symbol, name)
        return results

    def compare_strategies(self, symbols: List[str]) -> Dict:
        comparison = {}
        for symbol in symbols:
            all_results = self.run_all_strategies(symbol)
            valid = {
                name: res
                for name, res in all_results.items()
                if "error" not in res
            }
            if not valid:
                comparison[symbol] = {"best_strategy": None, "results": all_results}
                continue
            best = max(
                valid,
                key=lambda n: valid[n].get("sharpe_ratio", float("-inf")),
            )
            comparison[symbol] = {
                "best_strategy": best,
                "best_sharpe": valid[best].get("sharpe_ratio"),
                "best_total_return_pct": valid[best].get("total_return_pct"),
                "results": all_results,
            }
        return comparison

    def run_pandas(self, symbol: str, strategy: str = "rsi") -> Dict:
        df = _fetch_data(symbol, period_years=2)
        if df is None:
            df = _synthetic_data(2)
            used_synthetic = True
        else:
            used_synthetic = False

        close = df["close"]
        signals = self._pandas_rsi_signals(close)
        return self._pandas_backtest(close, signals, symbol, strategy, used_synthetic)

    @staticmethod
    def _pandas_rsi_signals(
        close: pd.Series,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - 100 / (1 + rs)

        position = pd.Series(0, index=close.index, dtype=int)
        in_position = False
        for i in range(len(rsi)):
            if np.isnan(rsi.iloc[i]):
                continue
            if not in_position and rsi.iloc[i] < oversold:
                in_position = True
            elif in_position and rsi.iloc[i] > overbought:
                in_position = False
            position.iloc[i] = 1 if in_position else 0
        return position

    @staticmethod
    def _pandas_backtest(
        close: pd.Series,
        signals: pd.Series,
        symbol: str,
        strategy: str,
        used_synthetic: bool,
        initial_cash: float = 10_000.0,
    ) -> Dict:
        returns = close.pct_change().fillna(0)
        strategy_returns = returns * signals.shift(1).fillna(0)

        equity = (1 + strategy_returns).cumprod() * initial_cash
        total_return_pct = float((equity.iloc[-1] / initial_cash - 1) * 100)
        sharpe = _compute_sharpe(strategy_returns)
        max_dd = _compute_max_drawdown(equity)

        n_days = len(equity)
        annual_return_pct = float(
            ((equity.iloc[-1] / initial_cash) ** (252 / max(n_days, 1)) - 1) * 100
        )
        n_trades = int((signals.diff().fillna(0) == 1).sum())

        return {
            "symbol": symbol,
            "strategy": strategy,
            "engine": "pandas",
            "total_return_pct": round(total_return_pct, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd, 4),
            "total_trades": n_trades,
            "win_rate": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "annual_return_pct": round(annual_return_pct, 4),
            "synthetic_data": used_synthetic,
        }
