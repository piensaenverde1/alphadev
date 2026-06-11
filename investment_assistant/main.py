#!/usr/bin/env python3
"""
ASISTENTE PERSONAL DE INVERSIÓN
================================
Sistema multi-agente de análisis financiero con auto-aprendizaje.

Uso:
  python main.py                        # Análisis completo del día
  python main.py --quick                # Análisis rápido (sin GitHub/learning)
  python main.py --portfolio            # Solo ver portfolio
  python main.py --add AAPL 10 150      # Añadir 10 acciones de AAPL a 150€
  python main.py --remove AAPL          # Quitar AAPL del portfolio
  python main.py --learn                # Ejecutar solo el motor de aprendizaje
  python main.py --news                 # Solo noticias
  python main.py --crypto               # Solo análisis crypto
  python main.py --status               # Estado del sistema y métricas
  python main.py --backtest AAPL NVDA   # Backtesting histórico de activos
  python main.py --optimize AAPL        # Optimizar parámetros de estrategia
  python main.py --risk                 # Análisis de riesgo del portfolio
  python main.py --paper                # Ver estado del paper trading
  python main.py --options AAPL 213.50  # Análisis de opciones para una acción
  python main.py --capital 25000        # Definir capital para sizing (default 10000)
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
    from memory.database import get_lessons

    print_header()

    coordinator = InvestmentCoordinator()

    if quick:
        results = coordinator.run_quick_scan()
        # run_quick_scan devuelve {"results": analysis_result, "synthesis": ...}
        r = results.get("results", {}).get("agent_results", {})
    else:
        results = coordinator.run_full_analysis(
            include_tech=not quick,
            include_learning=not quick,
        )
        # run_full_analysis devuelve {"analysis": ..., "execution": ..., "system": ..., "synthesis": ...}
        # Construir dict plano con todos los resultados de los agentes
        r = {}
        r.update(results.get("analysis", {}).get("agent_results", {}))
        r.update(results.get("execution", {}).get("agent_results", {}))
        r.update(results.get("system", {}).get("agent_results", {}))

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


def cmd_backtest(symbols: list):
    """Backtesting histórico con las 3 estrategias."""
    from agents.backtest_agent import BacktestAgent
    from rich.table import Table
    from rich import box

    agent = BacktestAgent()
    console.print(f"[cyan]Ejecutando backtesting para: {', '.join(symbols)}[/cyan]")
    results = agent.run(symbols=symbols)

    best = results.get("best_strategies", {})
    if not best:
        console.print("[yellow]Sin resultados de backtest. Puede que los datos históricos no estén disponibles.[/yellow]")
        return

    table = Table(title="RESULTADOS DE BACKTESTING", box=box.ROUNDED, border_style="cyan")
    table.add_column("Activo")
    table.add_column("Estrategia")
    table.add_column("Retorno", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Win Rate", justify="center")

    for sym, data in best.items():
        ret = data.get("return", 0)
        ret_color = "green" if ret > 0 else "red"
        sharpe = data.get("sharpe", 0)
        sharpe_color = "green" if sharpe > 1 else "yellow" if sharpe > 0 else "red"
        table.add_row(
            sym,
            data.get("strategy", "?"),
            f"[{ret_color}]{ret:+.1f}%[/{ret_color}]",
            f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]",
            f"{data.get('drawdown', 0):.1f}%",
            f"{data.get('win_rate', 0):.0f}%",
        )
    console.print(table)

    if results.get("ai_analysis"):
        try:
            import json
            data = json.loads(results["ai_analysis"])
            console.print(Panel(
                data.get("overall_assessment", results["ai_analysis"][:400]),
                title="ANÁLISIS IA DEL BACKTEST", border_style="cyan"
            ))
        except Exception:
            pass


def cmd_optimize(symbol: str):
    """Optimiza parámetros de estrategia para un activo."""
    from tools.optimizer import ParameterOptimizer
    from rich.table import Table
    from rich import box

    console.print(f"[cyan]Optimizando parámetros para {symbol}...[/cyan]")
    opt = ParameterOptimizer()
    params = opt.get_optimal_params(symbol)

    if "error" in params:
        console.print(f"[yellow]{params['error']}[/yellow]")
        return

    rsi = params.get("rsi_params", {})
    macd = params.get("macd_params", {})

    console.print(Panel(
        f"[bold]RSI ÓPTIMO para {symbol}:[/bold]\n"
        f"  Período: {rsi.get('period', 14)} | Sobrevendido: {rsi.get('oversold', 30)} | Sobrecomprado: {rsi.get('overbought', 70)}\n"
        f"  Sharpe con estos params: {rsi.get('sharpe', 0):.2f} | Retorno: {rsi.get('total_return_pct', 0):+.1f}%\n\n"
        f"[bold]MACD ÓPTIMO para {symbol}:[/bold]\n"
        f"  Fast: {macd.get('fast', 12)} | Slow: {macd.get('slow', 26)} | Signal: {macd.get('signal', 9)}\n"
        f"  Sharpe con estos params: {macd.get('sharpe', 0):.2f} | Retorno: {macd.get('total_return_pct', 0):+.1f}%",
        title=f"PARÁMETROS OPTIMIZADOS: {symbol}",
        border_style="yellow"
    ))


def cmd_risk(capital: float = 10000.0):
    """Análisis de riesgo del portfolio actual."""
    from agents.risk_agent import RiskAgent
    from memory.database import get_pending_signals

    agent = RiskAgent()
    pending = get_pending_signals(days_old=1)
    results = agent.run(signals=pending[:5], capital=capital)

    risk = results.get("portfolio_risk", {})
    if risk:
        hhi = risk.get("concentration_risk", 0)
        div_score = risk.get("diversification_score", 0)
        hhi_color = "red" if hhi > 0.6 else "yellow" if hhi > 0.3 else "green"
        div_color = "green" if div_score >= 7 else "yellow" if div_score >= 4 else "red"

        console.print(Panel(
            f"[bold]Concentración (HHI):[/bold] [{hhi_color}]{hhi:.2f}[/{hhi_color}] "
            f"({'Alta' if hhi > 0.6 else 'Media' if hhi > 0.3 else 'Baja'})\n"
            f"[bold]Diversificación:[/bold] [{div_color}]{div_score:.1f}/10[/{div_color}]\n"
            f"[bold]Recomendaciones:[/bold]\n" +
            "\n".join(f"  → {r}" for r in risk.get("recommendations", [])[:3]),
            title="RIESGO DEL PORTFOLIO",
            border_style="yellow"
        ))

    if results.get("ai_analysis"):
        try:
            import json
            data = json.loads(results["ai_analysis"])
            console.print(Panel(
                data.get("risk_summary", "") + "\n\n" +
                "\n".join(f"  {a}" for a in data.get("immediate_actions", [])),
                title="EVALUACIÓN DE RIESGO IA", border_style="red"
            ))
        except Exception:
            pass


def cmd_paper():
    """Ver estado del paper trading."""
    from core.paper_trader import PaperTrader
    from rich.table import Table
    from rich import box

    pt = PaperTrader()
    summary = pt.get_account_summary()
    history = pt.get_trade_history(limit=10)

    pnl = summary.get("total_pnl", 0)
    pnl_color = "green" if pnl >= 0 else "red"
    sign = "+" if pnl >= 0 else ""

    console.print(Panel(
        f"[bold]Capital inicial:[/bold] {summary.get('initial_cash', 10000):,.2f} EUR\n"
        f"[bold]Valor actual:[/bold] {summary.get('total_value', 0):,.2f} EUR\n"
        f"[bold]P&L total:[/bold] [{pnl_color}]{sign}{pnl:,.2f} EUR ({sign}{summary.get('total_pnl_pct', 0):.2f}%)[/{pnl_color}]\n"
        f"[bold]Operaciones:[/bold] {summary.get('total_trades', 0)} total | "
        f"[green]{summary.get('win_trades', 0)}W[/green] / [red]{summary.get('loss_trades', 0)}L[/red] | "
        f"Win rate: {summary.get('win_rate', 0):.0f}%",
        title="PAPER TRADING - CUENTA SIMULADA",
        border_style="magenta"
    ))

    if history:
        table = Table(title="HISTORIAL DE OPERACIONES", box=box.SIMPLE)
        table.add_column("Fecha")
        table.add_column("Símbolo")
        table.add_column("Acción")
        table.add_column("Qty", justify="right")
        table.add_column("Precio", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("P&L", justify="right")

        for trade in history:
            action = trade.get("action", "?")
            action_color = "green" if action == "BUY" else "red"
            pnl_t = trade.get("pnl", 0) or 0
            pnl_color_t = "green" if pnl_t >= 0 else "red"
            table.add_row(
                str(trade.get("executed_at", ""))[:10],
                trade.get("symbol", "?"),
                f"[{action_color}]{action}[/{action_color}]",
                f"{trade.get('quantity', 0):.4f}",
                f"{trade.get('price', 0):,.4f}",
                f"{trade.get('total_value', 0):,.2f}",
                f"[{pnl_color_t}]{'+' if pnl_t >= 0 else ''}{pnl_t:.2f}[/{pnl_color_t}]" if pnl_t else "-",
            )
        console.print(table)


def cmd_options(symbol: str, price: float):
    """Análisis de opciones para una acción."""
    from tools.options_analyzer import OptionsAnalyzer
    from rich.table import Table
    from rich import box

    console.print(f"[cyan]Calculando opciones para {symbol} @ {price}...[/cyan]")
    analyzer = OptionsAnalyzer()

    chain = analyzer.options_chain_summary(symbol, price)
    hedges = analyzer.suggest_hedges(symbol, 100, price, 'medium')

    if chain.get("calls"):
        table = Table(title=f"CADENA DE OPCIONES: {symbol}", box=box.SIMPLE)
        table.add_column("Tipo")
        table.add_column("Strike", justify="right")
        table.add_column("Vencimiento")
        table.add_column("Prima", justify="right")
        table.add_column("Delta", justify="right")
        table.add_column("IV", justify="right")

        for opt in chain.get("calls", [])[:5]:
            table.add_row(
                "[green]CALL[/green]",
                f"{opt.get('strike', 0):.2f}",
                f"{opt.get('expiry_days', 0)}d",
                f"{opt.get('price', 0):.2f}",
                f"{opt.get('delta', 0):.2f}",
                f"{opt.get('implied_vol', 0):.1%}",
            )
        for opt in chain.get("puts", [])[:5]:
            table.add_row(
                "[red]PUT[/red]",
                f"{opt.get('strike', 0):.2f}",
                f"{opt.get('expiry_days', 0)}d",
                f"{opt.get('price', 0):.2f}",
                f"{opt.get('delta', 0):.2f}",
                f"{opt.get('implied_vol', 0):.1%}",
            )
        console.print(table)

    if hedges:
        console.print("\n[bold yellow]ESTRATEGIAS DE COBERTURA SUGERIDAS:[/bold yellow]")
        for hedge in hedges:
            console.print(
                f"  [bold]{hedge.get('strategy', '?')}[/bold]: "
                f"Strike {hedge.get('strike', 0):.2f} | "
                f"Coste: {hedge.get('estimated_cost', 0):.2f} | "
                f"Protección: {hedge.get('protection_pct', 0):.1f}% | "
                f"Ganancia máx: {hedge.get('max_gain_pct', 0):.1f}%"
            )


def cmd_status():
    """Estado del sistema y estadísticas."""
    from memory.database import get_agent_accuracy, get_lessons, get_top_github_tools
    from core.reporter import print_learning_stats
    from core.paper_trader import PaperTrader
    from config.settings import get_ai_provider

    provider = get_ai_provider()
    provider_info = {
        "anthropic": "[green]Claude (Anthropic)[/green]",
        "groq": "[green]Groq (Llama 3.1 - GRATIS)[/green]",
        "ollama": "[green]Ollama (Local - GRATIS)[/green]",
        "rules": "[yellow]Modo Reglas (sin IA)[/yellow]",
    }

    pt = PaperTrader()
    pt_summary = pt.get_account_summary()

    console.print(Panel(
        f"[bold]Proveedor IA:[/bold] {provider_info.get(provider, provider)}\n"
        f"[bold]Base de datos:[/bold] SQLite (local)\n"
        f"[bold]Paper Trading:[/bold] {pt_summary.get('total_value', 0):,.2f} EUR "
        f"(P&L: {pt_summary.get('total_pnl', 0):+.2f} EUR)\n"
        f"[bold]Agentes activos:[/bold] market, crypto, news, tech, backtest, risk, learning (7 total)",
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
    parser.add_argument("--backtest", nargs="+", metavar="SYMBOL", help="Backtesting: --backtest AAPL NVDA")
    parser.add_argument("--optimize", metavar="SYMBOL", help="Optimizar parámetros")
    parser.add_argument("--risk", action="store_true", help="Análisis de riesgo")
    parser.add_argument("--paper", action="store_true", help="Ver paper trading")
    parser.add_argument("--options", nargs=2, metavar=("SYMBOL", "PRICE"), help="Opciones: --options AAPL 213.50")
    parser.add_argument("--capital", type=float, default=10000.0, help="Capital para sizing (default: 10000)")

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
        elif args.backtest:
            cmd_backtest(args.backtest)
        elif args.optimize:
            cmd_optimize(args.optimize)
        elif args.risk:
            cmd_risk(args.capital)
        elif args.paper:
            cmd_paper()
        elif args.options:
            cmd_options(args.options[0], float(args.options[1]))
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
