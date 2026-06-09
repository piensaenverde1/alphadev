"""Paper trading engine: simula operaciones + exporta en formato freqtrade."""
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import DB_PATH


@dataclass
class PaperPosition:
    symbol: str
    quantity: float
    avg_price: float
    asset_type: str
    opened_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PaperTrader:
    """Cuenta de paper trading con persistencia en SQLite."""

    def __init__(self, initial_cash: float = 10000.0):
        self.initial_cash = initial_cash
        self._init_db()
        state = self._load_state()
        self.cash = state.get("cash", initial_cash)
        self.positions: Dict[str, PaperPosition] = state.get("positions", {})

    # ── DB setup ──────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_account (
                id INTEGER PRIMARY KEY,
                cash REAL NOT NULL,
                positions TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                pnl REAL,
                cash_after REAL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        # Insertar estado inicial si no existe
        if not conn.execute("SELECT id FROM paper_account LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO paper_account (id, cash, positions) VALUES (1, ?, ?)",
                (self.initial_cash, "{}")
            )
            conn.commit()
        conn.close()

    def _save_state(self):
        conn = self._get_conn()
        positions_json = json.dumps({
            sym: asdict(pos) for sym, pos in self.positions.items()
        })
        conn.execute(
            "UPDATE paper_account SET cash=?, positions=?, updated_at=CURRENT_TIMESTAMP WHERE id=1",
            (self.cash, positions_json)
        )
        conn.commit()
        conn.close()

    def _load_state(self) -> Dict:
        conn = self._get_conn()
        row = conn.execute("SELECT cash, positions FROM paper_account WHERE id=1").fetchone()
        conn.close()
        if not row:
            return {"cash": self.initial_cash, "positions": {}}
        positions_raw = json.loads(row["positions"] or "{}")
        positions = {
            sym: PaperPosition(**data)
            for sym, data in positions_raw.items()
        }
        return {"cash": row["cash"], "positions": positions}

    # ── Trading ───────────────────────────────────────────────────

    def execute_signal(self, signal: Dict, current_price: float,
                       size_recommendation: Dict = None) -> Dict:
        """Ejecuta una señal en la cuenta de paper trading."""
        symbol = signal.get("symbol", "").upper()
        action = signal.get("action", "HOLD")
        asset_type = signal.get("asset_type", "stock")

        if action not in ("BUY", "SELL"):
            return {"executed": False, "reason": f"Acción {action} no requiere ejecución"}

        if action == "BUY":
            # Calcular tamaño
            if size_recommendation:
                invest_value = size_recommendation.get("recommended_value", self.cash * 0.05)
            else:
                invest_value = self.cash * 0.05  # 5% del cash disponible

            invest_value = min(invest_value, self.cash * 0.95)  # Dejar algo de liquidez

            if invest_value < 1.0:
                return {"executed": False, "reason": "Capital insuficiente"}

            quantity = invest_value / current_price
            total_cost = quantity * current_price

            # Actualizar posición (promedio si ya existe)
            if symbol in self.positions:
                existing = self.positions[symbol]
                new_qty = existing.quantity + quantity
                new_avg = (existing.avg_price * existing.quantity + current_price * quantity) / new_qty
                self.positions[symbol] = PaperPosition(
                    symbol=symbol, quantity=new_qty, avg_price=new_avg,
                    asset_type=asset_type, opened_at=existing.opened_at
                )
            else:
                self.positions[symbol] = PaperPosition(
                    symbol=symbol, quantity=quantity, avg_price=current_price,
                    asset_type=asset_type
                )

            self.cash -= total_cost
            pnl = None

            result = {
                "executed": True, "action": "BUY", "symbol": symbol,
                "quantity": round(quantity, 6), "price": current_price,
                "total_value": round(total_cost, 2), "cash_remaining": round(self.cash, 2),
                "reason": "Orden de compra ejecutada",
            }

        else:  # SELL
            if symbol not in self.positions:
                return {"executed": False, "reason": f"No tienes {symbol} en cartera"}

            pos = self.positions[symbol]
            total_value = pos.quantity * current_price
            pnl = total_value - (pos.quantity * pos.avg_price)
            self.cash += total_value
            del self.positions[symbol]

            result = {
                "executed": True, "action": "SELL", "symbol": symbol,
                "quantity": round(pos.quantity, 6), "price": current_price,
                "total_value": round(total_value, 2), "pnl": round(pnl, 2),
                "cash_remaining": round(self.cash, 2),
                "reason": "Posición cerrada",
            }

        # Persistir
        self._save_state()
        self._record_trade(symbol, action, result.get("quantity", 0),
                           current_price, result.get("total_value", 0),
                           pnl, self.cash)
        return result

    def _record_trade(self, symbol, action, qty, price, total, pnl, cash_after):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO paper_trades (symbol, action, quantity, price, total_value, pnl, cash_after)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, action, qty, price, total, pnl, cash_after))
        conn.commit()
        conn.close()

    # ── Reporting ─────────────────────────────────────────────────

    def get_account_summary(self) -> Dict:
        conn = self._get_conn()
        trades = conn.execute("SELECT * FROM paper_trades ORDER BY executed_at DESC").fetchall()
        conn.close()

        positions_value = sum(
            p.quantity * p.avg_price for p in self.positions.values()
        )
        total_value = self.cash + positions_value
        total_pnl = total_value - self.initial_cash
        total_pnl_pct = (total_pnl / self.initial_cash * 100) if self.initial_cash > 0 else 0

        wins = sum(1 for t in trades if (t["pnl"] or 0) > 0)
        losses = sum(1 for t in trades if (t["pnl"] or 0) < 0)
        total_sell_trades = wins + losses

        return {
            "initial_cash": self.initial_cash,
            "cash": round(self.cash, 2),
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "total_trades": len(trades),
            "win_trades": wins,
            "loss_trades": losses,
            "win_rate": round(wins / total_sell_trades * 100, 1) if total_sell_trades > 0 else 0,
            "open_positions": len(self.positions),
        }

    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM paper_trades ORDER BY executed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── freqtrade Integration ─────────────────────────────────────

    def export_freqtrade_signals(self, signals: List[Dict],
                                  output_path: str = None) -> str:
        """Exporta señales en formato freqtrade-compatible."""
        ft_signals = []
        for sig in signals:
            symbol = sig.get("symbol", "")
            asset_type = sig.get("asset_type", "crypto")
            action = sig.get("action", "HOLD")

            if action not in ("BUY", "SELL"):
                continue

            # Formato freqtrade para crypto: BTC/USDT
            if asset_type == "crypto":
                pair = f"{symbol}/USDT"
            else:
                pair = symbol

            ft_signals.append({
                "pair": pair,
                "action": action.lower(),
                "price": sig.get("current_price") or sig.get("price", 0),
                "target": sig.get("target") or sig.get("price_target", 0),
                "stop_loss": sig.get("stop") or sig.get("stop_loss", 0),
                "confidence": sig.get("confidence", 0.5),
                "reasoning": sig.get("reasoning", ""),
                "date": datetime.now().isoformat(),
                "source": sig.get("agent_source", "ai_assistant"),
            })

        output = json.dumps(ft_signals, indent=2, ensure_ascii=False)

        if output_path:
            Path(output_path).write_text(output)

        return output

    def export_freqtrade_config(self, strategy_name: str = "AIAssistantStrategy") -> Dict:
        """Genera config.json compatible con freqtrade."""
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
            "unfilledtimeout": {"entry": 10, "exit": 10},
            "entry_pricing": {"price_side": "same", "ask_last_balance": 0.0},
            "exit_pricing": {"price_side": "same", "bid_ask_gap": 0.0},
            "exchange": {
                "name": "binance",
                "key": "",
                "secret": "",
                "ccxt_config": {},
                "ccxt_async_config": {},
                "pair_whitelist": [
                    "BTC/USDT", "ETH/USDT", "SOL/USDT",
                    "ADA/USDT", "LINK/USDT"
                ],
                "pair_blacklist": ["BNB/USDT"]
            },
            "pairlists": [{"method": "StaticPairList"}],
            "telegram": {
                "enabled": False,
                "token": "",
                "chat_id": ""
            },
            "api_server": {
                "enabled": False,
                "listen_ip_address": "127.0.0.1",
                "listen_port": 8080,
                "verbosity": "error"
            },
            "bot_name": strategy_name,
            "strategy": strategy_name,
            "initial_state": "running",
            "internals": {"process_throttle_secs": 5},
            "_comment": (
                "Config generado por Asistente Personal de Inversión. "
                "dry_run=true para paper trading. "
                "Cambia a false solo cuando hayas validado la estrategia."
            )
        }
