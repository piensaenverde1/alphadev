# SKILL: analizar
**Trigger:** cuando el usuario dice "analiza", "análisis", "qué hace", "cómo está", "revisa" + un símbolo o activo

## Qué hace esta skill

Ejecuta el ciclo completo RIPER-5 para un activo:
**R**esearch → **I**nnovate → **P**lan → **E**xecute → **U**pdate

## Protocolo

### FASE 1 — RESEARCH (solo lectura)
- Obtener precio actual, histórico 90 días, volumen
- Calcular indicadores técnicos: RSI(14), MACD(12,26,9), Bollinger Bands, SMA50, SMA200
- Leer noticias recientes del activo (últimas 24h)
- Revisar lecciones previas sobre este símbolo en la base de datos
- Revisar correlaciones con otros activos del portfolio

### FASE 2 — INNOVATE (análisis)
- ¿Está el precio por encima o debajo de SMA50/SMA200?
- ¿RSI en zona de sobrecompra (>70), sobreventa (<30) o neutral?
- ¿Hay divergencia MACD? ¿Cruce alcista o bajista?
- ¿Qué dice el sentimiento de las noticias?
- ¿Qué ha pasado históricamente cuando estas condiciones se dieron?

### FASE 3 — PLAN
- Determinar acción: BUY / SELL / WATCH / HOLD
- Calcular nivel de confianza (0-100%)
- Calcular stop-loss usando ATR si disponible, sino 5% fijo
- Calcular take-profit usando ratio riesgo/recompensa histórico
- Aplicar Half-Kelly para sizing de posición

### FASE 4 — EXECUTE (presentar al usuario)
Presentar en este formato:

```
ANÁLISIS: [SÍMBOLO] — [ACCIÓN]
Precio actual: €XXX | Confianza: XX%

TÉCNICO:
  RSI(14): XX (sobreventa/neutral/sobrecompra)
  MACD: [señal]
  Tendencia: [alcista/bajista/lateral]

ACCIÓN RECOMENDADA:
  → [ACCIÓN] con confianza [XX%]
  Stop-loss: €XXX (-X%)
  Take-profit: €XXX (+X%)
  Tamaño sugerido: X acciones (€XXX) [con capital de €10.000]

RAZONAMIENTO:
  [Explicación en 2-3 frases]

⚠️ Esto no es asesoramiento financiero oficial.
```

### FASE 5 — UPDATE
- Registrar la señal en la base de datos para evaluación posterior
- Actualizar contexto de mercado si es relevante

## Comandos CLI equivalentes
```bash
python main.py                    # Análisis de todos los activos
python main.py --quick            # Solo acciones + cripto + noticias
python main.py --backtest [SYMS]  # Añadir backtesting histórico
```
