"""
Kelly Criterion + comprehensive risk management for the investment assistant.

All calculations are pure Python – no external libraries required.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional


class RiskManager:
    """
    Position sizing and portfolio risk management.

    Uses a half-Kelly Criterion for conservative position sizing and
    enforces hard limits on single-position concentration, sector
    concentration, and total portfolio risk.

    Parameters
    ----------
    capital : float
        Total account capital in base currency (e.g. EUR).
    max_risk_per_trade : float
        Maximum fraction of capital that can be risked on a single trade
        (default 2 %).
    max_portfolio_risk : float
        Maximum total portfolio risk across all open positions (default 20 %).
    """

    def __init__(
        self,
        capital: float,
        max_risk_per_trade: float = 0.02,
        max_portfolio_risk: float = 0.20,
    ) -> None:
        if capital <= 0:
            raise ValueError("capital must be positive")
        if not (0 < max_risk_per_trade <= 1):
            raise ValueError("max_risk_per_trade must be in (0, 1]")
        if not (0 < max_portfolio_risk <= 1):
            raise ValueError("max_portfolio_risk must be in (0, 1]")

        self.capital = capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk

    # ------------------------------------------------------------------
    # Kelly Criterion
    # ------------------------------------------------------------------

    def kelly_position_size(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
    ) -> float:
        """
        Calculate the half-Kelly optimal position size as a fraction of capital.

        Formula
        -------
        Full Kelly  = (W * b - L) / b
        Half Kelly  = Full Kelly / 2

        where
            W = win_rate
            L = 1 - win_rate   (loss rate)
            b = avg_win_pct / avg_loss_pct  (win/loss ratio)

        Returns
        -------
        float
            Fraction of capital to deploy, clamped to [0.0, 0.25].
        """
        if not (0.0 < win_rate < 1.0):
            raise ValueError("win_rate must be in (0, 1)")
        if avg_win_pct <= 0 or avg_loss_pct <= 0:
            raise ValueError("avg_win_pct and avg_loss_pct must be positive")

        loss_rate = 1.0 - win_rate
        b = avg_win_pct / avg_loss_pct  # reward-to-risk ratio

        full_kelly = (win_rate * b - loss_rate) / b
        half_kelly = full_kelly / 2.0

        return max(0.0, min(0.25, half_kelly))

    # ------------------------------------------------------------------
    # Position calculation
    # ------------------------------------------------------------------

    def calculate_position(
        self,
        signal: Dict,
        current_price: float,
        backtest_stats: Optional[Dict] = None,
    ) -> Dict:
        """
        Calculate recommended position size for a trade signal.

        Parameters
        ----------
        signal : dict
            Must contain at least 'symbol' and 'action' ('BUY'/'SELL').
            Optional keys: 'atr', 'sector', 'fractional' (bool for crypto).
        current_price : float
            Current asset price.
        backtest_stats : dict, optional
            Expected keys: 'win_rate', 'avg_win_pct', 'avg_loss_pct'.
            Falls back to conservative defaults when not provided.

        Returns
        -------
        dict with keys:
            recommended_shares    – int or float (fractional for crypto)
            recommended_value     – float (position value in base currency)
            max_loss_eur          – float (maximum loss if stop-loss is hit)
            risk_pct_of_capital   – float (risk as % of total capital)
            kelly_fraction        – float (half-Kelly fraction used)
            stop_loss_price       – float
            take_profit_price     – float
            sizing_reason         – str (human-readable explanation)
        """
        if current_price <= 0:
            raise ValueError("current_price must be positive")

        # Derive trade statistics from backtest or use conservative defaults
        if backtest_stats:
            win_rate = float(backtest_stats.get("win_rate", 0.55))
            avg_win = float(backtest_stats.get("avg_win_pct", 0.08))
            avg_loss = float(backtest_stats.get("avg_loss_pct", 0.05))
            data_source = "backtest statistics"
        else:
            win_rate = 0.55
            avg_win = 0.08
            avg_loss = 0.05
            data_source = "conservative defaults (55% win, 8% avg win, 5% avg loss)"

        kelly_fraction = self.kelly_position_size(win_rate, avg_win, avg_loss)

        # Stop-loss distance
        atr = signal.get("atr")
        stop_loss_price = self.get_stop_loss(
            current_price,
            atr=atr,
            method="volatility" if atr else "fixed",
        )
        stop_distance_pct = abs(current_price - stop_loss_price) / current_price
        stop_distance_pct = max(stop_distance_pct, 0.001)  # guard against near-zero

        # Position size via Kelly (fraction of total capital)
        kelly_value = self.capital * kelly_fraction

        # Position size via max-risk-per-trade (loss-limit approach):
        # max acceptable loss = capital * max_risk_per_trade
        # position_value * stop_distance = max_loss  =>  position_value = max_loss / stop_distance
        max_loss_allowed = self.capital * self.max_risk_per_trade
        risk_based_value = max_loss_allowed / stop_distance_pct

        # Conservative: always use the smaller of the two
        recommended_value = min(kelly_value, risk_based_value)
        recommended_value = max(0.0, recommended_value)

        # Number of shares: fractional for crypto/forex, integer for equities
        is_fractional = bool(signal.get("fractional", False))
        raw_shares = recommended_value / current_price
        recommended_shares: float = raw_shares if is_fractional else float(math.floor(raw_shares))

        # Recalculate actual value based on (possibly rounded) share count
        actual_value = recommended_shares * current_price
        max_loss_eur = actual_value * stop_distance_pct
        risk_pct_of_capital = (max_loss_eur / self.capital) * 100.0 if self.capital > 0 else 0.0

        # Take-profit: reward = risk * reward/risk ratio
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 2.0
        take_profit_price = current_price * (1.0 + stop_distance_pct * rr_ratio)

        sizing_reason = (
            f"Half-Kelly={kelly_fraction:.3f} "
            f"(win_rate={win_rate:.0%}, avg_win={avg_win:.0%}, avg_loss={avg_loss:.0%}); "
            f"risk_based_value=EUR{risk_based_value:.0f}; "
            f"stop_distance={stop_distance_pct:.2%}; "
            f"source={data_source}"
        )

        return {
            "recommended_shares": recommended_shares,
            "recommended_value": round(actual_value, 2),
            "max_loss_eur": round(max_loss_eur, 2),
            "risk_pct_of_capital": round(risk_pct_of_capital, 4),
            "kelly_fraction": round(kelly_fraction, 6),
            "stop_loss_price": round(stop_loss_price, 4),
            "take_profit_price": round(take_profit_price, 4),
            "sizing_reason": sizing_reason,
        }

    # ------------------------------------------------------------------
    # Portfolio-level risk check
    # ------------------------------------------------------------------

    def portfolio_risk_check(
        self,
        positions: List[Dict],
        new_signal: Dict,
    ) -> Dict:
        """
        Evaluate whether adding a new position breaches portfolio risk limits.

        Parameters
        ----------
        positions : list of dict
            Existing open positions. Each dict should contain:
            'symbol', 'value' (current market value), 'sector' (optional),
            'risk_pct' (optional, fraction of capital, e.g. 0.02 for 2 %).
        new_signal : dict
            Must contain 'symbol' and 'recommended_value'. Optional:
            'sector', 'risk_pct_of_capital' (as a percentage, e.g. 2.0).

        Returns
        -------
        dict with keys:
            approved              – bool
            reason                – str
            concentration_warning – bool
            correlation_warning   – bool
            total_risk_after      – float (fraction of capital at risk if trade approved)
        """
        symbol = new_signal.get("symbol", "UNKNOWN")
        new_value = float(new_signal.get("recommended_value", 0.0))

        # risk_pct_of_capital stored as a percentage (e.g. 2.0 = 2 %)
        raw_risk = float(new_signal.get("risk_pct_of_capital", self.max_risk_per_trade * 100))
        new_risk_frac = raw_risk / 100.0  # convert to fraction

        new_sector = new_signal.get("sector", "unknown").lower()

        existing_portfolio_value = sum(float(p.get("value", 0)) for p in positions)
        total_portfolio_value = existing_portfolio_value + new_value

        current_total_risk = self._total_risk_fraction(positions)

        # --- 1) Single-position concentration (> 20 % of total portfolio) ---
        position_concentration = (
            new_value / total_portfolio_value if total_portfolio_value > 0 else 0.0
        )
        if position_concentration > 0.20:
            return {
                "approved": False,
                "reason": (
                    f"Single position {symbol} would represent "
                    f"{position_concentration:.1%} of portfolio (limit 20 %)."
                ),
                "concentration_warning": True,
                "correlation_warning": False,
                "total_risk_after": round(current_total_risk + new_risk_frac, 6),
            }

        # --- 2) Sector concentration (> 40 % in one sector) ---
        sector_value = new_value + sum(
            float(p.get("value", 0))
            for p in positions
            if p.get("sector", "unknown").lower() == new_sector
        )
        sector_concentration = (
            sector_value / total_portfolio_value if total_portfolio_value > 0 else 0.0
        )
        if sector_concentration > 0.40:
            return {
                "approved": False,
                "reason": (
                    f"Sector '{new_sector}' would reach "
                    f"{sector_concentration:.1%} of portfolio (limit 40 %)."
                ),
                "concentration_warning": True,
                "correlation_warning": False,
                "total_risk_after": round(current_total_risk + new_risk_frac, 6),
            }

        # --- 3) Total portfolio risk (sum of all position risks > max_portfolio_risk) ---
        total_risk_after = current_total_risk + new_risk_frac
        if total_risk_after > self.max_portfolio_risk:
            return {
                "approved": False,
                "reason": (
                    f"Adding {symbol} would bring total portfolio risk to "
                    f"{total_risk_after:.1%}, exceeding the "
                    f"{self.max_portfolio_risk:.0%} limit."
                ),
                "concentration_warning": position_concentration > 0.15,
                "correlation_warning": False,
                "total_risk_after": round(total_risk_after, 6),
            }

        # --- 4) Correlation / duplicate warning ---
        correlation_warning = any(
            p.get("symbol", "").upper() == symbol.upper() for p in positions
        )

        return {
            "approved": True,
            "reason": "Position approved within all risk limits.",
            "concentration_warning": position_concentration > 0.15,
            "correlation_warning": correlation_warning,
            "total_risk_after": round(total_risk_after, 6),
        }

    # ------------------------------------------------------------------
    # Stop-loss calculation
    # ------------------------------------------------------------------

    def get_stop_loss(
        self,
        price: float,
        atr: Optional[float] = None,
        method: str = "fixed",
        price_history: Optional[List[float]] = None,
    ) -> float:
        """
        Calculate a stop-loss price for a long position.

        Parameters
        ----------
        price : float
            Current (entry) price.
        atr : float, optional
            Average True Range in price units.
        method : str
            'fixed'      – 2x ATR below price, or 5 % if ATR unavailable.
            'volatility' – 1.5x ATR below price (tighter volatility-based stop).
            'support'    – Nearest local support from price_history; falls back
                           to 'fixed' when history is unavailable.
        price_history : list of float, optional
            Recent closing prices; only used when method='support'.

        Returns
        -------
        float
            Stop-loss price, always at least 2 % below current price.
        """
        if price <= 0:
            raise ValueError("price must be positive")

        if method == "volatility":
            stop = (price - 1.5 * atr) if atr else price * 0.95
        elif method == "support":
            if price_history and len(price_history) >= 5:
                stop = self._nearest_support(price, price_history)
            elif atr:
                stop = price - 2.0 * atr
            else:
                stop = price * 0.95
        else:  # 'fixed' and any unrecognised method
            stop = (price - 2.0 * atr) if atr else price * 0.95

        # Never place stop within 2 % of entry (avoid noise-triggered exits)
        stop = min(stop, price * 0.98)
        return max(0.0, round(stop, 4))

    # ------------------------------------------------------------------
    # Batch sizing summary
    # ------------------------------------------------------------------

    def size_summary(self, capital: float, signals: List[Dict]) -> List[Dict]:
        """
        Apply position sizing to a list of signals and return a
        prioritised list (highest Kelly fraction first) with sizes attached.

        Parameters
        ----------
        capital : float
            Total available capital to deploy.
        signals : list of dict
            Each signal should contain at least:
            'symbol', 'action', 'current_price'.
            Optional: 'backtest_stats', 'atr', 'confidence', 'fractional'.

        Returns
        -------
        list of dict
            Input signals sorted by kelly_fraction descending, each
            augmented with all keys returned by calculate_position().
        """
        self.capital = capital  # refresh capital for this batch
        results: List[Dict] = []

        for sig in signals:
            try:
                price = float(sig.get("current_price", 0))
                if price <= 0:
                    results.append({**sig, "sizing_reason": "Skipped: invalid price"})
                    continue
                sizing = self.calculate_position(
                    signal=sig,
                    current_price=price,
                    backtest_stats=sig.get("backtest_stats"),
                )
                results.append({**sig, **sizing})
            except Exception as exc:
                results.append({**sig, "sizing_reason": f"Error during sizing: {exc}"})

        # Sort by Kelly fraction descending (highest-conviction trades first)
        results.sort(
            key=lambda x: x.get("kelly_fraction", 0.0),
            reverse=True,
        )
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _total_risk_fraction(self, positions: List[Dict]) -> float:
        """Sum the risk fractions of all existing positions."""
        total = 0.0
        for p in positions:
            rp = float(p.get("risk_pct", p.get("risk_pct_of_capital", 0.0)))
            # Normalise: values > 1.0 are assumed to be percentages (e.g. 2.0 → 0.02)
            if rp > 1.0:
                rp /= 100.0
            total += rp
        return total

    @staticmethod
    def _nearest_support(price: float, price_history: List[float]) -> float:
        """
        Estimate the nearest support level from recent closing prices.

        Identifies local price minima (values lower than both neighbours)
        and returns the highest one that is still below current price,
        with a small 1 % buffer.
        """
        if len(price_history) < 3:
            return price * 0.95

        local_mins = [
            price_history[i]
            for i in range(1, len(price_history) - 1)
            if price_history[i] < price_history[i - 1]
            and price_history[i] < price_history[i + 1]
        ]

        candidates = [m for m in local_mins if m < price]
        if not candidates:
            return price * 0.95

        # Closest support from below, with 1 % buffer
        return max(candidates) * 0.99
