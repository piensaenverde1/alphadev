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

    # ── BACKTESTING DEMO ──────────────────────────────────────
    console.print(Rule("[bold]BACKTESTING HISTÓRICO[/bold]"))
    import os, sys
    from tools.backtester import BacktestEngine
    from rich.table import Table
    from rich import box as rich_box
    engine = BacktestEngine()
    backtest_results = {}
    # Silenciar errores de red de yfinance en entorno sandbox
    _devnull = open(os.devnull, 'w')
    _stderr_backup = sys.stderr
    sys.stderr = _devnull
    for sym in ["NVDA", "ASML", "SPY"]:
        res = engine.run_all_strategies(sym)
        best = max(
            {k: v for k, v in res.items() if isinstance(v, dict) and v.get("sharpe_ratio", 0) > 0}.items(),
            key=lambda x: x[1].get("sharpe_ratio", 0),
            default=(None, {})
        )
        if best[0]:
            backtest_results[sym] = {"strategy": best[0], **best[1]}
    sys.stderr = _stderr_backup
    _devnull.close()

    if backtest_results:
        bt_table = Table(title="BACKTESTING: MEJORES ESTRATEGIAS (2 años)", box=rich_box.ROUNDED, border_style="cyan")
        bt_table.add_column("Activo")
        bt_table.add_column("Estrategia")
        bt_table.add_column("Retorno", justify="right")
        bt_table.add_column("Sharpe", justify="right")
        bt_table.add_column("Max DD", justify="right")
        bt_table.add_column("Win Rate", justify="center")
        for sym, d in backtest_results.items():
            ret = d.get("total_return_pct", 0)
            sh = d.get("sharpe_ratio", 0)
            rc = "green" if ret > 0 else "red"
            sc = "green" if sh > 1 else "yellow" if sh > 0 else "red"
            bt_table.add_row(
                sym, d.get("strategy", "?"),
                f"[{rc}]{ret:+.1f}%[/{rc}]",
                f"[{sc}]{sh:.2f}[/{sc}]",
                f"{d.get('max_drawdown_pct', 0):.1f}%",
                f"{d.get('win_rate', 0):.0f}%",
            )
        console.print(bt_table)

    # ── GESTIÓN DE RIESGO DEMO ────────────────────────────────
    console.print(Rule("[bold]GESTIÓN DE RIESGO & SIZING (Kelly Criterion)[/bold]"))
    from core.risk_manager import RiskManager
    rm = RiskManager(capital=10000.0)
    sizing_demo = [
        {"symbol": "NVDA", "action": "BUY", "asset_type": "stock",
         "current_price": 138.85, "confidence": 0.7, "stop": 131.0},
        {"symbol": "ASML", "action": "BUY", "asset_type": "stock",
         "current_price": 712.40, "confidence": 0.5, "stop": 676.0},
        {"symbol": "ETH",  "action": "BUY", "asset_type": "crypto",
         "current_price": 2692.0, "confidence": 0.67, "stop": 2290.0},
    ]
    risk_table = Table(title="SIZING ÓPTIMO (capital: 10,000 EUR)", box=rich_box.ROUNDED, border_style="yellow")
    risk_table.add_column("Activo")
    risk_table.add_column("Invertir", justify="right")
    risk_table.add_column("Cantidad", justify="right")
    risk_table.add_column("Stop-Loss", justify="right")
    risk_table.add_column("Take-Profit", justify="right")
    risk_table.add_column("Riesgo Cap.", justify="center")
    risk_table.add_column("Kelly", justify="center")
    for s in sizing_demo:
        sz = rm.calculate_position(s, s["current_price"])
        risk_table.add_row(
            s["symbol"],
            f"{sz['recommended_value']:,.2f} EUR",
            f"{sz['recommended_shares']:.4f}",
            f"[red]{sz['stop_loss_price']:,.2f}[/red]",
            f"[green]{sz['take_profit_price']:,.2f}[/green]",
            f"{sz['risk_pct_of_capital']:.2%}",
            f"{sz['kelly_fraction']:.1%}",
        )
    console.print(risk_table)

    # ── PAPER TRADING DEMO ────────────────────────────────────
    console.print(Rule("[bold]PAPER TRADING (Operaciones Simuladas)[/bold]"))
    from core.paper_trader import PaperTrader
    pt = PaperTrader(initial_cash=10000.0)
    for s in sizing_demo:
        sz = rm.calculate_position(s, s["current_price"])
        pt.execute_signal(s, s["current_price"], sz)
    summary_pt = pt.get_account_summary()
    console.print(Panel(
        f"[bold]Capital inicial:[/bold] {summary_pt['initial_cash']:,.2f} EUR\n"
        f"[bold]Cash restante:[/bold]  {summary_pt['cash']:,.2f} EUR\n"
        f"[bold]En posiciones:[/bold]  {summary_pt['positions_value']:,.2f} EUR\n"
        f"[bold]Valor total:[/bold]    {summary_pt['total_value']:,.2f} EUR\n"
        f"[bold]Operaciones:[/bold]    {summary_pt['total_trades']} ejecutadas",
        title="CUENTA PAPER TRADING",
        border_style="magenta"
    ))

    # ── OPCIONES DEMO ─────────────────────────────────────────
    console.print(Rule("[bold]ANÁLISIS DE OPCIONES (Black-Scholes)[/bold]"))
    from tools.options_analyzer import OptionsAnalyzer
    oa = OptionsAnalyzer()
    opt_call = oa.price_option(138.85, 145.0, 30, sigma=0.35, option_type='call')
    opt_put  = oa.price_option(138.85, 132.0, 30, sigma=0.35, option_type='put')
    hedges   = oa.suggest_hedges("NVDA", 10, 138.85, 'medium')
    console.print(Panel(
        f"[bold]NVDA @ 138.85 (volatilidad implícita: 35%)[/bold]\n\n"
        f"  CALL Strike 145  30d: Prima=[green]{opt_call['price']:.2f}[/green] "
        f"Delta={opt_call['delta']:.2f}  Theta={opt_call['theta_per_day']:.2f}/día\n"
        f"  PUT  Strike 132  30d: Prima=[red]{opt_put['price']:.2f}[/red]  "
        f"Delta={opt_put['delta']:.2f}  Theta={opt_put['theta_per_day']:.2f}/día\n\n"
        f"[bold]Estrategias de cobertura sugeridas:[/bold]\n" +
        "\n".join(
            f"  → [bold]{h.get('strategy','?')}[/bold]: Strike {h.get('strike',0):.2f} | "
            f"Coste: {h.get('estimated_cost',0):.2f} | Protección: {h.get('protection_pct',0) or 0:.1f}% | "
            f"{h.get('description','')}"
            for h in hedges
        ),
        title="OPCIONES FINANCIERAS",
        border_style="blue"
    ))

    # ── SENTIMIENTO AVANZADO ──────────────────────────────────
    console.print(Rule("[bold]ANÁLISIS DE SENTIMIENTO AVANZADO[/bold]"))
    from tools.sentiment_advanced import AdvancedSentiment
    sa = AdvancedSentiment()
    test_headlines = [
        "NVIDIA surges to record high after beating Q1 earnings by 40%",
        "Federal Reserve signals interest rate cuts in second half of 2026",
        "Bitcoin crashes below $90,000 amid regulatory fears and mass liquidations",
        "ASML stock falls 12% as semiconductor demand outlook worsens",
    ]
    for headline in test_headlines:
        result = sa.analyze(headline)
        sent_color = {"POSITIVE": "green", "NEGATIVE": "red", "NEUTRAL": "yellow"}.get(result["sentiment"], "white")
        entities = sa.extract_financial_entities(headline)
        console.print(
            f"  [{sent_color}]{result['sentiment']:8}[/{sent_color}] "
            f"score={result['score']:+.2f} conf={result['confidence']:.0%}  "
            f"│ {headline[:65]}"
        )
        if entities.get("companies") or entities.get("events"):
            console.print(
                f"  {'':10} Entidades: {', '.join(entities.get('companies', []) + entities.get('events', []))[:60]}"
            )

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
    total_signals = len(stock_signals) + len(crypto_signals)
    console.print(Panel(
        f"[bold]Motor IA:[/bold] {provider_labels.get(provider, provider)}\n"
        f"[bold]Agentes activos:[/bold] market, crypto, news, tech, backtest, risk, learning (7 total)\n"
        f"[bold]Señales generadas:[/bold] {total_signals} hoy\n"
        f"[bold]Base de datos:[/bold] SQLite local (memory/investment.db)\n"
        f"[bold]Paper trading:[/bold] {summary_pt['total_trades']} operaciones simuladas\n"
        f"[bold]Scheduler:[/bold] Disponible con python scheduler.py\n"
        f"[bold]Auto-aprendizaje:[/bold] Activo - evaluará señales en 7 días",
        title="SISTEMA",
        border_style="cyan"
    ))

    console.print(Panel(
        "[bold green]Sistema v2.0 operativo - 10 módulos activos[/bold green]\n\n"
        "[bold]Comandos disponibles:[/bold]\n"
        "  [bold]python main.py[/bold]                    ← análisis completo\n"
        "  [bold]python main.py --backtest NVDA ASML[/bold] ← backtesting histórico\n"
        "  [bold]python main.py --optimize AAPL[/bold]    ← optimizar parámetros RSI/MACD\n"
        "  [bold]python main.py --risk --capital 25000[/bold] ← gestión de riesgo\n"
        "  [bold]python main.py --paper[/bold]            ← ver paper trading\n"
        "  [bold]python main.py --options NVDA 138.85[/bold] ← análisis de opciones\n"
        "  [bold]python main.py --add BTC 0.1 95000[/bold]   ← añadir posición\n"
        "  [bold]python scheduler.py[/bold]               ← modo autónomo 24/7",
        title="COMANDOS",
        border_style="green"
    ))


if __name__ == "__main__":
    run_demo()
