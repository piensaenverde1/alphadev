import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config.settings import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea todas las tablas si no existen."""
    conn = get_connection()
    c = conn.cursor()

    # Portfolio - activos que posees
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            asset_type TEXT NOT NULL,  -- stock, crypto, etf, real_estate, cash
            quantity REAL NOT NULL DEFAULT 0,
            avg_buy_price REAL NOT NULL DEFAULT 0,
            currency TEXT DEFAULT 'EUR',
            notes TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Señales generadas por los agentes
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            asset_type TEXT,
            action TEXT NOT NULL,       -- BUY, SELL, HOLD, WATCH
            confidence REAL,            -- 0.0 a 1.0
            reasoning TEXT,
            price_at_signal REAL,
            price_target REAL,
            stop_loss REAL,
            time_horizon TEXT,          -- SHORT(días), MEDIUM(semanas), LONG(meses)
            agent_source TEXT,          -- qué agente generó la señal
            outcome TEXT,               -- NULL -> pendiente, WIN, LOSS, NEUTRAL
            outcome_price REAL,
            outcome_pct REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            evaluated_at TIMESTAMP
        )
    """)

    # Snapshots diarios de precios
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            asset_type TEXT,
            price REAL,
            volume REAL,
            change_pct REAL,
            market_cap REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Noticias analizadas
    c.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            source TEXT,
            sentiment TEXT,             -- POSITIVE, NEGATIVE, NEUTRAL
            sentiment_score REAL,       -- -1.0 a 1.0
            related_symbols TEXT,       -- JSON array
            summary TEXT,
            published_at TIMESTAMP,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Repos de GitHub descubiertos
    c.execute("""
        CREATE TABLE IF NOT EXISTS github_tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT UNIQUE,
            full_name TEXT,
            description TEXT,
            url TEXT,
            stars INTEGER,
            forks INTEGER,
            language TEXT,
            topics TEXT,                -- JSON array
            category TEXT,              -- trading, analytics, data, portfolio, etc.
            recommendation TEXT,
            relevance_score REAL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Lecciones aprendidas (self-learning)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_type TEXT,           -- signal_accuracy, market_pattern, news_impact
            agent_source TEXT,
            context TEXT,               -- qué situación
            lesson TEXT,                -- qué aprendimos
            confidence REAL,
            times_validated INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Informes generados
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT,           -- daily, weekly, signal, learning
            content TEXT,
            metadata TEXT,              -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ---- Portfolio ----

def upsert_asset(symbol: str, name: str, asset_type: str,
                 quantity: float, avg_price: float, currency: str = "EUR",
                 notes: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO portfolio (symbol, name, asset_type, quantity, avg_buy_price, currency, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            quantity = quantity + excluded.quantity,
            avg_buy_price = (avg_buy_price * quantity + excluded.avg_buy_price * excluded.quantity)
                            / (quantity + excluded.quantity),
            updated_at = CURRENT_TIMESTAMP
    """, (symbol, name, asset_type, quantity, avg_price, currency, notes))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def get_portfolio() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM portfolio WHERE quantity > 0").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_asset(symbol: str):
    conn = get_connection()
    conn.execute("UPDATE portfolio SET quantity = 0 WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()


# ---- Señales ----

def save_signal(symbol: str, asset_type: str, action: str, confidence: float,
                reasoning: str, price: float, target: float, stop: float,
                horizon: str, source: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO signals (symbol, asset_type, action, confidence, reasoning,
            price_at_signal, price_target, stop_loss, time_horizon, agent_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol, asset_type, action, confidence, reasoning,
          price, target, stop, horizon, source))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def get_pending_signals(days_old: int = 30) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM signals
        WHERE outcome IS NULL
        AND created_at >= datetime('now', ? || ' days')
    """, (f"-{days_old}",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_signal(signal_id: int, outcome: str, outcome_price: float, pct: float):
    conn = get_connection()
    conn.execute("""
        UPDATE signals SET outcome=?, outcome_price=?, outcome_pct=?, evaluated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (outcome, outcome_price, pct, signal_id))
    conn.commit()
    conn.close()


# ---- Historial de precios ----

