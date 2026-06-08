"""Agente scout de tecnología: busca herramientas open-source en GitHub."""
from typing import Dict, List
from agents.base import BaseAgent
from tools.github_scanner import search_fintech_repos, get_trending_fintech
from memory.database import save_github_tool, get_top_github_tools, save_lesson
from config.settings import GITHUB_TOPICS

SYSTEM_PROMPT = """Eres un experto en tecnología financiera (FinTech) y software open-source.
Tu misión es descubrir y evaluar herramientas de código abierto que puedan mejorar
las capacidades de inversión y análisis financiero.

Evalúas repos de GitHub considerando:
1. Utilidad práctica para inversores individuales
2. Calidad y mantenimiento del código
3. Facilidad de integración
4. Comunidad activa (stars, forks, PRs)
5. Casos de uso específicos en trading, portfolio, análisis

Siempre:
- Prioriza herramientas gratuitas y de código abierto
- Indica cómo integrar cada herramienta concretamente
- Detecta si alguna herramienta puede mejorar este sistema de inversión
- Responde en español
"""


class TechAgent(BaseAgent):
    name = "tech_scout"
    description = "Descubre herramientas FinTech open-source en GitHub"

    def run(self, topics: List[str] = None) -> Dict:
        self.log("Escaneando GitHub en busca de herramientas FinTech...")
        topics = topics or GITHUB_TOPICS[:4]  # Limitar para no agotar rate limit

        # 1. Buscar repos relevantes
        self.log(f"Buscando repos para topics: {topics}")
        repos = search_fintech_repos(topics=topics, min_stars=100)
        self.log(f"Encontrados {len(repos)} repositorios relevantes")

        # 2. Guardar en BD
        for repo in repos:
            save_github_tool(repo)

        # 3. Obtener top tools guardados históricamente
        top_tools = get_top_github_tools(limit=10)

        # 4. Repos en trending
        trending = get_trending_fintech()

        # 5. Análisis IA - evalúar y recomendar
        ai_recommendations = ""
        integration_ideas = []

        if repos and self.provider != "rules":
            lessons = self.get_lessons_context()
            repos_text = "\n".join([
                f"  [{r['category']}] {r['full_name']} ({r['stargazers_count']}⭐ {r['language']})\n"
                f"  Descripción: {r['description'][:120]}\n"
                f"  Topics: {', '.join(r.get('topics', [])[:4])}"
                for r in repos[:8]
            ])

            ai_recommendations = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Evalúa estos repositorios de GitHub para un sistema de inversión personal:

REPOSITORIOS ENCONTRADOS:
{repos_text}

El sistema actual tiene:
- Análisis técnico de acciones y ETFs (RSI, MACD, Bollinger)
- Seguimiento de criptomonedas
- Análisis de noticias con sentiment
- Portfolio tracker con SQLite
- Multi-agente con soporte para Claude/Groq/Ollama

Proporciona análisis en JSON con:
- "top_5_tools": las 5 herramientas más valiosas con justificación y cómo integrarlas
- "quick_wins": 2 herramientas que se pueden integrar en <1 hora
- "advanced_tools": herramientas avanzadas para el largo plazo
- "missing_capabilities": qué capacidades importantes faltan en el ecosistema
- "integration_roadmap": hoja de ruta para integrar las mejores herramientas
""",
                max_tokens=2000
            )

            # Extraer ideas de integración para aprendizaje
            try:
                import json
                parsed = json.loads(ai_recommendations)
                for tool in parsed.get("top_5_tools", []):
                    integration_ideas.append(tool)
                    # Guardar como lección
                    save_lesson(
                        lesson_type="tool_discovery",
                        agent=self.name,
                        context=f"GitHub scan - {tool.get('name', 'unknown')}",
                        lesson=f"Herramienta útil: {tool.get('name', '')} - {tool.get('use_case', '')}",
                        confidence=0.7
                    )
            except Exception:
                pass

        # 6. Categorizar por tipo
        by_category: Dict[str, List] = {}
        for repo in repos:
            cat = repo.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(repo)

        self.log(f"Tech scout completado: {len(repos)} repos en {len(by_category)} categorías")
        return {
            "agent": self.name,
            "repos_found": len(repos),
            "top_repos": repos[:5],
            "by_category": by_category,
            "top_tools_historical": top_tools[:5],
            "trending_repos": trending[:5],
            "ai_recommendations": ai_recommendations,
            "integration_ideas": integration_ideas,
        }
