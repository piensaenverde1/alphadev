import math
import numpy as np
from scipy.stats import norm
from typing import Dict, List, Optional


class OptionsAnalyzer:

    def price_option(
        self,
        S: float,
        K: float,
        T_days: float,
        r: float = 0.05,
        sigma: float = None,
        option_type: str = "call",
        price_history: List[float] = None,
    ) -> Dict:
        if sigma is None:
            sigma = self._estimate_sigma(price_history) if (price_history and len(price_history) >= 2) else 0.30

        T = T_days / 365.0

        if T <= 0:
            intrinsic = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
            atm = S > K if option_type == "call" else S < K
            return {
                "price": round(intrinsic, 6),
                "delta": 1.0 if (option_type == "call" and S > K) else (-1.0 if (option_type == "put" and S < K) else 0.0),
                "gamma": 0.0,
                "theta_per_day": 0.0,
                "vega": 0.0,
                "rho": 0.0,
                "intrinsic_value": round(intrinsic, 6),
                "time_value": 0.0,
            }

        if sigma <= 0:
            sigma = 1e-8

        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        nd1_pdf = norm.pdf(d1)
        disc = math.exp(-r * T)

        if option_type == "call":
            price = S * norm.cdf(d1) - K * disc * norm.cdf(d2)
            delta = float(norm.cdf(d1))
            rho = float(K * T * disc * norm.cdf(d2)) / 100.0
            theta_annual = (-(S * nd1_pdf * sigma) / (2 * sqrt_T)) - r * K * disc * norm.cdf(d2)
            intrinsic = max(S - K, 0.0)
        else:
            price = K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = float(norm.cdf(d1) - 1.0)
            rho = float(-K * T * disc * norm.cdf(-d2)) / 100.0
            theta_annual = (-(S * nd1_pdf * sigma) / (2 * sqrt_T)) + r * K * disc * norm.cdf(-d2)
            intrinsic = max(K - S, 0.0)

        gamma = float(nd1_pdf / (S * sigma * sqrt_T))
        vega = float(S * nd1_pdf * sqrt_T) / 100.0
        theta_per_day = float(theta_annual / 365.0)

        price = max(float(price), 0.0)
        time_value = max(price - intrinsic, 0.0)

        return {
            "price": round(price, 6),
            "delta": round(delta, 6),
            "gamma": round(gamma, 6),
            "theta_per_day": round(theta_per_day, 6),
            "vega": round(vega, 6),
            "rho": round(rho, 6),
            "intrinsic_value": round(intrinsic, 6),
            "time_value": round(time_value, 6),
        }

    def implied_volatility(
        self,
        market_price: float,
        S: float,
        K: float,
        T_days: float,
        r: float = 0.05,
        option_type: str = "call",
        precision: float = 1e-6,
        max_iterations: int = 200,
    ) -> float:
        T = T_days / 365.0
        if T <= 0:
            return 0.0

        intrinsic = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        if market_price <= intrinsic:
            return 0.0

        low, high = 1e-6, 10.0

        def _bs_price(s: float) -> float:
            return self.price_option(S, K, T_days, r, s, option_type)["price"]

        if _bs_price(high) < market_price:
            return high

        for _ in range(max_iterations):
            mid = (low + high) / 2.0
            mid_price = _bs_price(mid)
            if abs(mid_price - market_price) < precision:
                return round(mid, 6)
            if mid_price < market_price:
                low = mid
            else:
                high = mid

        return round((low + high) / 2.0, 6)

    def suggest_hedges(
        self,
        symbol: str,
        position_size: float,
        current_price: float,
        risk_tolerance: str = "medium",
    ) -> List[Dict]:
        tolerance_params = {
            "low":    {"put_strike_pct": 0.95, "call_strike_pct": 1.05, "expiry_days": 90},
            "medium": {"put_strike_pct": 0.90, "call_strike_pct": 1.10, "expiry_days": 60},
            "high":   {"put_strike_pct": 0.85, "call_strike_pct": 1.15, "expiry_days": 30},
        }
        params = tolerance_params.get(risk_tolerance, tolerance_params["medium"])
        sigma = 0.30
        r = 0.05

        put_strike = round(current_price * params["put_strike_pct"], 2)
        call_strike = round(current_price * params["call_strike_pct"], 2)
        expiry = params["expiry_days"]

        put_data = self.price_option(current_price, put_strike, expiry, r, sigma, "put")
        call_data = self.price_option(current_price, call_strike, expiry, r, sigma, "call")

        put_total_cost = put_data["price"] * position_size
        call_premium = call_data["price"] * position_size
        collar_net_cost = put_total_cost - call_premium

        protection_pct = (1.0 - params["put_strike_pct"]) * 100.0
        call_gain_pct = (params["call_strike_pct"] - 1.0) * 100.0
        covered_call_buffer_pct = round(call_data["price"] / current_price * 100.0, 2)

        return [
            {
                "strategy": "Protective Put",
                "symbol": symbol,
                "strike": put_strike,
                "expiry_days": expiry,
                "estimated_cost": round(put_total_cost, 2),
                "protection_pct": round(protection_pct, 2),
                "max_gain_pct": None,
                "description": f"Protege ante caídas mayores a {protection_pct:.0f}%",
            },
            {
                "strategy": "Covered Call",
                "symbol": symbol,
                "strike": call_strike,
                "expiry_days": expiry,
                "estimated_cost": round(-call_premium, 2),
                "protection_pct": covered_call_buffer_pct,
                "max_gain_pct": round(call_gain_pct + covered_call_buffer_pct, 2),
                "description": f"Genera ingreso; limita ganancia a ~{call_gain_pct:.0f}% sobre precio actual",
            },
            {
                "strategy": "Collar",
                "symbol": symbol,
                "put_strike": put_strike,
                "call_strike": call_strike,
                "expiry_days": expiry,
                "estimated_cost": round(collar_net_cost, 2),
                "protection_pct": round(protection_pct, 2),
                "max_gain_pct": round(call_gain_pct, 2),
                "description": (
                    f"Rango definido: protección -{protection_pct:.0f}% / ganancia máx +{call_gain_pct:.0f}%"
                ),
            },
        ]

    def options_chain_summary(self, symbol: str, current_price: float) -> Dict:
        strikes_pct = [-0.20, -0.10, 0.0, 0.10, 0.20]
        expiries = [30, 60, 90]
        r = 0.05
        sigma = 0.30

        strikes = [round(current_price * (1.0 + pct), 2) for pct in strikes_pct]
        chain: Dict = {"symbol": symbol, "underlying": current_price, "calls": {}, "puts": {}}

        for expiry in expiries:
            chain["calls"][expiry] = []
            chain["puts"][expiry] = []
            for strike in strikes:
                moneyness = round((current_price - strike) / strike * 100.0, 2)
                call = self.price_option(current_price, strike, expiry, r, sigma, "call")
                put = self.price_option(current_price, strike, expiry, r, sigma, "put")
                chain["calls"][expiry].append({"strike": strike, "moneyness_pct": moneyness, **call})
                chain["puts"][expiry].append({"strike": strike, "moneyness_pct": moneyness, **put})

        return chain

    def calculate_portfolio_greeks(self, positions: List[Dict]) -> Dict:
        totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

        for pos in positions:
            quantity = float(pos.get("quantity", 1))
            S = float(pos.get("underlying_price", 100.0))
            K = float(pos.get("strike", S))
            T_days = float(pos.get("T_days", 30))
            r = float(pos.get("r", 0.05))
            sigma = float(pos.get("sigma", 0.30))
            option_type = pos.get("option_type", "call")
            multiplier = float(pos.get("multiplier", 100))

            greeks = self.price_option(S, K, T_days, r, sigma, option_type)
            scale = quantity * multiplier

            totals["delta"] += greeks["delta"] * scale
            totals["gamma"] += greeks["gamma"] * scale
            totals["theta"] += greeks["theta_per_day"] * scale
            totals["vega"] += greeks["vega"] * scale

        return {k: round(v, 6) for k, v in totals.items()}

    def _estimate_sigma(self, price_history: List[float]) -> float:
        prices = np.array(price_history, dtype=float)
        log_returns = np.diff(np.log(prices))
        daily_vol = float(np.std(log_returns, ddof=1))
        return round(daily_vol * math.sqrt(252), 6)
