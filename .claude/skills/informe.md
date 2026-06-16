# SKILL: informe
**Trigger:** "dame el informe", "resumen del día", "qué debería hacer hoy", "informe ejecutivo", "qué pasa en el mercado"

## Qué hace esta skill

Genera el informe ejecutivo completo del día integrando todos los análisis disponibles.

## Protocolo

### ESTRUCTURA DEL INFORME EJECUTIVO

```
════════════════════════════════════════════════════════════
   INFORME EJECUTIVO DE INVERSIÓN — [FECHA]
   Asistente Personal de Inversión v3.0
════════════════════════════════════════════════════════════

RESUMEN EJECUTIVO (3-4 frases)
[Estado del mercado hoy, principales movimientos, qué hacer]

DIAGNÓSTICO DE MERCADO
  Dirección: [BULLISH/BEARISH/NEUTRAL]
  VIX: [X] → [CALMA/INCERTIDUMBRE/PÁNICO]
  Ciclo: [EXPANSIÓN/PICO/CONTRACCIÓN/RECUPERACIÓN]
  Sentimiento: [score y descripción]

ACCIONES PRIORITARIAS
  1. [ACCIÓN]: [SÍMBOLO] — [razonamiento en 1 frase]
     Sizing: [N] acc @ €[X] | Stop: €[X] | Target: €[X]
  2. [ACCIÓN]: [SÍMBOLO] — [razonamiento]
  3. [ACCIÓN]: [SÍMBOLO] — [razonamiento]

SEÑALES DEL DÍA
  COMPRAS:  [lista]
  VENTAS:   [lista]
  VIGILAR:  [lista]

TU PORTFOLIO
  Valor total: €[X] | P&L: €[X] ([X]%)
  [Consejo específico basado en posiciones actuales]

NIVEL DE RIESGO DEL MERCADO: [BAJO/MEDIO/ALTO]
  [Explicación en 1 frase]

NOTA DE APRENDIZAJE
  [Cómo ha mejorado el sistema desde ayer]

════════════════════════════════════════════════════════════
⚠️ Este informe es orientativo. No es asesoramiento financiero
oficial. Consulta con un profesional antes de invertir.
════════════════════════════════════════════════════════════
```

## Comando CLI equivalente
```bash
python main.py              # Análisis completo con informe
python main.py --quick      # Informe rápido (sin GitHub/learning)
```
