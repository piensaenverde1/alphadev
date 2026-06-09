"""
Paper trading engine with freqtrade-compatible signal and config export.

All state is persisted to SQLite so positions and trade history survive
restarts. The DB_PATH is imported from config.settings so it is consistent
with the rest of the application.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import DB_PATH


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PaperPosition:
    """Represents an open paper-trading position."""

    symbol: str
    quantity: float
    avg_price: float
    asset_type: str
    opened_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class PaperAccount:
    """Snapshot of the full paper-trading account state."""

    cash: float
    positions: Dict[str, PaperPosition] = field(default_factory=dict)
    trade_history: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PaperTrader
# ---------------------------------------------------------------------------

class PaperTrader:
    """
    Simulated trading account with SQLite persistence and freqtrade export.

    Parameters
    ----------
    initial_cash : float
        Starting cash balance when no saved state exists (default 10 000).
    """

    def __init__(self, initial_cash: float = 10_000.0) -> None:
        self.initial_cash = initial_cash
        self._db_path = str(DB_PATH)

        self._init_db()
        state = self._load_state()
        self.cash: float = state.get("cash", initial_cash)
        self.positions: Dict[str, PaperPosition] = state.get("positions", {})

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not already exist."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trading (
                    id          INTEGER PRIMARY KEY,
                    cash        REAL    NOT NULL,
                    positions   TEXT    NOT NULL DEFAULT '{}',
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol      TEXT    NOT NULL,
                    action      TEXT    NOT NULL,
                    quantity    REAL    NOT NULL,
                    price       REAL    NOT NULL,
                    total_value REAL    NOT NULL,
                    pnl         REAL,
                    cash_after  REAL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Seed the account row if it does not exist
            if not conn.execute("SELECT id FROM paper_trading LIMIT 1").fetchone():
                conn.execute(
                    "INSERT INTO paper_trading (id, cash, positions) VALUES (1, ?, ?)",
                    (self.initial_cash, "{}"),
                )
                conn.commit()
        finally:
            conn.close()

    def _save_state(self) -> None:
        """Persist current cash and positions to the 'paper_trading' table."""
        positions_json = json.dumps(
            {sym: asdict(pos) for sym, pos in self.positions.items()}
        )
        conn = self._get_conn()
        try:
            conn.execute(
                """
                UPDATE paper_trading
                SET cash = ?, positions = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (self.cash, positions_json),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_state(self) -> Dict:
        """Load cash and positions from the 'paper_trading' table."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT cash, positions FROM paper_trading WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return {"cash": self.initial_cash, "positions": {}}

        raw_positions: Dict = json.loads(row["positions"] or "{}")
        positions = {
            sym: PaperPosition(**data) for sym, data in raw_positions.items()
        }
        return {"cash": float(row["cash"]), "positions": positions}

    def _record_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        total_value: float,
        pnl: Optional[float],
        cash_after: float,
    ) -> None:
        """Append a completed trade to the 'paper_trades' table."""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO paper_trades
                    (symbol, action, quantity, price, total_value, pnl, cash_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (symbol, action, quantity, price, total_value, pnl, cash_after),
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Trading execution
    # ------------------------------------------------------------------

    def execute_signal(
        self,
        signal: Dict,
        current_price: float,
        size_recommendation: Optional[Dict] = None,
    ) -> Dict:
        """
        Execute a BUY or SELL signal against the paper account.

        Parameters
        ----------
        signal : dict
            Must contain 'symbol' and 'action' ('BUY'|'SELL').
            Optional: 'asset_type'.
        current_price : float
            Execution price.
        size_recommendation : dict, optional
            Output of RiskManager.calculate_position(). When supplied, the
            'recommended_value' key is used to determine position size.
            Falls back to 5 % of available cash.

        Returns
        -------
        dict with keys:
            executed    – bool
            order_type  – 'market' (always for paper trading)
            symbol      – str
            quantity    – float
            price       – float
            total_value – float
            reason      – str
        """
        symbol: str = signal.get("symbol", "").upper()
        action: str = signal.get("action", "HOLD").upper()
        asset_type: str = signal.get("asset_type", "stock")

        if action not in ("BUY", "SELL"):
            return {
                "executed": False,
                "order_type": None,
                "symbol": symbol,
                "quantity": 0,
                "price": current_price,
                "total_value": 0.0,
                "reason": f"Action '{action}' does not require execution.",
            }

        if current_price <= 0:
            return {
                "executed": False,
                "order_type": None,
                "symbol": symbol,
                "quantity": 0,
                "price": current_price,
                "total_value": 0.0,
                "reason": "Invalid price (<= 0).",
            }

        if action == "BUY":
            return self._execute_buy(symbol, asset_type, current_price, size_recommendation)
        return self._execute_sell(symbol, current_price)

    def _execute_buy(
        self,
        symbol: str,
        asset_type: str,
        price: float,
        size_recommendation: Optional[Dict],
    ) -> Dict:
        # Determine invest amount
        if size_recommendation:
            invest_value = float(size_recommendation.get("recommended_value", self.cash * 0.05))
        else:
            invest_value = self.cash * 0.05  # default: 5 % of available cash

        # Leave a small liquidity reserve (max 95 % of cash in one trade)
        invest_value = min(invest_value, self.cash * 0.95)

        if invest_value < 1.0:
            return {
                "executed": False,
                "order_type": "market",
                "symbol": symbol,
                "quantity": 0,
                "price": price,
                "total_value": 0.0,
                "reason": "Insufficient cash to execute BUY.",
            }

        quantity = invest_value / price
        total_cost = quantity * price

        # Average into existing position if the symbol is already held
        if symbol in self.positions:
            existing = self.positions[symbol]
            new_qty = existing.quantity + quantity
            new_avg = (
                (existing.avg_price * existing.quantity + price * quantity) / new_qty
            )
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=new_qty,
                avg_price=new_avg,
                asset_type=asset_type,
                opened_at=existing.opened_at,
            )
        else:
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                asset_type=asset_type,
            )

        self.cash -= total_cost
        self._save_state()
        self._record_trade(symbol, "BUY", quantity, price, total_cost, None, self.cash)

        return {
            "executed": True,
            "order_type": "market",
            "symbol": symbol,
            "quantity": round(quantity, 6),
            "price": price,
            "total_value": round(total_cost, 2),
            "reason": "BUY order executed.",
        }

    def _execute_sell(self, symbol: str, price: float) -> Dict:
        if symbol not in self.positions:
            return {
                "executed": False,
                "order_type": "market",
                "symbol": symbol,
                "quantity": 0,
                "price": price,
                "total_value": 0.0,
                "reason": f"No open position for {symbol}.",
            }

        pos = self.positions[symbol]
        total_value = pos.quantity * price
        pnl = total_value - (pos.quantity * pos.avg_price)

        self.cash += total_value
        del self.positions[symbol]

        self._save_state()
        self._record_trade(symbol, "SELL", pos.quantity, price, total_value, pnl, self.cash)

        return {
            "executed": True,
            "order_type": "market",
            "symbol": symbol,
            "quantity": round(pos.quantity, 6),
            "price": price,
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "reason": "Position closed (SELL).",
        }

    # ------------------------------------------------------------------
    # Account summary & history
    # ------------------------------------------------------------------

    def get_account_summary(self) -> Dict:
        """
        Return a snapshot of account performance.

        Returns
        -------
        dict with keys:
            cash, positions_value, total_value, total_pnl, total_pnl_pct,
            total_trades, win_trades, loss_trades, win_rate, open_positions
        """
        conn = self._get_conn()
        try:
            trades = conn.execute(
                "SELECT pnl FROM paper_trades WHERE pnl IS NOT NULL"
            ).fetchall()
            total_trades_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM paper_trades"
            ).fetchone()
        finally:
            conn.close()

        positions_value = sum(
            p.quantity * p.avg_price for p in self.positions.values()
        )
        total_value = self.cash + positions_value
        total_pnl = total_value - self.initial_cash
        total_pnl_pct = (
            (total_pnl / self.initial_cash * 100) if self.initial_cash > 0 else 0.0
        )

        win_trades = sum(1 for t in trades if float(t["pnl"]) > 0)
        loss_trades = sum(1 for t in trades if float(t["pnl"]) < 0)
        closed_trades = win_trades + loss_trades
        win_rate = (win_trades / closed_trades * 100) if closed_trades > 0 else 0.0

        return {
            "initial_cash": round(self.initial_cash, 2),
            "cash": round(self.cash, 2),
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "total_trades": int(total_trades_row["cnt"]) if total_trades_row else 0,
            "win_trades": win_trades,
            "loss_trades": loss_trades,
            "win_rate": round(win_rate, 1),
            "open_positions": len(self.positions),
        }

    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """
        Return the most recent trades from the database.

        Parameters
        ----------
        limit : int
            Maximum number of records to return (default 20).
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM paper_trades ORDER BY executed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # freqtrade integration
    # ------------------------------------------------------------------

    def export_freqtrade_signals(
        self,
        signals: List[Dict],
        output_path: Optional[str] = None,
    ) -> str:
        """
        Serialise signals to freqtrade-compatible JSON format.

        Each signal is converted to::

            {
                "pair":       "BTC/USDT",
                "action":     "buy",
                "price":      104280,
                "date":       "2026-06-09T12:00:00",
                "target":     ...,
                "stop_loss":  ...,
                "confidence": ...,
                "reasoning":  ...,
                "source":     ...
            }

        Parameters
        ----------
        signals : list of dict
            Signals to export. Each should contain at least 'symbol',
            'action', and 'current_price'.
        output_path : str, optional
            If provided, the JSON string is also written to this file path.

        Returns
        -------
        str
            JSON-serialised signal list.
        """
        ft_signals = []
        now_iso = datetime.utcnow().isoformat()

        for sig in signals:
            action = sig.get("action", "HOLD").upper()
            if action not in ("BUY", "SELL"):
                continue

            symbol = sig.get("symbol", "")
            asset_type = sig.get("asset_type", "crypto").lower()

            # Build freqtrade pair notation
            if asset_type == "crypto":
                pair = f"{symbol}/USDT"
            elif "/" in symbol:
                pair = symbol  # already in exchange notation
            else:
                pair = symbol  # equities: use symbol directly

            ft_signals.append({
                "pair": pair,
                "action": action.lower(),
                "price": sig.get("current_price") or sig.get("price", 0),
                "date": sig.get("date", now_iso),
                "target": sig.get("target") or sig.get("price_target", 0),
                "stop_loss": sig.get("stop") or sig.get("stop_loss", 0),
                "confidence": sig.get("confidence", 0.5),
                "reasoning": sig.get("reasoning", ""),
                "source": sig.get("agent_source", "ai_assistant"),
            })

        output = json.dumps(ft_signals, indent=2, ensure_ascii=False)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(output, encoding="utf-8")

        return output

    def export_freqtrade_config(
        self, strategy_name: str = "AIAssistantStrategy"
    ) -> Dict:
        """
        Generate a working freqtrade config.json template.

        The config targets spot trading on Binance in dry-run (paper) mode,
        using the strategy class named *strategy_name*.

        Returns
        -------
        dict
            A complete freqtrade configuration dict. Write to a file with::

                import json
                json.dump(trader.export_freqtrade_config(), open("config.json", "w"), indent=2)
        """
        return {
            "max_open_trades": 5,
            "stake_currency": "USDT",
            "stake_amount": "unlimited",
            "tradable_balance_ratio": 0.99,
            "fiat_display_currency": "EUR",
            "dry_run": True,
            "dry_run_wallet": self.initial_cash,
            "cancel_open_orders_on_exit": False,
            "trading_mode": "spot",
            "margin_mode": "",
            "unfilledtimeout": {"entry": 10, "exit": 10, "unit": "minutes"},
            "entry_pricing": {
                "price_side": "same",
                "use_order_book": False,
                "ask_last_balance": 0.0,
                "order_book_top": 1,
            },
            "exit_pricing": {
                "price_side": "same",
                "use_order_book": False,
                "bid_ask_gap": 0.0,
                "order_book_top": 1,
            },
            "exchange": {
                "name": "binance",
                "key": "",
                "secret": "",
                "ccxt_config": {},
                "ccxt_async_config": {},
                "pair_whitelist": [
                    "BTC/USDT",
                    "ETH/USDT",
                    "SOL/USDT",
                    "ADA/USDT",
                    "LINK/USDT",
                ],
                "pair_blacklist": ["BNB/USDT"],
            },
            "pairlists": [{"method": "StaticPairList"}],
            "stoploss": -0.05,
            "trailing_stop": False,
            "minimal_roi": {"0": 0.10, "60": 0.05, "120": 0.02},
            "telegram": {
                "enabled": False,
                "token": "",
                "chat_id": "",
            },
            "api_server": {
                "enabled": False,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8080,
                "verbosity": "error",
                "enable_openapi": False,
            },
            "bot_name": strategy_name,
            "strategy": strategy_name,
            "strategy_path": "user_data/strategies/",
            "initial_state": "running",
            "force_entry_enable": False,
            "internals": {"process_throttle_secs": 5},
            "_comment": (
                "Config generated by the AI Investment Assistant. "
                "dry_run=true for paper trading. "
                "Set dry_run=false only after thorough backtest validation."
            ),
        }
