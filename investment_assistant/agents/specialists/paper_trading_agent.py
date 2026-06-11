"""Agente especialista en paper trading: ejecución y monitorización simulada."""
import json
from datetime import datetime
from typing import Dict, List, Optional
from agents.base import BaseAgent
from core.paper_trader import PaperTrader
from memory.database import save_lesson

SYSTEM_PROMPT = """Eres el gestor de paper trading de un sistema de inversión automatizado.
Tu objetivo es ejecutar operaciones simuladas, aprender de los resultados y mejorar la estrategia.

Responsabilidades:
1. Ejecutar señales de alta confianza en modo simulado para validarlas sin riesgo real
2. Monitorizar posiciones abiertas y detectar si stop-loss o take-profit se han alcanzado
3. Analizar métricas de rendimiento para identificar qué estrategias funcionan mejor
4. Generar recomendaciones para mejorar la selección de señales
5. Exportar datos compatibles con freqtrade para backtesting avanzado

Métricas clave que analizas:
- Win rate: % de operaciones ganadoras (objetivo >55%)
- Retorno promedio: ganancia/pérdida media por operación
- Ratio riesgo/recompensa: target vs stop-loss
- Drawdown máximo: pérdida máxima desde el pico de capital

Responde siempre en español. Sé riguroso con los números y honesto sobre el rendimiento.
"""


