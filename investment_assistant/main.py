#!/usr/bin/env python3
"""
ASISTENTE PERSONAL DE INVERSIÓN
================================
Sistema multi-agente de análisis financiero con auto-aprendizaje.

Uso:
  python main.py                    # Análisis completo del día
  python main.py --quick            # Análisis rápido (sin GitHub/learning)
  python main.py --portfolio        # Solo ver portfolio
  python main.py --add AAPL 10 150  # Añadir 10 acciones de AAPL a 150€
  python main.py --remove AAPL      # Quitar AAPL del portfolio
  python main.py --learn            # Ejecutar solo el motor de aprendizaje
  python main.py --news             # Solo noticias
  python main.py --crypto           # Solo análisis crypto
  python main.py --status           # Estado del sistema y métricas
"""
import sys
import os
import argparse
from pathlib import Path

# Añadir directorio al path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel

console = Console()


def setup():
    """Inicializa la base de datos."""
    from memory.database import init_db
    init_db()


def cmd_full_analysis(quick: bool = False):
    """Análisis completo de todos los agentes."""
    from agents.coordinator import InvestmentCoordinator
    from core.reporter import (
        print_header, print_market_overview, print_signals,
        print_crypto_overview, print_news_mood, print_github_tools,
        print_ai_synthesis, print_learning_stats
    )
    from memory.database import get_lessons, get_agent_accuracy

    print_header()

    coordinator = InvestmentCoordinator()

    if quick:
        results = coordinator.run_quick_scan()
    else:
        results = coordinator.run_full_analysis(
            include_tech=not quick,
            include_learning=not quick
        )

    r = results["results"]

    # --- Mood de noticias ---
    if r.get("news"):
        news_r = r["news"]
        print_news_mood(
            news_r.get("market_mood", {}),
            news_r.get("trending_topics", {}),
            news_r.get("high_impact_news", [])
        )

    # --- Mercado global ---
    if r.get("market"):
        market_r = r["market"]
        print_market_overview(market_r.get("market_overview", {}))
        print_signals(
            market_r.get("actionable_signals", []),
            "SEÑALES: ACCIONES & ETFs"
        )

    # --- Crypto ---
    if r.get("crypto"):
        crypto_r = r["crypto"]
        print_crypto_overview(
            crypto_r.get("global_stats", {}),
            crypto_r.get("top_coins", [])
        )
        print_signals(
            crypto_r.get("actionable_signals", []),
            "SEÑALES: CRIPTOMONEDAS"
        )

    # --- GitHub Tools ---
    if r.get("tech"):
        print_github_tools(r["tech"].get("top_repos", []))

    # --- Síntesis IA ---
    if results.get("synthesis"):
        print_ai_synthesis(results["synthesis"])

    # --- Aprendizaje ---
    if r.get("learning"):
        accuracy = r["learning"].get("agent_accuracy", {})
        lessons = get_lessons(limit=5)
        if accuracy or lessons:
            print_learning_stats(accuracy, lessons)


def cmd_portfolio():
    """Muestra el portfolio actual."""
    from core.portfolio import Portfolio
    from core.reporter import print_header, print_portfolio

    print_header()
    pf = Portfolio()
    summary = pf.get_summary()
    print_portfolio(summary)


def cmd_add_position(symbol: str, quantity: float, price: float, asset_type: str = None):
    """Añade una posición al portfolio."""
    from core.portfolio import Portfolio
    from tools.market_data import get_stock_info

    # Detectar tipo automáticamente si no se especifica
    if not asset_type:
        crypto_symbols = {"BTC", "ETH", "SOL", "ADA", "DOT", "LINK", "AVAX", "UNI"}
        if symbol.upper() in crypto_symbols:
            asset_type = "crypto"
        elif symbol.upper().endswith(".F") or "ETF" in symbol.upper():
            asset_type = "etf"
        else:
            asset_type = "stock"

    # Obtener nombre del activo
    name = symbol
    if asset_type in ("stock", "etf"):
        info = get_stock_info(symbol)
        name = info.get("name", symbol)

    pf = Portfolio()
    msg = pf.add_position(symbol.upper(), name, asset_type, quantity, price)
    console.print(f"[green]✓ {msg}[/green]")


def cmd_remove_position(symbol: str):
    """Elimina una posición del portfolio."""
    from core.portfolio import Portfolio
    pf = Portfolio()
    pf.remove_position(symbol.upper())
    console.print(f"[yellow]✓ {symbol} eliminado del portfolio[/yellow]")


