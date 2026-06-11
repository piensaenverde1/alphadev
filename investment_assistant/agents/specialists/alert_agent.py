"""Agente especialista en gestión de alertas y notificaciones."""
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from agents.base import BaseAgent
from tools.telegram_notifier import TelegramNotifier
from config.settings import DB_PATH
from memory.database import save_lesson

SYSTEM_PROMPT = """Eres un especialista en gestión de alertas de inversión.
Tu función es filtrar el ruido y enviar únicamente las notificaciones más importantes.

Filosofía de alertas:
1. Menos es más: solo alertar cuando la situación realmente lo justifica
2. BUY con alta confianza (>60%) merece notificación inmediata
3. Cualquier señal de VENTA debe comunicarse sin demora
4. Cambios bruscos en el portfolio (>5% P&L) requieren atención urgente
5. El humor del mercado importa: un resumen diario ayuda a tomar decisiones

Prioridades: CRÍTICO > IMPORTANTE > INFORMATIVO
Responde siempre en español con recomendaciones claras sobre qué hacer con cada alerta.
"""


class AlertAgent(BaseAgent):
    name = "alert_specialist"
    description = "Gestión de alertas y notificaciones vía Telegram y reglas personalizadas"

    def __init__(self):
        super().__init__()
        self._db_path = str(DB_PATH)
        self._init_alert_rules_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_alert_rules_table(self):
        """Crea la tabla alert_rules si no existe."""
        try:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    last_triggered TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.log(f"Error inicializando tabla de reglas: {e}")

    # ------------------------------------------------------------------
    # Gestión de reglas
    # ------------------------------------------------------------------

    def add_rule(self, symbol: str, condition_type: str, threshold: float) -> bool:
        """
        Añade una regla de alerta personalizada.

        condition_type opciones: 'price_above', 'price_below', 'change_pct'
        """
        try:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO alert_rules (symbol, condition_type, threshold)
                VALUES (?, ?, ?)
            """, (symbol.upper(), condition_type, threshold))
            conn.commit()
            conn.close()
            self.log(f"Regla añadida: {symbol} {condition_type} {threshold}")
            return True
        except Exception as e:
            self.log(f"Error añadiendo regla: {e}")
            return False

    def remove_rule(self, symbol: str) -> bool:
        """Elimina todas las reglas de un símbolo."""
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM alert_rules WHERE symbol = ?", (symbol.upper(),))
            conn.commit()
            conn.close()
            self.log(f"Reglas eliminadas para: {symbol}")
            return True
        except Exception as e:
            self.log(f"Error eliminando regla: {e}")
            return False

    def get_rules(self) -> List[Dict]:
        """Retorna todas las reglas almacenadas."""
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM alert_rules ORDER BY symbol"
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            self.log(f"Error obteniendo reglas: {e}")
            return []

    # ------------------------------------------------------------------
    # Evaluación de reglas
    # ------------------------------------------------------------------

    def _check_rules_against_signals(self, signals: List[Dict]) -> List[Dict]:
        """Compara señales actuales contra las reglas almacenadas."""
        triggered = []
        rules = self.get_rules()
        if not rules or not signals:
            return triggered

        # Construir mapa símbolo -> señal para búsqueda rápida
        signal_map = {s.get("symbol", "").upper(): s for s in signals}

        for rule in rules:
            symbol = rule["symbol"]
            condition = rule["condition_type"]
            threshold = float(rule["threshold"])

            signal = signal_map.get(symbol)
            if not signal:
                continue

            current_price = float(signal.get("current_price") or signal.get("price", 0))
            change_pct = float(signal.get("change_pct", signal.get("change_5d_pct", 0)))

            fired = False
            message = ""

            if condition == "price_above" and current_price > threshold:
                fired = True
                message = f"{symbol} superó ${threshold:,.2f} → Precio actual: ${current_price:,.2f}"
            elif condition == "price_below" and current_price < threshold:
                fired = True
                message = f"{symbol} cayó bajo ${threshold:,.2f} → Precio actual: ${current_price:,.2f}"
            elif condition == "change_pct" and abs(change_pct) >= abs(threshold):
                fired = True
                sign = "+" if change_pct > 0 else ""
                message = f"{symbol} cambió {sign}{change_pct:.1f}% (umbral: {threshold:.1f}%)"

            if fired:
                triggered.append({
                    "rule_id": rule["id"],
                    "symbol": symbol,
                    "condition": condition,
                    "threshold": threshold,
                    "message": message,
                })
                # Actualizar last_triggered
                try:
                    conn = self._get_conn()
                    conn.execute(
                        "UPDATE alert_rules SET last_triggered = CURRENT_TIMESTAMP WHERE id = ?",
                        (rule["id"],)
                    )
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

        return triggered

    # ------------------------------------------------------------------
    # run principal
    # ------------------------------------------------------------------

    def run(
        self,
        signals: List[Dict] = None,
        portfolio_summary: Dict = None,
        market_mood: str = None,
    ) -> Dict:
        self.log("Iniciando gestión de alertas...")

        signals = signals or []
        telegram = TelegramNotifier()
        telegram_configured = telegram.is_configured()

        alerts_sent = []
        rules_triggered = []

        # 1. Alertas por señales de trading
        for signal in signals:
            action = signal.get("action", "HOLD").upper()
            confidence = float(signal.get("confidence", 0.0))
            symbol = signal.get("symbol", "?")

            should_alert = False
            reason = ""

            if action == "BUY" and confidence > 0.6:
                should_alert = True
                reason = f"Señal de COMPRA con confianza {confidence:.0%}"
            elif action == "SELL":
                should_alert = True
                reason = f"Señal de VENTA detectada"

            if should_alert:
                self.log(f"Enviando alerta: {action} {symbol}")
                sent = False
                if telegram_configured:
                    try:
                        sent = telegram.send_signal_alert({
                            "direction": action,
                            "symbol": symbol,
                            "price": signal.get("current_price") or signal.get("price", 0),
                            "target": signal.get("target") or signal.get("price_target", 0),
                            "stop": signal.get("stop") or signal.get("stop_loss", 0),
                            "confidence": confidence,
                            "reasoning": signal.get("reasoning", reason),
                        })
                    except Exception as e:
                        self.log(f"Error enviando alerta Telegram: {e}")

                alerts_sent.append({
                    "type": "signal",
                    "symbol": symbol,
                    "action": action,
                    "confidence": confidence,
                    "telegram_sent": sent,
                    "reason": reason,
                })

        # 2. Alerta de cambio en P&L del portfolio
        if portfolio_summary:
            pnl_pct = float(portfolio_summary.get("total_pnl_pct", 0))
            if abs(pnl_pct) > 5.0:
                self.log(f"Alerta de portfolio: P&L {pnl_pct:+.2f}%")
                sent = False
                if telegram_configured:
                    try:
                        sent = telegram.send_portfolio_update(portfolio_summary)
                    except Exception as e:
                        self.log(f"Error enviando actualización de portfolio: {e}")

                alerts_sent.append({
                    "type": "portfolio_pnl",
                    "pnl_pct": pnl_pct,
                    "telegram_sent": sent,
                    "reason": f"Cambio de P&L significativo: {pnl_pct:+.2f}%",
                })

        # 3. Comprobar reglas almacenadas contra señales actuales
        if signals:
            rules_triggered = self._check_rules_against_signals(signals)
            for rule_alert in rules_triggered:
                self.log(f"Regla activada: {rule_alert['message']}")
                sent = False
                if telegram_configured:
                    try:
                        msg = f"⚠️ *Alerta de precio*\n{rule_alert['message']}"
                        sent = telegram.send_message(msg)
                    except Exception as e:
                        self.log(f"Error enviando alerta de regla: {e}")
                rule_alert["telegram_sent"] = sent

        # 4. Resumen diario del mood de mercado
        if market_mood:
            self.log(f"Enviando resumen de mercado: {market_mood}")
            signals_count = len(signals)
            sent = False
            if telegram_configured:
                try:
                    sent = telegram.send_daily_report(
                        synthesis_json=json.dumps({
                            "summary": f"El mercado muestra sentimiento {market_mood} hoy.",
                            "top_actions": [
                                f"{s['symbol']} → {s['action']}"
                                for s in signals[:3]
                                if s.get("action") in ("BUY", "SELL")
                            ],
                        }),
                        signals_count=signals_count,
                        mood=market_mood,
                    )
                except Exception as e:
                    self.log(f"Error enviando resumen diario: {e}")

            alerts_sent.append({
                "type": "daily_summary",
                "market_mood": market_mood,
                "telegram_sent": sent,
            })

        # 5. Guardar lección si hubo muchas alertas
        total_critical = sum(
            1 for a in alerts_sent
            if a.get("action") == "SELL" or abs(a.get("pnl_pct", 0)) > 10
        )
        if total_critical > 0:
            try:
                save_lesson(
                    lesson_type="signal_accuracy",
                    agent=self.name,
                    context=f"Se dispararon {total_critical} alertas críticas",
                    lesson=f"Alta actividad de alertas críticas detectada. "
                           f"Total alertas enviadas: {len(alerts_sent)}. "
                           f"Reglas activadas: {len(rules_triggered)}.",
                    confidence=0.7,
                )
            except Exception as e:
                self.log(f"Error guardando lección: {e}")

        summary = (
            f"{len(alerts_sent)} alertas enviadas, "
            f"{len(rules_triggered)} reglas activadas, "
            f"Telegram {'configurado' if telegram_configured else 'no configurado'}"
        )

        self.log(summary)

        return {
            "alerts_sent": alerts_sent,
            "rules_triggered": rules_triggered,
            "telegram_configured": telegram_configured,
            "summary": summary,
        }