class PaperTradingAgent(BaseAgent):
    name = "paper_trading_specialist"
    description = "Ejecución y monitorización de paper trading con exportación freqtrade"

    def run(
        self,
        signals: List[Dict] = None,
        execute: bool = False,
    ) -> Dict:
        self.log("Iniciando análisis de paper trading...")

        signals = signals or []
        trader = PaperTrader()

        # 1. Resumen de la cuenta actual
        self.log("Obteniendo resumen de cuenta...")
        account_summary = {}
        try:
            account_summary = trader.get_account_summary()
            self.log(
                f"Cuenta: ${account_summary.get('total_value', 0):,.2f} | "
                f"P&L: {account_summary.get('total_pnl_pct', 0):+.2f}%"
            )
        except Exception as e:
            self.log(f"Error obteniendo resumen de cuenta: {e}")

        # 2. Historial de trades
        trade_history = []
        try:
            trade_history = trader.get_trade_history(limit=50)
        except Exception as e:
            self.log(f"Error obteniendo historial: {e}")

        # 3. Ejecutar o simular señales de compra con alta confianza
        executed_trades = []
        simulated_trades = []

        buy_signals = [
            s for s in signals
            if s.get("action", "").upper() == "BUY"
            and float(s.get("confidence", 0)) > 0.65
        ]

        for signal in buy_signals:
            symbol = signal.get("symbol", "?")
            confidence = float(signal.get("confidence", 0))
            price = float(signal.get("current_price") or signal.get("price", 0))

            if price <= 0:
                self.log(f"Precio inválido para {symbol}, omitiendo...")
                continue

            if execute:
                self.log(f"Ejecutando BUY en paper trading: {symbol} @ ${price:,.2f} (conf: {confidence:.0%})")
                try:
                    result = trader.execute_signal(
                        signal={"symbol": symbol, "action": "BUY",
                                "asset_type": signal.get("asset_type", "stock")},
                        current_price=price,
                    )
                    if result.get("executed"):
                        executed_trades.append({
                            "symbol": symbol,
                            "action": "BUY",
                            "price": price,
                            "quantity": result.get("quantity", 0),
                            "total_value": result.get("total_value", 0),
                            "confidence": confidence,
                            "status": "executed",
                        })
                        self.log(f"  Ejecutado: {result.get('quantity', 0):.6f} unidades")
                    else:
                        self.log(f"  No ejecutado: {result.get('reason', 'desconocido')}")
                except Exception as e:
                    self.log(f"Error ejecutando {symbol}: {e}")
            else:
                # Simulación (dry run)
                invest_value = trader.cash * 0.05
                simulated_qty = invest_value / price if price > 0 else 0
                simulated_trades.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "price": price,
                    "estimated_quantity": round(simulated_qty, 6),
                    "estimated_value": round(invest_value, 2),
                    "confidence": confidence,
                    "status": "simulated",
                })

        # 4. Verificar posiciones abiertas (stop-loss / take-profit)
        pending_exits = []
        open_positions = account_summary.get("open_positions", 0)

        if open_positions > 0:
            self.log("Verificando posiciones abiertas contra niveles de salida...")
            for signal in signals:
                symbol = signal.get("symbol", "").upper()
                current_price = float(signal.get("current_price") or signal.get("price", 0))
                stop_loss = float(signal.get("stop") or signal.get("stop_loss", 0))
                take_profit = float(signal.get("target") or signal.get("price_target", 0))

                if symbol in trader.positions and current_price > 0:
                    pos = trader.positions[symbol]
                    avg_price = pos.avg_price
                    current_pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                    exit_reason = None
                    if stop_loss > 0 and current_price <= stop_loss:
                        exit_reason = f"Stop-loss alcanzado: ${current_price:,.2f} <= ${stop_loss:,.2f}"
                    elif take_profit > 0 and current_price >= take_profit:
                        exit_reason = f"Take-profit alcanzado: ${current_price:,.2f} >= ${take_profit:,.2f}"

                    if exit_reason:
                        pending_exits.append({
                            "symbol": symbol,
                            "entry_price": avg_price,
                            "current_price": current_price,
                            "pnl_pct": round(current_pnl_pct, 2),
                            "exit_reason": exit_reason,
                        })
                        self.log(f"Posición a cerrar: {symbol} - {exit_reason}")

        # 5. Métricas de rendimiento
        performance_metrics = self._calculate_performance(trade_history)

        # 6. Exportar señales freqtrade
        if signals:
            try:
                trader.export_freqtrade_signals(
                    signals=signals,
                    output_path="/tmp/freqtrade_signals.json",
                )
                self.log("Señales exportadas a /tmp/freqtrade_signals.json")
            except Exception as e:
                self.log(f"Error exportando señales freqtrade: {e}")

        # 7. Análisis de IA
        self.log("Generando análisis de rendimiento con IA...")
        lessons_ctx = self.get_lessons_context()

        metrics_str = json.dumps(performance_metrics, ensure_ascii=False, indent=2)
        account_str = json.dumps(account_summary, ensure_ascii=False, indent=2)

        user_message = f"""Revisión del sistema de paper trading:

ESTADO DE LA CUENTA:
{account_str}

MÉTRICAS DE RENDIMIENTO:
{metrics_str}

OPERACIONES EJECUTADAS HOY: {len(executed_trades)}
SIMULACIONES (dry run): {len(simulated_trades)}
POSICIONES PENDIENTES DE CIERRE: {len(pending_exits)}

{lessons_ctx}

¿Cómo está rindiendo el sistema? ¿Qué ajustes de estrategia recomiendas
basándote en estas métricas de paper trading?"""

        ai_analysis = self.ask_ai(SYSTEM_PROMPT, user_message, max_tokens=700)

        # 8. Guardar lección si el rendimiento es significativo
        win_rate = performance_metrics.get("win_rate", 0)
        if performance_metrics.get("total_trades", 0) >= 5:
            lesson_text = (
                f"Paper trading win rate: {win_rate:.1f}%. "
                f"Retorno promedio: {performance_metrics.get('avg_return', 0):+.2f}%. "
                f"Mejor operación: {performance_metrics.get('best_trade', {}).get('symbol', 'N/A')}."
            )
            try:
                save_lesson(
                    lesson_type="signal_accuracy",
                    agent=self.name,
                    context="Revisión periódica de paper trading",
                    lesson=lesson_text,
                    confidence=0.8 if win_rate > 55 else 0.5,
                )
            except Exception as e:
                self.log(f"Error guardando lección: {e}")

        self.log(
            f"Paper trading completado. "
            f"Win rate: {win_rate:.1f}% | "
            f"Ejecutados: {len(executed_trades)} | "
            f"Salidas pendientes: {len(pending_exits)}"
        )

        return {
            "account_summary": account_summary,
            "executed_trades": executed_trades,
            "simulated_trades": simulated_trades,
            "performance_metrics": performance_metrics,
            "pending_exits": pending_exits,
            "ai_analysis": ai_analysis,
        }

    def _calculate_performance(self, trade_history: List[Dict]) -> Dict:
        """Calcula métricas de rendimiento a partir del historial de trades."""
        closed_trades = [t for t in trade_history if t.get("pnl") is not None]

        if not closed_trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_pnl": 0.0,
                "best_trade": {},
                "worst_trade": {},
            }

        pnl_values = [float(t.get("pnl", 0)) for t in closed_trades]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]

        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0
        avg_return = sum(pnl_values) / len(pnl_values) if pnl_values else 0.0
        total_pnl = sum(pnl_values)

        # Mejor y peor operación
        best_idx = pnl_values.index(max(pnl_values)) if pnl_values else 0
        worst_idx = pnl_values.index(min(pnl_values)) if pnl_values else 0

        best_trade = {
            "symbol": closed_trades[best_idx].get("symbol", "N/A"),
            "pnl": round(pnl_values[best_idx], 2),
        } if closed_trades else {}

        worst_trade = {
            "symbol": closed_trades[worst_idx].get("symbol", "N/A"),
            "pnl": round(pnl_values[worst_idx], 2),
        } if closed_trades else {}

        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 1),
            "avg_return": round(avg_return, 2),
            "total_pnl": round(total_pnl, 2),
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        }
