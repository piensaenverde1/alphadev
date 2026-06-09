"""Generador de informes con Rich (terminal bonito)."""
import json
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def print_header():
    console.print(Panel(
        "[bold cyan]ASISTENTE PERSONAL DE INVERSIÓN[/bold cyan]\n"
        "[dim]Multi-Agente • Auto-Aprendizaje • 100% Open Source[/dim]",
        border_style="cyan",
        padding=(1, 4)
    ))


def print_market_overview(overview: Dict):
    if not overview:
        return
    table = Table(title="MERCADOS GLOBALES", box=box.ROUNDED, border_style="blue")
    table.add_column("Índice", style="bold white")
    table.add_column("Precio", justify="right")
    table.add_column("Cambio", justify="right")

    for name, data in overview.items():
        pct = data.get("change_pct", 0)
        price = data.get("price", 0)
        trend = data.get("trend", "-")
        color = "green" if pct > 0 else "red" if pct < 0 else "white"
        table.add_row(
            name,
            f"{price:,.2f}",
            f"[{color}]{trend} {pct:+.2f}%[/{color}]"
        )
    console.print(table)


def print_signals(signals: List[Dict], title: str = "SEÑALES DE INVERSIÓN"):
    if not signals:
        console.print(f"[dim]Sin señales accionables en {title}[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED, border_style="yellow")
    table.add_column("Símbolo", style="bold")
    table.add_column("Acción", justify="center")
    table.add_column("Precio", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Stop", justify="right")
    table.add_column("Confianza", justify="center")
    table.add_column("Razón", max_width=40)

    for sig in signals:
        action = sig.get("action", "?")
        action_colors = {"BUY": "green", "SELL": "red", "WATCH": "yellow", "HOLD": "white"}
        color = action_colors.get(action, "white")

        price = sig.get("current_price") or sig.get("price", 0)
        target = sig.get("target") or sig.get("price_target", 0)
        stop = sig.get("stop") or sig.get("stop_loss", 0)
        confidence = sig.get("confidence", 0)
        reasons = sig.get("reasons") or sig.get("signals", [])
        reason_text = reasons[0] if reasons else sig.get("reasoning", "")[:40]

        table.add_row(
            sig.get("symbol", "?"),
            f"[{color}]{action}[/{color}]",
            f"{price:,.4f}" if price < 1 else f"{price:,.2f}",
            f"[green]{target:,.2f}[/green]" if target else "-",
            f"[red]{stop:,.2f}[/red]" if stop else "-",
            f"{'█' * int(confidence * 5)}{'░' * (5 - int(confidence * 5))} {confidence:.0%}",
            f"[dim]{reason_text[:40]}[/dim]",
        )

    console.print(table)


def print_crypto_overview(global_stats: Dict, top_coins: List[Dict]):
    if global_stats:
        mcap = global_stats.get("total_market_cap_eur", 0)
        btc_dom = global_stats.get("btc_dominance", 0)
        change = global_stats.get("market_cap_change_24h", 0)
        color = "green" if change > 0 else "red"

        console.print(Panel(
            f"[bold]Market Cap Total:[/bold] {mcap/1e12:.2f}T EUR  |  "
            f"[bold]BTC Dominancia:[/bold] {btc_dom}%  |  "
            f"[bold]Cambio 24h:[/bold] [{color}]{change:+.2f}%[/{color}]",
            title="MERCADO CRIPTO GLOBAL",
            border_style="magenta"
        ))

    if top_coins:
        table = Table(title="TOP CRIPTOMONEDAS", box=box.SIMPLE, border_style="magenta")
        table.add_column("#", style="dim")
        table.add_column("Nombre")
        table.add_column("Precio EUR", justify="right")
        table.add_column("24h", justify="right")
        table.add_column("7d", justify="right")

        for i, coin in enumerate(top_coins[:10], 1):
            c24 = coin.get("change_24h", 0) or 0
            c7d = coin.get("change_7d", 0) or 0
            color24 = "green" if c24 > 0 else "red"
            color7d = "green" if c7d > 0 else "red"
            table.add_row(
                str(i),
                f"[bold]{coin.get('name', '?')}[/bold] [dim]{coin.get('symbol', '')}[/dim]",
                f"{coin.get('price', 0):,.2f}",
                f"[{color24}]{c24:+.1f}%[/{color24}]",
                f"[{color7d}]{c7d:+.1f}%[/{color7d}]",
            )
        console.print(table)


def print_news_mood(mood: Dict, trending: Dict, top_news: List[Dict]):
    mood_name = mood.get("mood", "NEUTRAL")
    mood_colors = {"BULLISH": "green", "BEARISH": "red", "NEUTRAL": "yellow"}
    mood_emojis = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}
    color = mood_colors.get(mood_name, "white")
    emoji = mood_emojis.get(mood_name, "")

    console.print(Panel(
        f"[bold {color}]{emoji} {mood_name}[/bold {color}]  "
        f"Score: {mood.get('score', 0):+.2f}  |  "
        f"{mood.get('description', '')}",
        title="MOOD DEL MERCADO",
        border_style=color
    ))

    if top_news:
        console.print("\n[bold]NOTICIAS RELEVANTES:[/bold]")
        for news in top_news[:5]:
            sent = news.get("sentiment", "NEUTRAL")
            sent_color = {"POSITIVE": "green", "NEGATIVE": "red", "NEUTRAL": "dim"}.get(sent, "white")
            console.print(f"  [{sent_color}]●[/{sent_color}] {news['title'][:90]}")
            console.print(f"     [dim]{news.get('source', '')} | {news.get('summary', '')[:80]}[/dim]")


def print_portfolio(summary: Dict):
    if not summary or not summary.get("positions"):
        console.print("[dim]Portfolio vacío. Usa 'add' para añadir posiciones.[/dim]")
        return

    pnl = summary.get("total_pnl", 0)
    pnl_pct = summary.get("total_pnl_pct", 0)
    pnl_color = "green" if pnl >= 0 else "red"
    pnl_sign = "+" if pnl >= 0 else ""

    console.print(Panel(
        f"[bold]Valor total:[/bold] {summary.get('total_current_value', 0):,.2f} EUR  |  "
        f"[bold]Invertido:[/bold] {summary.get('total_invested', 0):,.2f} EUR  |  "
        f"[bold]P&L:[/bold] [{pnl_color}]{pnl_sign}{pnl:,.2f} EUR ({pnl_sign}{pnl_pct:.2f}%)[/{pnl_color}]",
        title="MI PORTFOLIO",
        border_style="cyan"
    ))

    table = Table(box=box.SIMPLE)
    table.add_column("Símbolo", style="bold")
    table.add_column("Tipo", style="dim")
    table.add_column("Cantidad", justify="right")
    table.add_column("Compra", justify="right")
    table.add_column("Actual", justify="right")
    table.add_column("Valor", justify="right")
    table.add_column("P&L", justify="right")

    for pos in summary.get("positions", []):
        p_color = "green" if pos.pnl >= 0 else "red"
        sign = "+" if pos.pnl >= 0 else ""
        table.add_row(
            pos.symbol,
            pos.asset_type,
            f"{pos.quantity:,.4f}",
            f"{pos.avg_buy_price:,.4f}",
            f"{pos.current_price:,.4f}",
            f"{pos.current_value:,.2f}",
            f"[{p_color}]{sign}{pos.pnl:,.2f} ({sign}{pos.pnl_pct:.1f}%)[/{p_color}]",
        )

    console.print(table)


def print_github_tools(tools: List[Dict]):
    if not tools:
        return
    console.print("\n[bold cyan]HERRAMIENTAS GITHUB DESCUBIERTAS:[/bold cyan]")
    for tool in tools[:5]:
        stars = tool.get("stargazers_count") or tool.get("stars", 0)
        console.print(
            f"  [bold]{tool.get('full_name', tool.get('repo_name', '?'))}[/bold] "
            f"[yellow]⭐ {stars}[/yellow]"
        )
        if tool.get("description"):
            console.print(f"  [dim]{tool['description'][:100]}[/dim]")
        if tool.get("recommendation"):
            console.print(f"  [green]→ {tool['recommendation'][:100]}[/green]")
        console.print()


def print_ai_synthesis(synthesis: str):
    """Imprime la síntesis generada por IA."""
    if not synthesis:
        return

    try:
        data = json.loads(synthesis)
        console.print(Panel(
            data.get("executive_summary", synthesis[:500]),
            title="[bold]RESUMEN EJECUTIVO[/bold]",
            border_style="bright_white"
        ))

        if data.get("priority_actions"):
            console.print("\n[bold yellow]ACCIONES PRIORITARIAS:[/bold yellow]")
            for action in data.get("priority_actions", []):
                if isinstance(action, dict):
                    sym = action.get("symbol", "")
                    act = action.get("action", "")
                    reason = action.get("reasoning", action.get("reason", ""))
                    act_color = "green" if act == "BUY" else "red" if act == "SELL" else "yellow"
                    console.print(
                        f"  [{act_color}]▶ {act}[/{act_color}] {sym} - {reason[:80]}"
                    )
                else:
                    console.print(f"  ▶ {str(action)[:100]}")

        risk = data.get("risk_level", "")
        if risk:
            risk_colors = {"BAJO": "green", "MEDIO": "yellow", "ALTO": "red"}
            color = risk_colors.get(risk.upper().split()[0] if risk else "MEDIO", "white")
            console.print(f"\n[bold]RIESGO:[/bold] [{color}]{risk}[/{color}]")

        if data.get("disclaimer"):
            console.print(f"\n[dim italic]⚠️  {data['disclaimer']}[/dim italic]")

    except (json.JSONDecodeError, Exception):
        # Si no es JSON válido, mostrar como texto
        console.print(Panel(synthesis[:1000], title="ANÁLISIS", border_style="white"))


def print_learning_stats(accuracy: Dict, lessons: List[Dict]):
    if not accuracy:
        return

    table = Table(title="RENDIMIENTO DEL SISTEMA", box=box.SIMPLE, border_style="cyan")
    table.add_column("Agente")
    table.add_column("Acierto", justify="center")
    table.add_column("Señales", justify="right")
    table.add_column("Retorno Avg", justify="right")

    for agent, stats in accuracy.items():
        win_rate = stats.get("win_rate", 0)
        color = "green" if win_rate >= 60 else "yellow" if win_rate >= 45 else "red"
        avg_ret = stats.get("avg_return", 0)
        ret_color = "green" if avg_ret > 0 else "red"
        table.add_row(
            agent,
            f"[{color}]{win_rate}%[/{color}]",
            str(stats.get("total", 0)),
            f"[{ret_color}]{avg_ret:+.1f}%[/{ret_color}]",
        )

    console.print(table)

    if lessons:
        console.print(f"\n[dim]Lecciones acumuladas: {len(lessons)} | "
                      f"Última lección: {lessons[0].get('lesson', '')[:60]}[/dim]")
