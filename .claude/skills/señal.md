# SKILL: señal
**Trigger:** "dame una señal", "señal rápida", "¿compro?", "¿vendo?", "¿es buen momento para [activo]?"

## Qué hace esta skill

Genera una señal técnica rápida (sin el ciclo completo RIPER-5).

## Protocolo

### VELOCIDAD vs PROFUNDIDAD
Esta skill es para respuesta rápida. Para análisis profundo usar la skill `analizar`.

### ANÁLISIS EXPRESS (5 indicadores)
1. **RSI(14)**: <30 oversold→BUY, >70 overbought→SELL
2. **MACD**: cruce alcista→BUY, cruce bajista→SELL
3. **Precio vs SMA50**: sobre→bullish, bajo→bearish
4. **Precio vs SMA200**: sobre→bull market, bajo→bear market
5. **Volumen**: >150% del promedio → confirma la señal

### SISTEMA DE PUNTUACIÓN
```
+2 puntos: RSI oversold (<30)
+2 puntos: MACD cruce alcista
+1 punto: precio sobre SMA50
+1 punto: precio sobre SMA200
+1 punto: volumen elevado

-2 puntos: RSI overbought (>70)
-2 puntos: MACD cruce bajista
-1 punto: precio bajo SMA50
-1 punto: precio bajo SMA200

Score >= 3 → BUY
Score <= -3 → SELL
-2 a +2 → WATCH/HOLD
```

### OUTPUT ESPERADO

```
SEÑAL RÁPIDA: [SÍMBOLO]
Precio: €[X] | Score técnico: [N]/7

[BUY/SELL/WATCH] — Confianza: [X]%

Indicadores:
  RSI: [X] [señal]
  MACD: [señal]
  Tendencia: [señal]

Stop sugerido: €[X] | Target: €[X]

⚠️ Señal orientativa, no asesoramiento financiero.
```