def cmd_learn():
    """Ejecuta solo el motor de aprendizaje."""
    from agents.learning_engine import LearningEngine
    from core.reporter import print_learning_stats
    from memory.database import get_lessons

    engine = LearningEngine()
    results = engine.run()

    print_learning_stats(results.get("agent_accuracy", {}), get_lessons(limit=10))

    report = results.get("learning_report", "")
    if report:
        console.print(Panel(report, title="INFORME DE APRENDIZAJE", border_style="cyan"))


def cmd_news():
    """Solo análisis de noticias."""
    from agents.news_agent import NewsAgent
    from core.reporter import print_news_mood

    agent = NewsAgent()
    results = agent.run()

    print_news_mood(
        results.get("market_mood", {}),
        results.get("trending_topics", {}),
        results.get("high_impact_news", [])
    )

    if results.get("ai_analysis"):
        try:
            import json
            data = json.loads(results["ai_analysis"])
            summary = data.get("summary", results["ai_analysis"][:500])
            console.print(Panel(summary, title="ANÁLISIS IA", border_style="white"))
        except Exception:
            console.print(Panel(results["ai_analysis"][:500], title="ANÁLISIS", border_style="white"))


def cmd_crypto():
    """Solo análisis de criptomonedas."""
    from agents.crypto_agent import CryptoAgent
    from core.reporter import print_crypto_overview, print_signals

    agent = CryptoAgent()
    results = agent.run()

    print_crypto_overview(results.get("global_stats", {}), results.get("top_coins", []))
    print_signals(results.get("actionable_signals", []), "SEÑALES CRIPTO")


def cmd_status():
    """Estado del sistema y estadísticas."""
    from memory.database import get_agent_accuracy, get_lessons, get_top_github_tools
    from core.reporter import print_learning_stats
    from config.settings import get_ai_provider

    provider = get_ai_provider()
    provider_info = {
        "anthropic": "[green]Claude (Anthropic)[/green]",
        "groq": "[green]Groq (Llama 3.1 - GRATIS)[/green]",
        "ollama": "[green]Ollama (Local - GRATIS)[/green]",
        "rules": "[yellow]Modo Reglas (sin IA)[/yellow]",
    }

    console.print(Panel(
        f"[bold]Proveedor IA:[/bold] {provider_info.get(provider, provider)}\n"
        f"[bold]Modo:[/bold] {'Análisis con IA' if provider != 'rules' else 'Solo análisis técnico'}\n"
        f"[bold]Base de datos:[/bold] SQLite (local)",
        title="ESTADO DEL SISTEMA",
        border_style="cyan"
    ))

    accuracy = get_agent_accuracy()
    lessons = get_lessons(limit=10)
    tools = get_top_github_tools(limit=5)

    if accuracy:
        print_learning_stats(accuracy, lessons)
    else:
        console.print("[dim]Sin señales evaluadas aún. Ejecuta análisis por unos días para ver métricas.[/dim]")

    if tools:
        from core.reporter import print_github_tools
        print_github_tools(tools)

    console.print(f"\n[dim]Lecciones acumuladas: {len(lessons)}[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Asistente Personal de Inversión",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--quick", action="store_true", help="Análisis rápido")
    parser.add_argument("--portfolio", action="store_true", help="Ver portfolio")
    parser.add_argument("--add", nargs=3, metavar=("SYMBOL", "QUANTITY", "PRICE"),
                        help="Añadir posición: --add AAPL 10 150.50")
    parser.add_argument("--type", default=None, help="Tipo de activo: stock/crypto/etf")
    parser.add_argument("--remove", metavar="SYMBOL", help="Eliminar posición")
    parser.add_argument("--learn", action="store_true", help="Ejecutar aprendizaje")
    parser.add_argument("--news", action="store_true", help="Solo noticias")
    parser.add_argument("--crypto", action="store_true", help="Solo crypto")
    parser.add_argument("--status", action="store_true", help="Estado del sistema")

    args = parser.parse_args()

    # Inicializar sistema
    setup()

    try:
        if args.portfolio:
            cmd_portfolio()
        elif args.add:
            symbol, qty, price = args.add
            cmd_add_position(symbol, float(qty), float(price), args.type)
        elif args.remove:
            cmd_remove_position(args.remove)
        elif args.learn:
            cmd_learn()
        elif args.news:
            cmd_news()
        elif args.crypto:
            cmd_crypto()
        elif args.status:
            cmd_status()
        else:
            cmd_full_analysis(quick=args.quick)

    except KeyboardInterrupt:
        console.print("\n[yellow]Análisis interrumpido por el usuario[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
