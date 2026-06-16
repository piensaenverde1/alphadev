# Contexto de Inversión — Estrategias y Lecciones

> Memoria de dominio: estrategias de inversión, señales históricas, lecciones del sistema.
> Se actualiza automáticamente tras cada ciclo de aprendizaje.

---

## ESTRATEGIAS ACTIVAS

### Estrategia principal: Análisis Técnico Multi-Indicador
**Indicadores usados:** RSI(14), MACD(12,26,9), Bollinger Bands(20,2), SMA50, SMA200
**Señal de compra:** Score técnico >= 3/7 de los indicadores en zona positiva
**Señal de venta:** Score técnico <= -3/7
**Gestión de riesgo:** Half-Kelly Criterion con stop-loss dinámico basado en ATR

### Estrategia secundaria: Momentum de Criptomonedas
**Fuente:** CoinGecko API (top 50 por capitalización)
**Señal:** Cambio >10% en 24h + volumen >200% del promedio + RSI <70
**Tamaño:** Posiciones más pequeñas (max 1% riesgo por operación en cripto)
**Stop-loss:** 8% fijo (mayor volatilidad requiere stop más amplio)

### Estrategia de cobertura (cuando portfolio >15.000€)
**Protective Put:** en posiciones con ganancias >20%
**Covered Call:** en posiciones sobrecompradas (RSI >70)
**Collar:** para posiciones grandes en mercados de alta incertidumbre (VIX >25)

---

## REGLAS DE INVERSIÓN (no negociables)

1. Nunca más del 2% del capital total en riesgo por operación
2. Diversificación mínima: al menos 5 activos diferentes antes de considerar concentración
3. Rebalanceo cuando un activo supera el 25% del portfolio
4. Stop-loss obligatorio en cada posición (sin excepción)
5. No invertir en activos sin datos de histórico mínimo de 90 días
6. En mercados VIX >30: reducir exposición total al 50%

---

## LECCIONES APRENDIDAS (auto-actualizado)

*Las lecciones se leen de la base de datos SQLite. Este archivo muestra las más importantes del histórico.*

### Patrones que funcionan
- RSI oversold (<30) + MACD cruce alcista = señal de alta confianza
- Precio rebotando en SMA200 + volumen elevado = suelo probable
- Noticias positivas + momentum técnico = confirmar antes de actuar

### Patrones que fallan
- RSI overbought (>70) no garantiza caída inmediata (puede seguir subiendo)
- MACD cruce bajista en mercado alcista = muchas falsas señales
- Noticias negativas de corto plazo en activos con fundamentos sólidos = oportunidad

---

## ACTIVOS BAJO SEGUIMIENTO

### Acciones y ETFs (DEFAULT_STOCKS de config/settings.py)
Incluye: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, JPM, V, MA, SPY, QQQ, VTI

### Criptomonedas (DEFAULT_CRYPTO)
Incluye: BTC, ETH, SOL, ADA, AVAX, DOT, LINK

### REITs (RealEstateAgent)
Incluye: IYR, VNQ, XLRE, AMT, PLD, EQIX, SPG, O

### Macroeconómicos
Incluye: ^VIX, ^GSPC (S&P500), ^TNX (US10Y), ^IRX (US2Y), DX-Y.NYB (USD), GC=F (Oro), CL=F (Petróleo)
