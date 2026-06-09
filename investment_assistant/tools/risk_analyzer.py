import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional


class RiskAnalyzer:

    TRADING_DAYS_PER_YEAR = 252

    def analyze_returns(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series = None,
    ) -> Dict:
        returns = returns.dropna()
        if len(returns) < 2:
            raise ValueError("Need at least 2 data points.")

        ann_factor = self.TRADING_DAYS_PER_YEAR
        mean_daily = returns.mean()
        std_daily = returns.std(ddof=1)

        annual_return = self._annualized_return(returns)
        annual_volatility = std_daily * np.sqrt(ann_factor)

        rf_daily = 0.0
        sharpe = (mean_daily - rf_daily) / std_daily * np.sqrt(ann_factor) if std_daily > 0 else np.nan

        downside = returns[returns < 0]
        downside_std = downside.std(ddof=1) * np.sqrt(ann_factor) if len(downside) > 1 else np.nan
        sortino = annual_return / downside_std if (downside_std and downside_std > 0) else np.nan

        drawdown_df = self.drawdown_analysis(returns)
        max_dd = drawdown_df["depth_pct"].min() / 100.0 if not drawdown_df.empty else 0.0
        max_dd_duration = int(drawdown_df["duration_days"].max()) if not drawdown_df.empty else 0

        calmar = annual_return / abs(max_dd) if max_dd != 0 else np.nan

        var_95 = float(np.percentile(returns, 5))
        cvar_95 = float(returns[returns <= var_95].mean()) if (returns <= var_95).any() else var_95

        result: Dict = {
            "sharpe_ratio": round(float(sharpe), 4) if not np.isnan(sharpe) else None,
            "sortino_ratio": round(float(sortino), 4) if not np.isnan(sortino) else None,
            "max_drawdown_pct": round(float(max_dd * 100), 4),
            "max_drawdown_duration_days": max_dd_duration,
            "calmar_ratio": round(float(calmar), 4) if not np.isnan(calmar) else None,
            "annual_return_pct": round(float(annual_return * 100), 4),
            "annual_volatility_pct": round(float(annual_volatility * 100), 4),
            "var_95": round(float(var_95 * 100), 4),
            "cvar_95": round(float(cvar_95 * 100), 4),
            "beta": None,
            "alpha": None,
        }

        if benchmark_returns is not None:
            benchmark_returns = benchmark_returns.dropna()
            r_aligned, b_aligned = returns.align(benchmark_returns, join="inner")
            if len(r_aligned) >= 2 and b_aligned.std() > 0:
                beta_val, alpha_daily, _, _, _ = stats.linregress(b_aligned.values, r_aligned.values)
                alpha_annual = (1 + alpha_daily) ** ann_factor - 1
                result["beta"] = round(float(beta_val), 4)
                result["alpha"] = round(float(alpha_annual * 100), 4)

        return result

    def analyze_portfolio(
        self,
        positions: List[Dict],
        price_history: Dict[str, List[float]],
    ) -> Dict:
        symbols = [p["symbol"] for p in positions if p["symbol"] in price_history]

        returns_dict: Dict[str, pd.Series] = {}
        for sym in symbols:
            prices = pd.Series(price_history[sym], dtype=float)
            if len(prices) >= 2:
                returns_dict[sym] = prices.pct_change().dropna()

        correlation_matrix: Dict[str, Dict[str, float]] = {}
        avg_corr = 0.0
        if len(returns_dict) >= 2:
            df = pd.DataFrame(returns_dict).dropna()
            cm = df.corr()
            correlation_matrix = {
                row: {col: round(float(cm.loc[row, col]), 4) for col in cm.columns}
                for row in cm.index
            }
            upper = [cm.iloc[i, j] for i in range(len(cm)) for j in range(i + 1, len(cm))]
            avg_corr = float(np.mean(upper)) if upper else 0.0

        total_value = sum(float(p.get("value", 0)) for p in positions)
        weights: List[float] = []
        sector_exposure: Dict[str, float] = {}

        for p in positions:
            w = float(p.get("value", 0)) / total_value if total_value > 0 else 0.0
            weights.append(w)
            sector = p.get("sector", "Unknown")
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + w * 100.0

        hhi = float(sum(w ** 2 for w in weights))

        n = len(weights)
        if n <= 1:
            diversification_score = 0.0
        else:
            min_hhi = 1.0 / n
            hhi_score = max(0.0, 1.0 - (hhi - min_hhi) / (1.0 - min_hhi)) * 5.0
            corr_score = (1.0 - max(0.0, avg_corr)) * 5.0
            diversification_score = round(min(10.0, hhi_score + corr_score), 2)

        recommendations = self._portfolio_recommendations(
            hhi, diversification_score, sector_exposure, weights, positions
        )

        return {
            "correlation_matrix": correlation_matrix,
            "concentration_risk": round(hhi, 4),
            "diversification_score": diversification_score,
            "sector_exposure": {k: round(v, 2) for k, v in sector_exposure.items()},
            "recommendations": recommendations,
        }

    def drawdown_analysis(self, returns: pd.Series) -> pd.DataFrame:
        returns = returns.dropna()
        if returns.empty:
            return pd.DataFrame(columns=["start", "end", "depth_pct", "duration_days"])

        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max

        records = []
        in_drawdown = False
        start_idx = None

        for i, (date, dd) in enumerate(drawdown.items()):
            if not in_drawdown and dd < 0:
                in_drawdown = True
                start_idx = date
            elif in_drawdown and (dd == 0 or i == len(drawdown) - 1):
                end_idx = date
                segment = drawdown[start_idx:end_idx]
                depth = float(segment.min())
                dur_raw = end_idx - start_idx
                duration = dur_raw.days if hasattr(dur_raw, "days") else int(len(segment))
                records.append({
                    "start": start_idx,
                    "end": end_idx,
                    "depth_pct": round(depth * 100, 4),
                    "duration_days": duration,
                })
                in_drawdown = False
                start_idx = None

        if not records:
            return pd.DataFrame(columns=["start", "end", "depth_pct", "duration_days"])
        return pd.DataFrame(records).sort_values("depth_pct").reset_index(drop=True)

    def monthly_returns_table(self, returns: pd.Series) -> Dict:
        returns = returns.dropna()
        if not isinstance(returns.index, pd.DatetimeIndex):
            returns.index = pd.to_datetime(returns.index)

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        table: Dict[int, Dict[str, float]] = {}
        for (year, month), group in returns.groupby([returns.index.year, returns.index.month]):
            monthly_ret = float((1 + group).prod() - 1)
            if year not in table:
                table[year] = {}
            table[year][month_names[month - 1]] = round(monthly_ret * 100, 2)

        for year in table:
            year_returns = returns[returns.index.year == year]
            annual = float((1 + year_returns).prod() - 1)
            table[year]["Annual"] = round(annual * 100, 2)

        return table

    def stress_test(self, portfolio_value: float, positions: List[Dict]) -> Dict:
        scenarios = {
            "crash_20pct": -0.20,
            "bear_market_40pct": -0.40,
            "bull_run_30pct": 0.30,
        }

        results: Dict = {}
        for scenario_name, market_shock in scenarios.items():
            scenario_positions = []
            for pos in positions:
                beta = float(pos.get("beta", 1.0))
                pos_value = float(pos.get("value", 0))
                pos_shock = market_shock * beta
                new_value = pos_value * (1 + pos_shock)
                scenario_positions.append({
                    "symbol": pos.get("symbol", "UNKNOWN"),
                    "original_value": round(pos_value, 2),
                    "new_value": round(new_value, 2),
                    "change": round(new_value - pos_value, 2),
                    "change_pct": round(pos_shock * 100, 2),
                })

            total_change = sum(p["change"] for p in scenario_positions)
            new_total = portfolio_value + total_change
            results[scenario_name] = {
                "portfolio_original": round(portfolio_value, 2),
                "portfolio_new": round(new_total, 2),
                "total_change": round(total_change, 2),
                "total_change_pct": round(total_change / portfolio_value * 100, 2) if portfolio_value else 0.0,
                "positions": scenario_positions,
            }

        return results

    def _annualized_return(self, returns: pd.Series) -> float:
        n = len(returns)
        total = float((1 + returns).prod())
        return total ** (self.TRADING_DAYS_PER_YEAR / n) - 1

    def _annualized_volatility(self, returns: pd.Series) -> float:
        return float(returns.std(ddof=1) * np.sqrt(self.TRADING_DAYS_PER_YEAR))

    def _portfolio_recommendations(
        self,
        hhi: float,
        diversification_score: float,
        sector_exposure: Dict[str, float],
        weights: List[float],
        positions: List[Dict],
    ) -> List[str]:
        recs: List[str] = []

        if hhi > 0.25:
            top = max(positions, key=lambda p: float(p.get("value", 0)))
            recs.append(
                f"Alta concentración (HHI={hhi:.2f}): considera reducir exposición en {top.get('symbol', 'posición principal')}."
            )

        if diversification_score < 4.0:
            recs.append("Diversificación baja: agrega activos con baja correlación entre sí.")

        for sector, pct in sector_exposure.items():
            if pct > 40.0:
                recs.append(f"Sobreexposición al sector {sector} ({pct:.1f}%): considera rebalancear.")

        if weights:
            max_w = max(weights)
            if max_w > 0.40:
                heavy = positions[weights.index(max_w)]
                recs.append(
                    f"{heavy.get('symbol', 'Una posición')} representa {max_w * 100:.1f}% del portafolio; revisa el límite de concentración."
                )

        if not recs:
            recs.append("El portafolio muestra un perfil de riesgo/diversificación adecuado.")

        return recs
