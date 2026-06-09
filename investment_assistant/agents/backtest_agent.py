"""Agente de backtesting: valida estrategias con datos históricos."""
import json
from typing import Dict, List
from agents.base import BaseAgent
from memory.database import save_lesson, save_report

SYSTEM_PROMPT = """Eres un analista cuantitativo experto en backtesting de estrategias de inversión.
Tu misión es interpretar resultados de backtests y extraer conclusiones accionables.

Evalúas:
- Si una estrategia es estadísticamente sólida o es overfitting
- Si el Sharpe ratio justifica el riesgo tomado (>1.0 es bueno, >2.0 es excelente)
- Si el max drawdown es aceptable para un inversor particular
- Qué condiciones de mercado favorecen cada estrategia
- Cuál es la estrategia óptima para cada tipo de activo

Siempre recuerdas que el pasado no garantiza el futuro.
Responde en español. Sé preciso con los números.
"""


class BacktestAgent(BaseAgent):
    name = "backtest_agent"
    description = "Valida estrategias con backtesting histórico y optimiza parámetros"

    def run(self, symbols: List[str] = None) -> Dict:
        from tools.backtester import BacktestEngine
        from tools.optimizer import ParameterOptimizer
        from config.settings import DEFAULT_STOCKS, DEFAULT_ETFS

        symbols = symbols or (DEFAULT_STOCKS[:3] + DEFAULT_ETFS[:2])
        self.log(f"Iniciando backtesting para {len(symbols)} símbolos...")

        engine = BacktestEngine()
        optimizer = ParameterOptimizer()

        all_results = {}
        best_strategies = {}
        optimized_params = {}

        for sym in symbols:
            self.log(f"  Backtesting {sym}...")
            results = engine.run_all_strategies(sym)
            all_results[sym] = results

            # Determinar mejor estrategia
            if results:
                valid = {k: v for k, v in results.items()
                         if isinstance(v, dict) and "sharpe_ratio" in v and v.get("sharpe_ratio", 0) > 0}
                if valid:
                    best = max(valid.items(), key=lambda x: x[1].get("sharpe_ratio", 0))
                    best_strategies[sym] = {
                        "strategy": best[0],
                        "sharpe": best[1].get("sharpe_ratio", 0),
                        "return": best[1].get("total_return_pct", 0),
                        "drawdown": best[1].get("max_drawdown_pct", 0),
                        "win_rate": best[1].get("win_rate", 0),
                    }

            # Optimizar parámetros RSI
            self.log(f"  Optimizando parámetros para {sym}...")
            params = optimizer.get_optimal_params(sym)
            optimized_params[sym] = params

        # Análisis IA de los resultados
        ai_analysis = ""
        if best_strategies and self.provider != "rules":
            results_text = "\n".join([
                f"  {sym}: Mejor={data['strategy']} | Sharpe={data['sharpe']:.2f} | "
                f"Return={data['return']:+.1f}% | Drawdown={data['drawdown']:.1f}% | "
                f"WinRate={data['win_rate']:.0f}%"
                for sym, data in best_strategies.items()
            ])

            params_text = "\n".join([
                f"  {sym}: RSI period={p.get('rsi_params', {}).get('period', 14)}, "
                f"oversold={p.get('rsi_params', {}).get('oversold', 30)}"
                for sym, p in optimized_params.items()
            ])

            ai_analysis = self.ask_ai(
                SYSTEM_PROMPT,
                f"""Analiza estos resultados de backtesting:

MEJORES ESTRATEGIAS POR ACTIVO:
{results_text}

PARÁMETROS OPTIMIZADOS:
{params_text}

Responde en JSON con:
- "overall_assessment": evaluación general (1-2 frases)
- "recommended_strategies": {{symbol: {{strategy, why, confidence}}}} para las 3 mejores oportunidades
- "risk_warnings": advertencias sobre activos con alto drawdown
- "parameter_insights": qué nos dicen los parámetros optimizados sobre cada mercado
- "backtesting_caveats": limitaciones importantes del análisis
""",
                max_tokens=1500
            )

        # Guardar lecciones
        for sym, data in best_strategies.items():
            if data.get("sharpe", 0) > 1.5:
                save_lesson(
                    lesson_type="backtest_insight",
                    agent=self.name,
                    context=f"Backtest {sym} - estrategia {data['strategy']}",
                    lesson=f"En {sym}, la estrategia {data['strategy']} mostró Sharpe={data['sharpe']:.2f} "
                           f"con win_rate={data['win_rate']:.0f}%. Priorizar esta señal.",
                    confidence=min(0.85, data["sharpe"] / 3)
                )

        self.log(f"Backtesting completado: {len(best_strategies)} activos analizados")
        return {
            "agent": self.name,
            "symbols_tested": len(symbols),
            "all_results": all_results,
            "best_strategies": best_strategies,
            "optimized_params": optimized_params,
            "ai_analysis": ai_analysis,
        }
