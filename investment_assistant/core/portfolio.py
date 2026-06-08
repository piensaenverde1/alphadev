"""Gestión del portfolio de inversión."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from memory.database import (
    upsert_asset, get_portfolio, remove_asset,
    get_price_history, save_price
)
from tools.market_data import get_multiple_stocks, get_stock_info
from tools.crypto_data import get_top_coins


@dataclass
class Position:
    symbol: str
    name: str
    asset_type: str
    quantity: float
    avg_buy_price: float
    current_price: float = 0.0
    currency: str = "EUR"

    @property
    def total_invested(self) -> float:
        return self.quantity * self.avg_buy_price

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def pnl(self) -> float:
        return self.current_value - self.total_invested

    @property
    def pnl_pct(self) -> float:
        if self.total_invested == 0:
            return 0
        return (self.pnl / self.total_invested) * 100

    @property
    def trend_emoji(self) -> str:
        if self.pnl_pct > 5:
            return "▲▲"
        elif self.pnl_pct > 0:
            return "▲"
        elif self.pnl_pct < -5:
            return "▼▼"
        else:
            return "▼"


class Portfolio:
    """Portfolio manager."""

    def __init__(self, cash: float = 0, currency: str = "EUR"):
        self.cash = cash
        self.currency = currency

    def add_position(self, symbol: str, name: str, asset_type: str,
                     quantity: float, price: float, notes: str = "") -> str:
        """Añade o actualiza una posición."""
        upsert_asset(symbol, name, asset_type, quantity, price, self.currency, notes)
        total = quantity * price
        return f"Añadido {quantity} {symbol} a {price} = {total:.2f} {self.currency}"

    def remove_position(self, symbol: str):
        """Elimina una posición."""
        remove_asset(symbol)

    def get_positions(self, refresh_prices: bool = True) -> List[Position]:
        """Obtiene todas las posiciones con precios actualizados."""
        raw = get_portfolio()
        if not raw:
            return []

        positions = []

        # Separar por tipo para actualización eficiente
        stocks = [p for p in raw if p["asset_type"] in ("stock", "etf")]
        cryptos = [p for p in raw if p["asset_type"] == "crypto"]

        current_prices: Dict[str, float] = {}

        if refresh_prices and stocks:
            symbols = [p["symbol"] for p in stocks]
            price_data = get_multiple_stocks(symbols)
            for pd in price_data:
                current_prices[pd["symbol"]] = pd.get("price", 0)

        if refresh_prices and cryptos:
            top = get_top_coins(limit=100)
            for c in top:
                current_prices[c["symbol"]] = c.get("price", 0)

        for p in raw:
            current = current_prices.get(p["symbol"], p["avg_buy_price"])
            position = Position(
                symbol=p["symbol"],
                name=p.get("name", p["symbol"]),
                asset_type=p["asset_type"],
                quantity=p["quantity"],
                avg_buy_price=p["avg_buy_price"],
                current_price=current,
                currency=p.get("currency", self.currency),
            )
            positions.append(position)

        return positions

    def get_summary(self, refresh_prices: bool = True) -> Dict:
        """Resumen del portfolio."""
        positions = self.get_positions(refresh_prices)

        total_invested = sum(p.total_invested for p in positions)
        total_current = sum(p.current_value for p in positions) + self.cash
        total_pnl = sum(p.pnl for p in positions)
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        by_type: Dict[str, float] = {}
        for p in positions:
            if p.asset_type not in by_type:
                by_type[p.asset_type] = 0
            by_type[p.asset_type] += p.current_value

        winners = [p for p in positions if p.pnl > 0]
        losers = [p for p in positions if p.pnl < 0]

        return {
            "positions": positions,
            "total_positions": len(positions),
            "cash": self.cash,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
            "winners": len(winners),
            "losers": len(losers),
            "best_position": max(positions, key=lambda p: p.pnl_pct).symbol if positions else None,
            "worst_position": min(positions, key=lambda p: p.pnl_pct).symbol if positions else None,
        }

    def get_allocation_pct(self) -> Dict[str, float]:
        """Distribución porcentual del portfolio."""
        positions = self.get_positions(refresh_prices=False)
        total = sum(p.current_value for p in positions) + self.cash
        if total == 0:
            return {}
        result = {p.symbol: round(p.current_value / total * 100, 1) for p in positions}
        if self.cash > 0:
            result["CASH"] = round(self.cash / total * 100, 1)
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
