# SKILL: portfolio
**Trigger:** "mi portfolio", "mis posiciones", "cómo va mi inversión", "diversificación", "rebalancear"

## Qué hace esta skill

Analiza la salud completa del portfolio con stress tests, concentración y recomendaciones.

## Protocolo

### 1. ESTADO ACTUAL
- Listar todas las posiciones con precio actual y P&L
- Calcular P&L total (€ y %)
- Identificar mejor y peor posición
- Contar ganadores vs perdedores

### 2. ANÁLISIS DE CONCENTRACIÓN (HHI)
```
HHI = Σ (peso_i)²
  < 0.25 → bien diversificado
  0.25-0.50 → concentración moderada
  > 0.50 → alta concentración (¡alerta!)
```

### 3. STRESS TEST
Simular tres escenarios de mercado:
- Crash moderado (-20%): ¿cuánto perderías?
- Crash severo (-40%): ¿cuánto perderías?
- Rally alcista (+30%): ¿cuánto ganarías?

### 4. ANÁLISIS DE CORRELACIÓN
- ¿Están los activos correlacionados entre sí?
- Correlación alta (>0.7): peligro, no hay diversificación real
- Correlación baja (<0.3): buena diversificación

### OUTPUT ESPERADO

```
ESTADO DEL PORTFOLIO — [FECHA]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSICIONES:
  [SYM]  [N] acc @ €[AVG] → €[ACTUAL] | P&L: €[PNL] ([%]%)
  ...
  TOTAL: €[VALOR] | P&L: €[PNL_TOTAL] ([%_TOTAL]%)

DIVERSIFICACIÓN:
  HHI: [X.XX] → [Interpretación]
  Mayor exposición: [SYM] ([X]%)
  Sectores: [breakdown]

STRESS TEST:
  Crash -20%: portfolio valdría €[X] (pérdida de €[Y])
  Crash -40%: portfolio valdría €[X] (pérdida de €[Y])
  Rally +30%: portfolio valdría €[X] (ganancia de €[Y])

RECOMENDACIONES:
  [Lista de 1-3 acciones concretas]

⚠️ Análisis orientativo. No es asesoramiento financiero.
```

## Comando CLI equivalente
```bash
python main.py --portfolio
python main.py --add AAPL 10 213.50   # Añadir posición
python main.py --remove AAPL          # Eliminar posición
```
