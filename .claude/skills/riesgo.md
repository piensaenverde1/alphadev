# SKILL: riesgo
**Trigger:** "cuánto arriesgar", "sizing", "posición", "stop-loss", "Kelly", "cuántas acciones comprar"

## Qué hace esta skill

Calcula el tamaño óptimo de posición usando el Half-Kelly Criterion y gestión de riesgo profesional.

## Protocolo

### INPUT NECESARIO
- Símbolo del activo
- Precio de entrada
- Capital disponible (default: 10.000€)
- Estadísticas de backtest si disponibles (win_rate, avg_win_pct, avg_loss_pct)

### CÁLCULO KELLY

```
Win Rate (W): histórico o 55% por defecto
Ratio recompensa/riesgo (b): avg_win / avg_loss
Full Kelly = (W * b - (1-W)) / b
Half Kelly = Full Kelly / 2   ← usamos esto (más conservador)
```

### CÁLCULO STOP-LOSS
1. Con ATR disponible: stop = precio - (1.5 × ATR)
2. Sin ATR: stop = precio × 0.95 (5% por debajo)
3. Mínimo siempre: precio × 0.98 (nunca más cerca del 2%)

### OUTPUT ESPERADO

```
SIZING PARA: [SÍMBOLO] @ €[PRECIO]
Capital disponible: €[CAPITAL]

KELLY CALCULATION:
  Win rate histórico: XX%
  Ratio R/R: X.X
  Half-Kelly fraction: X.XX% del capital

POSICIÓN RECOMENDADA:
  Valor a invertir: €[VALOR]
  Número de acciones: [N]
  
GESTIÓN DE RIESGO:
  Stop-loss: €[STOP] (-X.X% desde entrada)
  Take-profit: €[TARGET] (+X.X% desde entrada)
  Pérdida máxima si se activa stop: €[LOSS] (X% del capital)

VERIFICACIÓN DE LÍMITES:
  ✓/✗ Riesgo por operación < 2% del capital
  ✓/✗ Posición < 20% del portfolio total
  ✓/✗ Sector < 40% del portfolio
  ✓/✗ Riesgo total portfolio < 20%

⚠️ Este cálculo es orientativo. No es asesoramiento financiero.
```

## Comando CLI equivalente
```bash
python main.py --risk       # Análisis de riesgo del portfolio completo
python main.py --capital 25000  # Cambiar capital de referencia
```
