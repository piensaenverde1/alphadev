# Contexto Global — Asistente de Inversión Personal

> Archivo de memoria global. Se actualiza automáticamente tras cada sesión de análisis.
> Última actualización: ver timestamp en la base de datos SQLite.

---

## ARQUITECTURA DEL SISTEMA

**Stack principal:**
- Python 3.8+ — lenguaje base
- SQLite (`memory/investment.db`) — persistencia de todo el estado
- yfinance — datos de mercado (gratuito)
- CoinGecko API — datos de criptomonedas (gratuito)
- rich — interfaz terminal
- schedule — ejecución autónoma 24/7

**Proveedores de IA (en orden de prioridad):**
1. Anthropic (Claude) — si existe `ANTHROPIC_API_KEY`
2. Groq (Llama 3.1 70B) — si existe `GROQ_API_KEY` (gratuito)
3. Ollama (local) — si está disponible en localhost
4. Modo reglas — fallback sin IA, siempre disponible

---

## ESTRUCTURA DE AGENTES

```
Coordinador
├── AnalysisManager  → [MarketAgent, CryptoAgent, NewsAgent, SentimentAgent, MacroAgent, RealEstateAgent]
├── ExecutionManager → [RiskAgent, BacktestAgent, PortfolioAgent, OptionsAgent, PaperTradingAgent]
└── SystemManager    → [LearningEngine, TechAgent, AlertAgent, ReportAgent]
```

**Directorio base:** `/home/user/alphadev/investment_assistant/`

---

## CONVENCIONES DE CÓDIGO

- Todos los archivos Python usan type hints
- Cada agente hereda de `BaseAgent` (`agents/base.py`)
- Todos los agentes implementan `run() -> Dict`
- Los errores se capturan y devuelven como `{"error": str(e)}` — nunca se propagan
- Los datos de demo se usan cuando los APIs externos no están disponibles
- Todo texto al usuario: en español

---

## BASE DE DATOS

**Schema SQLite** (`memory/database.py`):
- `portfolio` — posiciones actuales
- `signals` — señales generadas con estado pending/correct/wrong
- `price_history` — histórico de precios
- `news` — noticias procesadas
- `github_tools` — herramientas GitHub escaneadas
- `lessons` — lecciones del motor de aprendizaje
- `reports` — informes generados
- `paper_trading` — cuentas de paper trading
- `paper_trades` — operaciones simuladas
- `alert_rules` — reglas de alertas personalizadas

---

## CONVENCIONES DE SIGNALS

```python
{
    "symbol": "AAPL",
    "action": "BUY",          # BUY | SELL | WATCH | HOLD
    "current_price": 213.50,
    "target": 235.00,
    "stop": 200.00,
    "confidence": 0.72,        # 0.0 a 1.0
    "reasoning": "RSI oversold + MACD crossover + volume surge",
    "sector": "technology",
    "fractional": False,       # True para crypto
}
```

---

## CONFIGURACIÓN DE RIESGO POR DEFECTO

- Capital default: 10.000€
- Riesgo máximo por operación: 2% del capital
- Riesgo máximo del portfolio: 20%
- Concentración máxima por posición: 20%
- Concentración máxima por sector: 40%
- Half-Kelly máximo: 25% del capital

---

## LECCIONES APRENDIDAS

Las lecciones se almacenan en SQLite y se inyectan automáticamente en los análisis.
Para ver las últimas lecciones: `python main.py --status`

---

## ARCHIVOS IMPORTANTES

| Archivo | Propósito |
|---------|-----------|
| `main.py` | CLI principal — punto de entrada |
| `scheduler.py` | Ejecución autónoma 24/7 |
| `demo.py` | Demo completa sin APIs externas |
| `agents/coordinator.py` | Orquestador de los 3 managers |
| `config/settings.py` | Configuración central + detección de IA |
| `memory/database.py` | Toda la persistencia SQLite |
| `tools/demo_data.py` | Datos estáticos de fallback |
| `.env` | Claves API (nunca en git) |
