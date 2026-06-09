import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# IA Provider
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
NO_AI = os.getenv("NO_AI", "false").lower() == "true"

# Proveedor activo (detecta automáticamente)
def get_ai_provider() -> str:
    if NO_AI:
        return "rules"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    if GROQ_API_KEY:
        return "groq"
    try:
        import requests
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass
    return "rules"

# Base de datos local
DB_PATH = BASE_DIR / "memory" / "investment.db"
DB_PATH.parent.mkdir(exist_ok=True)

# Portfolio
PORTFOLIO_CURRENCY = os.getenv("PORTFOLIO_CURRENCY", "EUR")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Activos por defecto a monitorear
DEFAULT_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "ASML", "SAP", "NOVO-B.CO"
]
DEFAULT_ETFS = [
    "SPY", "QQQ", "VTI", "VWRL.L", "IWDA.AS",
    "CSPX.L", "EEM", "GLD", "TLT"
]
DEFAULT_CRYPTO = [
    "bitcoin", "ethereum", "solana", "cardano",
    "polkadot", "chainlink", "avalanche-2", "uniswap"
]

# GitHub topics a monitorear
GITHUB_TOPICS = [
    "algorithmic-trading", "portfolio-management",
    "crypto-trading", "quantitative-finance",
    "stock-market", "fintech", "backtesting",
    "real-estate-investing", "personal-finance"
]

# RSS Feeds de noticias financieras (100% gratuitas)
NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.investing.com/rss/news.rss",
]

# Modelos IA por proveedor
AI_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",  # Más barato
    "groq": "llama-3.1-8b-instant",             # Gratis
    "ollama": "llama3.1",                        # Local gratis
}

# Scheduler
DAILY_RUN_TIME = "08:00"    # Hora del análisis diario
WEEKLY_RUN_DAY = "monday"   # Día del informe semanal
