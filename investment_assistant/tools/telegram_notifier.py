import json
import os
import requests
from typing import Dict, List, Optional


class TelegramNotifier:

    _API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.is_configured():
            return False
        try:
            url = self._API_URL.format(token=self._token)
            payload = {
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def send_signal_alert(self, signal: Dict) -> bool:
        direction = signal.get("direction", "WATCH").upper()
        symbol = signal.get("symbol", "N/A")
        price = signal.get("price", 0)
        target = signal.get("target", 0)
        stop = signal.get("stop", 0)
        confidence = float(signal.get("confidence", 0.5))
        reasoning = signal.get("reasoning", "")

        emoji_map = {"BUY": "📈", "SELL": "📉", "WATCH": "👀"}
        emoji = emoji_map.get(direction, "👀")
        conf_bar = self._format_confidence_bar(confidence)

        lines = [
            f"{emoji} *{direction}: {symbol}*",
            f"💰 Precio: `${price:,.2f}`",
            f"🎯 Objetivo: `${target:,.2f}`",
            f"🛑 Stop: `${stop:,.2f}`",
            f"📊 Confianza: {conf_bar}",
        ]
        if reasoning:
            lines.append(f"💬 _{reasoning}_")

        return self.send_message("\n".join(lines))

    def send_daily_report(
        self,
        synthesis_json: str,
        signals_count: int,
        mood: str,
    ) -> bool:
        mood_emoji_map = {
            "bullish":  "🟢",
            "bearish":  "🔴",
            "neutral":  "🟡",
            "volatile": "🌪️",
        }
        mood_emoji = mood_emoji_map.get(mood.lower(), "🟡")

        try:
            synthesis = json.loads(synthesis_json) if isinstance(synthesis_json, str) else synthesis_json
        except (json.JSONDecodeError, TypeError):
            synthesis = {}

        top_actions: List[str] = synthesis.get("top_actions", [])[:3]
        summary_line: str = synthesis.get("summary", "Sin resumen disponible.")

        lines = [
            f"{mood_emoji} *Reporte Diario de Mercado*",
            f"📡 Señales generadas: `{signals_count}`",
            f"🌡️ Sentimiento: *{mood.capitalize()}*",
            f"📝 {summary_line}",
        ]
        if top_actions:
            lines.append("🔝 *Top acciones recomendadas:*")
            for i, action in enumerate(top_actions, 1):
                lines.append(f"  {i}. {action}")

        return self.send_message("\n".join(lines))

    def send_portfolio_update(self, summary: Dict) -> bool:
        total_value = float(summary.get("total_value", 0))
        pnl = float(summary.get("pnl", 0))
        pnl_pct = float(summary.get("pnl_pct", 0))
        best = summary.get("best_position", {})
        worst = summary.get("worst_position", {})

        pnl_emoji = "📈" if pnl >= 0 else "📉"
        sign = "+" if pnl >= 0 else ""

        lines = [
            "💼 *Actualización de Portafolio*",
            f"💵 Valor total: `${total_value:,.2f}`",
            f"{pnl_emoji} P&L: `{sign}${pnl:,.2f}` ({sign}{pnl_pct:.2f}%)",
        ]

        if best:
            b_sym = best.get("symbol", "N/A")
            b_pct = float(best.get("change_pct", 0))
            lines.append(f"🏆 Mejor: *{b_sym}* `+{b_pct:.2f}%`")

        if worst:
            w_sym = worst.get("symbol", "N/A")
            w_pct = float(worst.get("change_pct", 0))
            lines.append(f"⚠️ Peor: *{w_sym}* `{w_pct:.2f}%`")

        return self.send_message("\n".join(lines))

    def send_price_alert(
        self,
        symbol: str,
        current_price: float,
        threshold_pct: float,
        direction: str,
    ) -> bool:
        direction_text = "subió" if threshold_pct >= 0 else "cayó"
        sign = "+" if threshold_pct >= 0 else ""
        text = (
            f"⚠️ *ALERTA: {symbol} {direction_text} {sign}{threshold_pct:.1f}% en las últimas 2h*\n"
            f"💰 Precio actual: `${current_price:,.2f}`"
        )
        return self.send_message(text)

    def _format_confidence_bar(self, confidence: float) -> str:
        confidence = max(0.0, min(1.0, confidence))
        filled = round(confidence * 10)
        empty = 10 - filled
        return f"{'█' * filled}{'░' * empty} {int(confidence * 100)}%"
