# Contexto del Sistema — Estado y Rendimiento

> Memoria de dominio: estado de los agentes, métricas de rendimiento del sistema.
> Se actualiza con cada ciclo de aprendizaje.

---

## ESTADO DE LOS AGENTES

### Agentes de Análisis
| Agente | Estado | Win Rate | Señales totales |
|--------|--------|----------|----------------|
| MarketAgent | Activo | (ver DB) | (ver DB) |
| CryptoAgent | Activo | (ver DB) | (ver DB) |
| NewsAgent | Activo | N/A | (ver DB) |
| SentimentAgent | Activo | N/A | (ver DB) |
| MacroAgent | Activo | N/A | (ver DB) |
| RealEstateAgent | Activo | (ver DB) | (ver DB) |

### Agentes de Ejecución
| Agente | Estado | Última ejecución |
|--------|--------|-----------------|
| RiskAgent | Activo | (ver DB) |
| BacktestAgent | Activo | (ver DB) |
| PortfolioAgent | Activo | (ver DB) |
| OptionsAgent | Activo | (ver DB) |
| PaperTradingAgent | Activo | (ver DB) |

### Agentes de Sistema
| Agente | Estado | Última ejecución |
|--------|--------|-----------------|
| LearningEngine | Activo | Diario 18:00 |
| TechAgent | Activo | Semanal lunes |
| AlertAgent | Activo | Bajo demanda |
| ReportAgent | Activo | Diario 08:00 |

---

## FUENTES DE DATOS — DISPONIBILIDAD

| Fuente | Estado esperado | Fallback |
|--------|----------------|---------|
| yfinance | Disponible en prod | demo_data.py |
| CoinGecko API | Disponible en prod | demo_data.py |
| GitHub API | Disponible con token | búsqueda básica |
| RSS Feeds | Disponible en prod | noticias vacías |
| Groq API | Con GROQ_API_KEY | modo reglas |
| Anthropic API | Con ANTHROPIC_API_KEY | Groq/reglas |

---

## MÉTRICAS DE CALIDAD DEL SISTEMA

### Objetivos
- Win rate global: >55%
- Señales por día: 5-15 (calidad > cantidad)
- Agentes fallando: 0 (todos deben tener fallback)
- Tiempo de ejecución análisis completo: <120 segundos

### Alerta si
- Win rate cae por debajo del 45% durante 2 semanas
- Más de 2 agentes fallando simultáneamente
- Base de datos sin actualización hace >48h en modo autónomo

---

## SCHEDULE AUTÓNOMO

```
08:00 diario    → Análisis completo del día (todos los agentes)
18:00 diario    → Ciclo de aprendizaje (evalúa señales de 7 días atrás)
Cada 2 horas    → Snapshot de precios (sin análisis completo)
Lunes 09:00     → Análisis semanal (con backtest + tech scout)
```

Para activar el modo autónomo:
```bash
python scheduler.py
```

---

## HISTORIAL DE MEJORAS DEL SISTEMA

### v1.0 — Sistema base
- Agentes: market, crypto, news, tech, learning, backtest, risk

### v2.0 — Integración de herramientas open-source
- Backtrader, Vectorbt, Pyfolio, Black-Scholes, Kelly Criterion
- Paper trading con export freqtrade
- Sentimiento avanzado FinBERT/lexicón
- Alertas Telegram

### v3.0 — Arquitectura de 3 capas (actual)
- 9 agentes especialistas
- 3 managers (Analysis, Execution, System)
- 1 coordinador central
- Skills system (este directorio)
- Memoria de contexto en markdown (RIPER-5)
- Optimización de tokens ECC-style
- Hook de inicio de sesión
