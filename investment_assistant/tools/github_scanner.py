"""Scanner de GitHub para descubrir herramientas open-source de finanzas."""
import requests
import time
from typing import Dict, List, Optional
from config.settings import GITHUB_TOKEN, GITHUB_TOPICS

HEADERS = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

BASE_URL = "https://api.github.com"


def _get(url: str, params: Dict = None) -> Optional[Dict]:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code == 403:
            reset = int(r.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset - time.time()) + 5
            time.sleep(min(wait, 30))
            r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


def search_fintech_repos(topics: List[str] = None, min_stars: int = 50) -> List[Dict]:
    """Busca repositorios de fintech/trading relevantes."""
    topics = topics or GITHUB_TOPICS
    all_repos = []
    seen = set()

    for topic in topics[:5]:  # Limitar para no gastar rate limit
        query = f"topic:{topic} stars:>={min_stars} language:python"
        data = _get(f"{BASE_URL}/search/repositories", params={
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5,
        })
        if not data:
            continue

        for repo in data.get("items", []):
            if repo["full_name"] in seen:
                continue
            seen.add(repo["full_name"])

            category = _categorize_repo(repo, topic)
            relevance = _calc_relevance(repo, topic)

            all_repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description", ""),
                "html_url": repo["html_url"],
                "stargazers_count": repo.get("stargazers_count", 0),
                "forks_count": repo.get("forks_count", 0),
                "language": repo.get("language", "Unknown"),
                "topics": repo.get("topics", []),
                "category": category,
                "relevance_score": relevance,
                "recommendation": _generate_recommendation(repo, category),
                "pushed_at": repo.get("pushed_at", ""),
            })
        time.sleep(1)  # Respetar rate limit

    return sorted(all_repos, key=lambda x: x["relevance_score"], reverse=True)


def _categorize_repo(repo: Dict, topic: str) -> str:
    """Categoriza el repo por tipo de herramienta."""
    name = (repo.get("name", "") + " " + (repo.get("description") or "")).lower()
    topics = repo.get("topics", [])

    if any(t in topics for t in ["backtesting", "backtest"]) or "backtest" in name:
        return "backtesting"
    if any(t in topics for t in ["algorithmic-trading", "algo-trading"]) or "algo" in name:
        return "algo_trading"
    if any(t in topics for t in ["portfolio", "portfolio-management"]) or "portfolio" in name:
        return "portfolio"
    if any(t in topics for t in ["crypto", "cryptocurrency"]) or "crypto" in name:
        return "crypto"
    if "real-estate" in topic or "real-estate" in name or "property" in name:
        return "real_estate"
    if "data" in name or "dataset" in name:
        return "data"
    if "analysis" in name or "analytics" in name:
        return "analytics"
    if "dashboard" in name or "visualiz" in name:
        return "visualization"
    return "general_finance"


def _calc_relevance(repo: Dict, topic: str) -> float:
    """Puntúa la relevancia del repo (0.0 a 1.0)."""
    score = 0.0
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)

    # Estrellas (log scale)
    if stars > 10000:
        score += 0.4
    elif stars > 1000:
        score += 0.3
    elif stars > 100:
        score += 0.2
    else:
        score += 0.1

    # Actividad reciente
    pushed = repo.get("pushed_at", "")
    if pushed:
        from datetime import datetime, timezone
        try:
            last_push = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - last_push).days
            if days_ago < 30:
                score += 0.3
            elif days_ago < 90:
                score += 0.2
            elif days_ago < 365:
                score += 0.1
        except Exception:
            pass

    # Ratio forks/stars (indica uso real)
    if stars > 0 and forks / stars > 0.1:
        score += 0.15

    # Python (más fácil de integrar)
    if repo.get("language") == "Python":
        score += 0.15

    return min(1.0, round(score, 2))


def _generate_recommendation(repo: Dict, category: str) -> str:
    """Genera recomendación de uso."""
    name = repo.get("name", "")
    desc = repo.get("description", "") or ""
    stars = repo.get("stargazers_count", 0)

    recs = {
        "backtesting": f"Usa {name} para testear estrategias de trading con datos históricos antes de invertir dinero real.",
        "algo_trading": f"Implementa con {name} estrategias automatizadas. Revisa su documentación para configurar señales.",
        "portfolio": f"Usa {name} para optimizar la distribución de tu cartera y gestionar el riesgo.",
        "crypto": f"Integra {name} para análisis on-chain y seguimiento de wallets cripto.",
        "real_estate": f"Usa {name} para analizar mercados inmobiliarios y calcular rentabilidades.",
        "data": f"{name} proporciona datos financieros. Úsalo como fuente de información para el sistema.",
        "analytics": f"Añade {name} al pipeline de análisis para mejorar las señales técnicas.",
        "visualization": f"Usa {name} para crear dashboards visuales de tu cartera.",
        "general_finance": f"Herramienta financiera ({stars} ⭐): {desc[:100]}",
    }
    return recs.get(category, f"Evalúa {name} ({stars} ⭐): {desc[:100]}")


def get_trending_fintech(since: str = "weekly") -> List[Dict]:
    """Repos de fintech en tendencia (trending)."""
    # GitHub no tiene API oficial de trending, usamos búsqueda reciente
    query = "stars:>50 language:python topic:finance pushed:>2024-01-01"
    data = _get(f"{BASE_URL}/search/repositories", params={
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": 10,
    })
    if not data:
        return []

    return [{
        "name": r["name"],
        "full_name": r["full_name"],
        "description": r.get("description", ""),
        "url": r["html_url"],
        "stars": r.get("stargazers_count", 0),
        "language": r.get("language", ""),
        "updated_at": r.get("updated_at", ""),
    } for r in data.get("items", [])]


def get_repo_readme_summary(full_name: str) -> str:
    """Obtiene un extracto del README."""
    data = _get(f"{BASE_URL}/repos/{full_name}/readme")
    if not data:
        return ""
    import base64
    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
    # Primeras líneas relevantes
    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
    return " ".join(lines[:5])[:500]
