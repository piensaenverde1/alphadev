"""Agente especialista en análisis y gestión de portfolios."""
import json
from datetime import datetime
from typing import Dict, List, Optional

from agents.base import BaseAgent
from core.portfolio import Portfolio
from tools.market_data import get_multiple_stocks, get_technical_signals
from tools.risk_analyzer import RiskAnalyzer
from memory.database import save_lesson, save_price, get_lessons
from config.settings import DEFAULT_STOCKS

SYSTEM_PROMPT = """Eres un analista especialista en salud y gestión de portfolios de inversión.
Tu rol es evaluar la composición del portfolio, identificar riesgos de concentración,
y proporcionar recomendaciones concretas de rebalanceo y diversificación.

Responde siempre en español. Sé directo y accionable.
Cuando evalúes un portfolio:
1. Analiza la diversificación real (no sólo el número de activos)
2. Identifica correlaciones peligrosas entre posiciones
3. Evalúa la exposición sectorial y geográfica
4. Calcula el riesgo real ajustado por escenarios adversos
5. Proporciona un plan de rebalanceo concreto con prioridades
6. Considera el coste fiscal de las operaciones de rebalanceo

Responde en formato JSON con las claves:
"health_score" (0-10), "main_risks", "rebalancing_plan", "diversification_gaps", "summary"
"""


