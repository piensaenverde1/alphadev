#!/usr/bin/env python3
"""
Scheduler automático del Asistente de Inversión.
Ejecuta análisis periódicos de forma autónoma.

Uso:
  python scheduler.py        # Inicia el planificador continuo
  python scheduler.py --once # Ejecuta una vez ahora y sale
"""
import sys
import time
import schedule
import threading
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from memory.database import init_db, save_report

console = Console()

# ---- Tareas programadas ----

def run_daily_analysis():
    """Análisis diario completo (sin GitHub para no gastar rate limit)."""
    from agents.coordinator import InvestmentCoordinator
    console.print(f"\n[cyan][SCHEDULER] Iniciando análisis diario - {datetime.now().strftime('%H:%M')}[/cyan]")
    try:
        coordinator = InvestmentCoordinator()
        results = coordinator.run_full_analysis(include_tech=False, include_learning=True)
        synthesis = results.get("synthesis", "")
        save_report("daily_auto", synthesis, {"trigger": "scheduler"})
        console.print("[green][SCHEDULER] Análisis diario completado[/green]")
    except Exception as e:
        console.print(f"[red][SCHEDULER] Error en análisis diario: {e}[/red]")


def run_weekly_analysis():
    """Análisis semanal completo (incluye GitHub y tech scout)."""
    from agents.coordinator import InvestmentCoordinator
    console.print(f"\n[magenta][SCHEDULER] Iniciando análisis SEMANAL - {datetime.now().strftime('%H:%M')}[/magenta]")
    try:
        coordinator = InvestmentCoordinator()
        results = coordinator.run_full_analysis(include_tech=True, include_learning=True)
        synthesis = results.get("synthesis", "")
        save_report("weekly_auto", synthesis, {"trigger": "scheduler_weekly"})
        console.print("[green][SCHEDULER] Análisis semanal completado[/green]")
    except Exception as e:
        console.print(f"[red][SCHEDULER] Error en análisis semanal: {e}[/red]")


def run_learning_cycle():
    """Ciclo de aprendizaje: evalúa señales pasadas."""
    from agents.learning_engine import LearningEngine
    console.print(f"[dim][SCHEDULER] Ciclo de aprendizaje - {datetime.now().strftime('%H:%M')}[/dim]")
    try:
        engine = LearningEngine()
        engine.run()
    except Exception as e:
        console.print(f"[red][SCHEDULER] Error en aprendizaje: {e}[/red]")


def run_price_snapshot():
    """Snapshot de precios para historial (cada hora)."""
    from tools.market_data import get_multiple_stocks
    from tools.crypto_data import get_top_coins
    from memory.database import save_price
    from config.settings import DEFAULT_STOCKS, DEFAULT_CRYPTO

    try:
        # Stocks
        prices = get_multiple_stocks(DEFAULT_STOCKS[:5])
        for p in prices:
            if p.get("price"):
                save_price(p["symbol"], "stock", p["price"], change_pct=p.get("change_pct", 0))

        # Crypto top 5
        coins = get_top_coins(limit=5)
        for c in coins:
            if c.get("price"):
                save_price(c["symbol"], "crypto", c["price"], change_pct=c.get("change_24h", 0))

    except Exception:
        pass  # Los snapshots de precio son silenciosos


def setup_schedules():
    """Configura las tareas programadas."""
    from config.settings import DAILY_RUN_TIME, WEEKLY_RUN_DAY

    # Análisis diario a las 8:00
    schedule.every().day.at(DAILY_RUN_TIME).do(run_daily_analysis)

    # Análisis semanal (lunes por la mañana)
    getattr(schedule.every(), WEEKLY_RUN_DAY).at("09:00").do(run_weekly_analysis)

    # Ciclo de aprendizaje: cada tarde a las 18:00
    schedule.every().day.at("18:00").do(run_learning_cycle)

    # Snapshots de precio: cada 2 horas en horario de mercado
    schedule.every(2).hours.do(run_price_snapshot)

    console.print("[green]Tareas programadas:[/green]")
    console.print(f"  ▶ Análisis diario: {DAILY_RUN_TIME}")
    console.print(f"  ▶ Análisis semanal: {WEEKLY_RUN_DAY.capitalize()} 09:00")
    console.print(f"  ▶ Aprendizaje: diario 18:00")
    console.print(f"  ▶ Snapshot precios: cada 2 horas")


def run_scheduler():
    """Loop principal del scheduler."""
    from rich.panel import Panel

    console.print(Panel(
        "[bold cyan]SCHEDULER DE INVERSIÓN ACTIVO[/bold cyan]\n"
        "[dim]El sistema analizará los mercados automáticamente[/dim]\n"
        "[dim]Ctrl+C para detener[/dim]",
        border_style="cyan"
    ))

    init_db()
    setup_schedules()

    console.print("\n[dim]Scheduler en marcha... esperando próxima tarea[/dim]")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler detenido[/yellow]")


def run_once():
    """Ejecuta todos los análisis una vez ahora."""
    console.print("[cyan]Ejecutando análisis completo ahora...[/cyan]")
    init_db()
    run_daily_analysis()
    run_learning_cycle()


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        run_scheduler()