def save_price(symbol: str, asset_type: str, price: float,
               volume: float = 0, change_pct: float = 0, market_cap: float = 0):
    conn = get_connection()
    conn.execute("""
        INSERT INTO price_history (symbol, asset_type, price, volume, change_pct, market_cap)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (symbol, asset_type, price, volume, change_pct, market_cap))
    conn.commit()
    conn.close()


def get_price_history(symbol: str, days: int = 30) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM price_history
        WHERE symbol = ? AND recorded_at >= datetime('now', ? || ' days')
        ORDER BY recorded_at ASC
    """, (symbol, f"-{days}")).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Noticias ----

def save_news(title: str, url: str, source: str, sentiment: str,
              score: float, symbols: List[str], summary: str, published: str):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO news (title, url, source, sentiment, sentiment_score,
            related_symbols, summary, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, url, source, sentiment, score,
          json.dumps(symbols), summary, published))
    conn.commit()
    conn.close()


def get_recent_news(hours: int = 24, limit: int = 20) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM news
        WHERE analyzed_at >= datetime('now', ? || ' hours')
        ORDER BY sentiment_score DESC
        LIMIT ?
    """, (f"-{hours}", limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- GitHub Tools ----

def save_github_tool(repo: Dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO github_tools (repo_name, full_name, description, url, stars,
            forks, language, topics, category, recommendation, relevance_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_name) DO UPDATE SET
            stars = excluded.stars,
            forks = excluded.forks,
            recommendation = excluded.recommendation,
            relevance_score = excluded.relevance_score,
            last_updated = CURRENT_TIMESTAMP
    """, (
        repo.get("name"), repo.get("full_name"), repo.get("description"),
        repo.get("html_url"), repo.get("stargazers_count", 0),
        repo.get("forks_count", 0), repo.get("language"),
        json.dumps(repo.get("topics", [])),
        repo.get("category", "general"),
        repo.get("recommendation", ""),
        repo.get("relevance_score", 0.5)
    ))
    conn.commit()
    conn.close()


def get_top_github_tools(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM github_tools ORDER BY relevance_score DESC, stars DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Lecciones ----

def save_lesson(lesson_type: str, agent: str, context: str,
                lesson: str, confidence: float):
    conn = get_connection()
    # Buscar si ya existe una lección similar para reforzarla
    existing = conn.execute("""
        SELECT id, times_validated FROM lessons
        WHERE lesson_type=? AND agent_source=? AND lesson=?
    """, (lesson_type, agent, lesson)).fetchone()

    if existing:
        conn.execute("""
            UPDATE lessons SET times_validated=times_validated+1,
            confidence=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (confidence, existing["id"]))
    else:
        conn.execute("""
            INSERT INTO lessons (lesson_type, agent_source, context, lesson, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (lesson_type, agent, context, lesson, confidence))
    conn.commit()
    conn.close()


def get_lessons(agent: str = None, limit: int = 20) -> List[Dict]:
    conn = get_connection()
    if agent:
        rows = conn.execute("""
            SELECT * FROM lessons WHERE agent_source=?
            ORDER BY times_validated DESC, confidence DESC LIMIT ?
        """, (agent, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM lessons ORDER BY times_validated DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Informes ----

def save_report(report_type: str, content: str, metadata: Dict = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO reports (report_type, content, metadata) VALUES (?, ?, ?)
    """, (report_type, content, json.dumps(metadata or {})))
    conn.commit()
    conn.close()


def get_agent_accuracy() -> Dict:
    """Calcula el % de acierto de cada agente."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT agent_source,
               COUNT(*) as total,
               SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses,
               AVG(outcome_pct) as avg_return
        FROM signals WHERE outcome IS NOT NULL
        GROUP BY agent_source
    """).fetchall()
    conn.close()
    result = {}
    for r in rows:
        total = r["total"]
        result[r["agent_source"]] = {
            "total": total,
            "wins": r["wins"],
            "losses": r["losses"],
            "win_rate": round(r["wins"] / total * 100, 1) if total else 0,
            "avg_return": round(r["avg_return"] or 0, 2),
        }
    return result