class PortfolioAgent(BaseAgent):
    name = "portfolio_specialist"
    description = "Analiza la salud del portfolio, diversificación y sugiere rebalanceos"

    def run(self, capital: float = 10000.0) -> Dict:
        self.log("Iniciando análisis completo de portfolio...")

        portfolio = Portfolio(cash=capital)
        risk_analyzer = RiskAnalyzer()

        # 1. Obtener posiciones actuales con precios actualizados
        self.log("Cargando posiciones con precios actuales...")
        try:
            summary = portfolio.get_summary(refresh_prices=True)
            positions = summary.get("positions", [])
        except Exception as e:
            self.log(f"Error al cargar portfolio: {e}")
            positions = []
            summary = {
                "total_positions": 0,
                "total_invested": 0.0,
                "total_current_value": capital,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "by_type": {},
                "cash": capital,
                "winners": 0,
                "losers": 0,
                "best_position": None,
                "worst_position": None,
            }

        # Serializar posiciones para el resultado
        positions_data = []
        for p in positions:
            positions_data.append({
                "symbol": p.symbol,
                "name": p.name,
                "asset_type": p.asset_type,
                "quantity": p.quantity,
                "avg_buy_price": round(p.avg_buy_price, 2),
                "current_price": round(p.current_price, 2),
                "current_value": round(p.current_value, 2),
                "total_invested": round(p.total_invested, 2),
                "pnl": round(p.pnl, 2),
                "pnl_pct": round(p.pnl_pct, 2),
            })

        # Guardar precios en historial
        for p in positions:
            try:
                save_price(p.symbol, p.asset_type, p.current_price)
            except Exception:
                pass

        # 2. Calcular métricas completas del portfolio
        self.log("Calculando métricas del portfolio...")
        total_value = summary.get("total_current_value", capital)
        total_invested = summary.get("total_invested", 0.0)
        total_pnl = summary.get("total_pnl", 0.0)
        total_pnl_pct = summary.get("total_pnl_pct", 0.0)

        # Desglose por tipo de activo
        by_type = summary.get("by_type", {})
        by_type_pct = {}
        if total_value > 0:
            for asset_type, value in by_type.items():
                by_type_pct[asset_type] = round(value / total_value * 100, 1)

        # 3. Stress test del portfolio
        self.log("Ejecutando stress test...")
        stress_test = {}
        try:
            risk_positions = [
                {
                    "symbol": p.symbol,
                    "value": p.current_value,
                    "beta": 1.0,
                    "sector": p.asset_type,
                }
                for p in positions
            ]
            if risk_positions:
                stress_test = risk_analyzer.stress_test(total_value, risk_positions)
            else:
                stress_test = {
                    "crash_20pct": {"portfolio_original": total_value, "portfolio_new": total_value * 0.80, "total_change_pct": -20.0},
                    "bear_market_40pct": {"portfolio_original": total_value, "portfolio_new": total_value * 0.60, "total_change_pct": -40.0},
                    "bull_run_30pct": {"portfolio_original": total_value, "portfolio_new": total_value * 1.30, "total_change_pct": 30.0},
                }
        except Exception as e:
            self.log(f"Error en stress test: {e}")
            stress_test = {"error": str(e)}

        # 4. Calcular correlación y concentración (HHI)
        self.log("Calculando concentración y correlación...")
        portfolio_analysis = {}
        hhi = 0.0
        correlation = {}
        try:
            if positions and total_value > 0:
                risk_positions_full = [
                    {
                        "symbol": p.symbol,
                        "value": p.current_value,
                        "sector": p.asset_type,
                    }
                    for p in positions
                ]
                weights = [p.current_value / total_value for p in positions]
                hhi = sum(w ** 2 for w in weights)

                # Intentar análisis completo de correlación si hay datos históricos suficientes
                from memory.database import get_price_history
                price_history: Dict[str, List[float]] = {}
                for p in positions:
                    hist = get_price_history(p.symbol, days=30)
                    if len(hist) >= 5:
                        price_history[p.symbol] = [h["price"] for h in hist]

                if len(price_history) >= 2:
                    pa = risk_analyzer.analyze_portfolio(risk_positions_full, price_history)
                    portfolio_analysis = pa
                    correlation = pa.get("correlation_matrix", {})
                else:
                    portfolio_analysis = {
                        "concentration_risk": round(hhi, 4),
                        "diversification_score": round(max(0, (1 - hhi) * 10), 2),
                        "sector_exposure": by_type_pct,
                        "recommendations": ["Historial de precios insuficiente para correlación completa."],
                    }
                    correlation = {}
        except Exception as e:
            self.log(f"Error en análisis de correlación: {e}")
            portfolio_analysis = {"error": str(e)}

        # 5. Detectar concentración excesiva y guardar lección
        if hhi > 0.5 and positions:
            dominant = max(positions, key=lambda p: p.current_value)
            dominant_pct = round(dominant.current_value / total_value * 100, 1) if total_value > 0 else 0
            lesson_context = (
                f"Portfolio con {len(positions)} posiciones, "
                f"HHI={hhi:.3f}, posición dominante: {dominant.symbol} ({dominant_pct}%)"
            )
            lesson_text = (
                f"Portfolio excesivamente concentrado (HHI={hhi:.3f} > 0.5). "
                f"{dominant.symbol} representa el {dominant_pct}% del portfolio. "
                f"Diversificar reduciendo exposición a posición dominante."
            )
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=lesson_context,
                    lesson=lesson_text,
                    confidence=0.85,
                )
                self.log(f"Lección guardada: concentración excesiva en {dominant.symbol}")
            except Exception as e:
                self.log(f"Error guardando lección: {e}")

        # 6. Análisis IA
        self.log("Generando análisis IA del portfolio...")
        ai_analysis = ""
        if self.provider != "rules":
            lessons_ctx = self.get_lessons_context()

            # Preparar datos clave para el prompt
            stress_summary = ""
            if "crash_20pct" in stress_test:
                s20 = stress_test["crash_20pct"]
                s40 = stress_test.get("bear_market_40pct", {})
                s30 = stress_test.get("bull_run_30pct", {})
                stress_summary = (
                    f"  Crash -20%: nuevo valor = {s20.get('portfolio_new', 0):.2f} "
                    f"(cambio: {s20.get('total_change_pct', 0):+.1f}%)\n"
                    f"  Bear -40%: nuevo valor = {s40.get('portfolio_new', 0):.2f} "
                    f"(cambio: {s40.get('total_change_pct', 0):+.1f}%)\n"
                    f"  Bull +30%: nuevo valor = {s30.get('portfolio_new', 0):.2f} "
                    f"(cambio: {s30.get('total_change_pct', 0):+.1f}%)"
                )

            positions_summary = "\n".join([
                f"  {p['symbol']} ({p['asset_type']}): "
                f"${p['current_value']:.2f} | P&L: {p['pnl_pct']:+.1f}%"
                for p in positions_data
            ]) or "  (portfolio vacío)"

            recommendations_text = "\n".join(
                f"  - {r}" for r in portfolio_analysis.get("recommendations", [])
            )

            user_message = f"""Analiza la salud de este portfolio de inversión:

RESUMEN GENERAL:
  Valor total: ${total_value:.2f}
  Total invertido: ${total_invested:.2f}
  P&L total: ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)
  Posiciones: {len(positions_data)}
  Efectivo disponible: ${summary.get('cash', 0):.2f}

POSICIONES:
{positions_summary}

DISTRIBUCIÓN POR TIPO:
{json.dumps(by_type_pct, indent=2)}

MÉTRICAS DE CONCENTRACIÓN:
  HHI (Herfindahl): {hhi:.4f} (>0.5 = muy concentrado, <0.25 = bien diversificado)
  Score diversificación: {portfolio_analysis.get('diversification_score', 'N/A')}/10

STRESS TEST:
{stress_summary}

RECOMENDACIONES TÉCNICAS PREVIAS:
{recommendations_text}

{lessons_ctx}

Proporciona tu evaluación en formato JSON con:
"health_score" (0-10), "main_risks" (lista), "rebalancing_plan" (lista de pasos concretos),
"diversification_gaps" (qué falta), "summary" (párrafo ejecutivo en español)
"""
            try:
                ai_analysis = self.ask_ai(
                    SYSTEM_PROMPT + ("\n\n" + lessons_ctx if lessons_ctx else ""),
                    user_message,
                    max_tokens=1500,
                )
            except Exception as e:
                ai_analysis = f"[Error en análisis IA: {e}]"

        self.log(f"Análisis de portfolio completado. {len(positions_data)} posiciones analizadas.")

        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "positions": positions_data,
            "summary": {
                "total_value": round(total_value, 2),
                "total_invested": round(total_invested, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 2),
                "cash": round(summary.get("cash", 0), 2),
                "num_positions": len(positions_data),
                "by_type": by_type,
                "by_type_pct": by_type_pct,
                "best_position": summary.get("best_position"),
                "worst_position": summary.get("worst_position"),
                "winners": summary.get("winners", 0),
                "losers": summary.get("losers", 0),
            },
            "concentration": {
                "hhi": round(hhi, 4),
                "hhi_interpretation": (
                    "alta concentración" if hhi > 0.5
                    else "concentración moderada" if hhi > 0.25
                    else "bien diversificado"
                ),
                "diversification_score": portfolio_analysis.get("diversification_score"),
                "sector_exposure": portfolio_analysis.get("sector_exposure", by_type_pct),
            },
            "stress_test": stress_test,
            "correlation": correlation,
            "recommendations": portfolio_analysis.get("recommendations", []),
            "ai_analysis": ai_analysis,
        }
