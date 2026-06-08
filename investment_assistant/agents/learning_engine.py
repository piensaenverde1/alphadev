"""Motor de aprendizaje: evalúa predicciones pasadas y mejora el sistema."""
import json
from datetime import datetime, timedelta
from typing import Dict, List
from agents.base import BaseAgent
from memory.database import (
    get_pending_signals, resolve_signal, save_lesson,
    get_lessons, get_agent_accuracy
)
from tools.market_data import get_multiple_stocks
from tools.crypto_data import get_top_coins

SYSTEM_PROMPT = """Eres el motor de aprendizaje de un sistema de inversión automatizado.
Tu rol es analizar el desempeño pasado del sistema, identificar patrones de éxito
y fracaso, y generar lecciones que mejoren las predicciones futuras.

Analiza:
1. Señales que resultaron ganadoras vs perdedoras
2. En qué condiciones las señales fueron más acertadas
3. Qué tipo de análisis (técnico, noticias, crypto) fue más efectivo
4. Sesgos o errores sistemáticos en las predicciones

Genera lecciones concretas y accionables que puedan incluirse en los prompts
de los otros agentes para mejorar su rendimiento.

Responde siempre en español. Sé específico y práctico.
"""


class LearningEngine(BaseAgent):
    name = "learning_engine"
    description = "Evalúa predicciones pasadas y genera lecciones de mejora"

    def run(self) -> Dict:
        self.log("Iniciando ciclo de aprendizaje...")

        # 1. Evaluar señales pendientes
        evaluated = self._evaluate_pending_signals()
        self.log(f"Señales evaluadas: {len(evaluated)}")

        # 2. Calcular accuracy por agente
        accuracy = get_agent_accuracy()
        self.log(f"Accuracy calculada para {len(accuracy)} agentes")

        # 3. Cargar todas las lecciones actuales
        all_lessons = get_lessons(limit=30)

        # 4. Generar nuevas lecciones con IA
        new_lessons = []
        if accuracy and self.provider != "rules":
            accuracy_text = json.dumps(accuracy, indent=2, ensure_ascii=False)
            lessons_text = "\n".join([
                f"- [{l['agent_source']}] {l['lesson']} (validado {l['times_validated']}x, confianza: {l['confidence']})"
                for l in all_lessons[:15]
            ])
            evaluated_text = "\n".join([
                f"  {e['symbol']} ({e['agent_source']}): {e['action']} -> {e['outcome']} ({e.get('outcome_pct', 0):+.1f}%)"
                for e in evaluated[:10]
            ])

            response = self.ask_ai(
                SYSTEM_PROMPT,
                f"""Analiza el rendimiento del sistema de inversión:

ACCURACY POR AGENTE:
{accuracy_text}

SEÑALES EVALUADAS RECIENTEMENTE:
{evaluated_text if evaluated_text else "Sin señales evaluadas aún"}

LECCIONES EXISTENTES:
{lessons_text if lessons_text else "Sin lecciones previas"}

Genera un análisis en JSON con:
- "performance_summary": resumen del rendimiento general
- "best_performing_agent": qué agente acierta más y por qué
- "worst_performing_agent": qué agente falla más y por qué
- "new_lessons": lista de 3-5 nuevas lecciones concretas para mejorar (cada una con: agent, lesson, confidence)
- "system_improvements": mejoras estructurales recomendadas para el sistema
- "overall_score": puntuación del sistema 0-10 con justificación
""",
                max_tokens=2000
            )

            try:
                parsed = json.loads(response)
                for lesson_data in parsed.get("new_lessons", []):
                    save_lesson(
                        lesson_type="performance_review",
                        agent=lesson_data.get("agent", "general"),
                        context="Evaluación periódica de rendimiento",
                        lesson=lesson_data.get("lesson", ""),
                        confidence=lesson_data.get("confidence", 0.5)
                    )
                    new_lessons.append(lesson_data)
            except Exception:
                pass

        # 5. Generar informe de aprendizaje
        report = self._generate_learning_report(accuracy, evaluated, all_lessons, new_lessons)

        self.log(f"Ciclo de aprendizaje completado. {len(new_lessons)} nuevas lecciones")
        return {
            "agent": self.name,
            "signals_evaluated": len(evaluated),
            "agent_accuracy": accuracy,
            "lessons_total": len(all_lessons),
            "new_lessons": new_lessons,
            "learning_report": report,
        }

    def _evaluate_pending_signals(self) -> List[Dict]:
        """Evalúa señales pendientes comparando con precios actuales."""
        pending = get_pending_signals(days_old=7)
        if not pending:
            return []

        # Separar por tipo
        stock_signals = [s for s in pending if s["asset_type"] in ("stock", "etf")]
        crypto_signals = [s for s in pending if s["asset_type"] == "crypto"]

        # Obtener precios actuales
        current_prices: Dict[str, float] = {}

        if stock_signals:
            symbols = list(set(s["symbol"] for s in stock_signals))
            prices = get_multiple_stocks(symbols[:10])
            for p in prices:
                current_prices[p["symbol"]] = p.get("price", 0)

        if crypto_signals:
            top = get_top_coins(limit=50)
            for c in top:
                current_prices[c["symbol"]] = c.get("price", 0)

        evaluated = []
        for signal in pending:
            current = current_prices.get(signal["symbol"], 0)
            if not current or not signal["price_at_signal"]:
                continue

            original = signal["price_at_signal"]
            pct_change = (current / original - 1) * 100

            # Determinar outcome
            action = signal["action"]
            if action == "BUY":
                if pct_change > 3:
                    outcome = "WIN"
                elif pct_change < -3:
                    outcome = "LOSS"
                else:
                    outcome = "NEUTRAL"
            elif action == "SELL":
                if pct_change < -3:
                    outcome = "WIN"
                elif pct_change > 3:
                    outcome = "LOSS"
                else:
                    outcome = "NEUTRAL"
            else:
                outcome = "NEUTRAL"

            resolve_signal(signal["id"], outcome, current, pct_change)

            # Auto-aprender de pérdidas
            if outcome == "LOSS" and abs(pct_change) > 5:
                save_lesson(
                    lesson_type="signal_failure",
                    agent=signal["agent_source"],
                    context=f"{signal['symbol']}: {action} @ {original}, actual: {current}",
                    lesson=f"Señal {action} en {signal['symbol']} falló ({pct_change:+.1f}%). "
                           f"Razón original: {signal['reasoning'][:100]}",
                    confidence=0.7
                )

            # Auto-aprender de victorias
            if outcome == "WIN" and abs(pct_change) > 8:
                save_lesson(
                    lesson_type="signal_success",
                    agent=signal["agent_source"],
                    context=f"{signal['symbol']}: {action} @ {original}",
                    lesson=f"Señal {action} en {signal['symbol']} exitosa ({pct_change:+.1f}%). "
                           f"Indicadores clave: {signal['reasoning'][:100]}",
                    confidence=0.8
                )

            evaluated.append({
                **dict(signal),
                "current_price": current,
                "outcome": outcome,
                "outcome_pct": round(pct_change, 2),
            })

        return evaluated

    def _generate_learning_report(self, accuracy: Dict, evaluated: List,
                                   lessons: List, new_lessons: List) -> str:
        lines = [
            "=" * 50,
            "   INFORME DE APRENDIZAJE DEL SISTEMA",
            f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
        ]

        if accuracy:
            lines.append("\nRENDIMIENTO POR AGENTE:")
            for agent, stats in accuracy.items():
                lines.append(
                    f"  {agent}: {stats['win_rate']}% acierto "
                    f"({stats['wins']}W/{stats['losses']}L) | "
                    f"Retorno promedio: {stats['avg_return']:+.1f}%"
                )
        else:
            lines.append("\nAún no hay suficientes señales evaluadas para calcular accuracy.")

        if evaluated:
            lines.append(f"\nSEÑALES EVALUADAS HOY: {len(evaluated)}")
            wins = sum(1 for e in evaluated if e["outcome"] == "WIN")
            losses = sum(1 for e in evaluated if e["outcome"] == "LOSS")
            lines.append(f"  Ganadoras: {wins} | Perdedoras: {losses}")

        if new_lessons:
            lines.append(f"\nNUEVAS LECCIONES GENERADAS: {len(new_lessons)}")
            for l in new_lessons:
                lines.append(f"  → {l.get('lesson', '')[:100]}")

        lines.append(
            f"\nTOTAL LECCIONES ACUMULADAS: {len(lessons)}"
        )
        lines.append("=" * 50)

        return "\n".join(lines)
