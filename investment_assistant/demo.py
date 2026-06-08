#!/usr/bin/env python3
"""
DEMO del Asistente de Inversión (datos de muestra para entornos sin internet).
En tu máquina con conexión real, usa main.py para datos en tiempo real.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from memory.database import init_db, save_signal, save_price, save_github_tool, save_news
from tools.demo_data import (
    DEMO_MARKET_OVERVIEW, DEMO_STOCKS, DEMO_CRYPTO_GLOBAL,
    DEMO_CRYPTO_COINS, DEMO_NEWS, DEMO_GITHUB_TOOLS
)
from core.reporter import (
    console, print_header, print_market_overview, print_signals,
    print_crypto_overview, print_news_mood, print_github_tools,
    print_ai_synthesis, print_learning_stats
)
from tools.news_fetcher import get_market_mood, get_trending_topics
from memory.database import get_agent_accuracy, get_lessons

console = Console()


def load_demo_data():
    """Carga datos de demostración en la BD local."""
    # Precios históricos
    for stock in DEMO_STOCKS:
        save_price(stock["symbol"], "stock", stock["current_price"],
                   change_pct=stock["change_5d_pct"])

    for coin in DEMO_CRYPTO_COINS:
        save_price(coin["symbol"], "crypto", coin["price"],
                   change_pct=coin["change_24h"])

    # Señales demo
    actionable_stocks = [s for s in DEMO_STOCKS if s["action"] in ("BUY", "SELL", "WATCH")]
    saved_signals = []
    for s in actionable_stocks:
        price = s["current_price"]
        target = price * 1.10 if s["action"] == "BUY" else price * 0.92
        stop = price * 0.95 if s["action"] == "BUY" else price * 1.05
        conf = min(1.0, abs(s["technical_score"]) / 4)
        sig_id = save_signal(
            symbol=s["symbol"], asset_type="stock",
            action=s["action"], confidence=conf,
            reasoning=" | ".join(s.get("signals", [])[:2]),
            price=price, target=round(target, 2), stop=round(stop, 2),
            horizon="MEDIUM", source="market_analyst"
        )
        saved_signals.append({**s, "signal_id": sig_id, "target": round(target, 2), "stop": round(stop, 2), "confidence": conf})

    # Noticias
    for news in DEMO_NEWS:
        save_news(
            title=news["title"], url=news["url"], source=news["source"],
            sentiment=news["sentiment"], score=news["sentiment_score"],
            symbols=news["related_symbols"], summary=news["summary"],
            published=news["published_at"]
        )

    # GitHub tools
    for tool in DEMO_GITHUB_TOOLS:
        save_github_tool(tool)

    # Crypto signals
    crypto_signals = []
    for coin in DEMO_CRYPTO_COINS:
        score = 0
        reasons = []
        c24 = coin["change_24h"]
        c7d = coin["change_7d"]
        ath_pct = coin["ath_change_pct"]

        if c24 > 3:
            score += 1
            reasons.append(f"Momentum +{c24:.1f}% (24h)")
        if c7d > 10:
            score += 1
            reasons.append(f"Tendencia semanal alcista +{c7d:.1f}%")
        if ath_pct < -60:
            score += 1
            reasons.append(f"Lejos del ATH ({ath_pct:.0f}%) - potencial")

        action = "BUY" if score >= 2 else "WATCH" if score == 1 else "HOLD"
        if action in ("BUY", "WATCH"):
            price = coin["price"]
            target = price * 1.20
            stop = price * 0.85
            conf = min(1.0, score / 3)
            sig_id = save_signal(
                symbol=coin["symbol"], asset_type="crypto",
                action=action, confidence=conf,
                reasoning=" | ".join(reasons),
                price=price, target=round(target, 4), stop=round(stop, 4),
                horizon="SHORT", source="crypto_analyst"
            )
            crypto_signals.append({
                **coin, "action": action, "confidence": conf,
                "signal_id": sig_id, "reasons": reasons,
                "target": round(target, 4), "stop": round(stop, 4)
            })

    return saved_signals, crypto_signals


def run_demo():
    """Ejecuta el demo completo del sistema."""
    print_header()
    init_db()

    console.print("\n[dim italic]── Modo DEMO: datos de muestra (Jun 2026) ──[/dim italic]")
    console.print("[dim]En tu máquina con conexión: usa python main.py para datos en tiempo real[/dim]\n")

    # Cargar datos
    stock_signals, crypto_signals = load_demo_data()

    # ── NOTICIAS ──────────────────────────────────────────────
    console.print(Rule("[bold]NOTICIAS & SENTIMIENTO[/bold]"))
    mood = get_market_mood(DEMO_NEWS)
    trending = get_trending_topics(DEMO_NEWS)
    print_news_mood(mood, trending, DEMO_NEWS)

    # ── MERCADO GLOBAL ────────────────────────────────────────
    console.print(Rule("[bold]MERCADOS GLOBALES[/bold]"))
    print_market_overview(DEMO_MARKET_OVERVIEW)

    # ── SEÑALES ACCIONES ──────────────────────────────────────
    console.print(Rule("[bold]ANÁLISIS TÉCNICO: ACCIONES & ETFs[/bold]"))
    print_signals(stock_signals, "SEÑALES: ACCIONES & ETFs")

    # ── CRYPTO ────────────────────────────────────────────────
    console.print(Rule("[bold]CRIPTOMONEDAS[/bold]"))
    print_crypto_overview(DEMO_CRYPTO_GLOBAL, DEMO_CRYPTO_COINS)
    print_signals(
        [s for s in crypto_signals if s["action"] in ("BUY", "WATCH")],
        "SEÑALES: CRIPTOMONEDAS"
    )

    # ── GITHUB TOOLS ──────────────────────────────────────────
    console.print(Rule("[bold]HERRAMIENTAS OPEN-SOURCE DESCUBIERTAS[/bold]"))
    print_github_tools(DEMO_GITHUB_TOOLS)

    # ── SÍNTESIS EJECUTIVA ────────────────────────────────────
    console.print(Rule("[bold]SÍNTESIS EJECUTIVA[/bold]"))

    synthesis = json.dumps({
        "executive_summary": (
            "El mercado muestra un momentum alcista moderado liderado por el sector tecnológico. "
            "NVDA y ASML presentan las señales técnicas más fuertes. Bitcoin consolida por encima "
            "de $100k con sentimiento positivo en criptos. La Fed mantiene tipos estables, "
            "reduciendo el riesgo sistémico a corto plazo."
        ),
        "market_diagnosis": (
            "Mercado en fase de expansión tardía. Tecnología liderando. "
            "EUR/USD fuerte sugiere flujos hacia Europa. Oro en máximos indica búsqueda de refugio parcial."
        ),
        "priority_actions": [
            {
                "symbol": "NVDA",
                "action": "BUY",
                "reasoning": "RSI 64 + MACD alcista + Golden Cross activo. Catalizador: resultados Q1 récord."
            },
            {
                "symbol": "ASML",
                "action": "BUY",
                "reasoning": "RSI 28.5 (sobrevendido) + precio bajo Bollinger inferior. Corrección excesiva."
            },
            {
                "symbol": "SOL",
                "action": "WATCH",
                "reasoning": "Momentum +4.8% 24h, +15.3% semana. Esperar confirmación de ruptura > $170."
            }
        ],
        "risk_level": "MEDIO - Mercados en zona de sobrecompra moderada. Riesgo de corrección del 5-8%.",
        "portfolio_advice": (
            "Diversifica con un 60% renta variable (40% USA, 20% Europa), "
            "20% cripto (70% BTC+ETH, 30% altcoins de calidad), "
            "15% inmobiliario o REITs, 5% liquidez para oportunidades."
        ),
        "learning_note": (
            "Sistema en aprendizaje activo. Con más señales evaluadas, "
            "el motor de aprendizaje calibrará automáticamente la confianza de cada agente."
        ),
        "disclaimer": (
            "Este análisis es orientativo y generado por IA. No constituye asesoramiento financiero "
            "oficial. Siempre investiga por tu cuenta y considera consultar un asesor certificado."
        )
    }, ensure_ascii=False)

    print_ai_synthesis(synthesis)

    # ── ESTADO DEL SISTEMA ────────────────────────────────────
    console.print(Rule("[bold]ESTADO DEL SISTEMA DE APRENDIZAJE[/bold]"))
    from config.settings import get_ai_provider
    provider = get_ai_provider()
    provider_labels = {
        "anthropic": "Claude (Anthropic) - Activo",
        "groq": "Groq/Llama 3.1 - GRATIS",
        "ollama": "Ollama (local) - GRATIS",
        "rules": "Modo Reglas (sin IA) - GRATIS",
    }
    console.print(Panel(
        f"[bold]Motor IA:[/bold] {provider_labels.get(provider, provider)}\n"
        f"[bold]Señales generadas:[/bold] {len(stock_signals) + len(crypto_signals)} hoy\n"
        f"[bold]Base de datos:[/bold] SQLite local (memory/investment.db)\n"
        f"[bold]Scheduler:[/bold] Disponible con python scheduler.py\n"
        f"[bold]Auto-aprendizaje:[/bold] Activo - evaluará señales en 7 días",
        title="SISTEMA",
        border_style="cyan"
    ))

    console.print(Panel(
        "[bold green]Sistema operativo y listo para producción[/bold green]\n\n"
        "Para usar con datos en tiempo real:\n"
        "  1. Copia .env.example → .env y añade tu API key\n"
        "  2. [bold]python main.py[/bold]  ← análisis completo\n"
        "  3. [bold]python scheduler.py[/bold]  ← modo autónomo 24/7\n"
        "  4. [bold]python main.py --add BTC 0.1 95000[/bold]  ← añadir posición\n"
        "  5. [bold]python main.py --portfolio[/bold]  ← ver portfolio",
        title="PRÓXIMOS PASOS",
        border_style="green"
    ))


if __name__ == "__main__":
    run_demo()
