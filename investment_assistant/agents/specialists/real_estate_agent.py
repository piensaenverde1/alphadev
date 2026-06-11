"""Agente especialista en análisis del mercado inmobiliario vía REITs y sector."""
import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from agents.base import BaseAgent
from tools.market_data import get_multiple_stocks, get_technical_signals
from memory.database import save_lesson, save_price, get_lessons

SYSTEM_PROMPT = """Eres un analista especialista en inversión inmobiliaria, REITs y mercados
de propiedad. Tu rol es evaluar el sector inmobiliario como clase de activo desde la
perspectiva de un inversor individual con acceso a mercados cotizados (REITs, ETFs).

Cuando analices el mercado inmobiliario:
1. Evalúa el impacto de los tipos de interés en los REITs (relación inversa)
2. Diferencia entre subsectores: industrial/logístico, datos, residencial, comercial, sanitario
3. Identifica cuáles REITs ofrecen mejor relación riesgo/rentabilidad ajustada a tipos
4. Considera el dividendo como componente clave del retorno total en REITs
5. Analiza los REITs hipotecarios por separado (más sensibles a tipos)
6. Compara el desempeño del sector vs el mercado amplio (SPY)

Responde siempre en español. Sé específico sobre tickers y niveles de precios.
Responde en formato JSON con claves:
"sector_outlook", "best_subsectors" (lista), "rate_impact_analysis",
"top_opportunities" (lista con ticker, razón, riesgo), "dividend_highlights",
"risks" (lista), "summary"
"""

# ETFs de REITs a monitorear
REIT_ETFS = {
    "IYR": "iShares US Real Estate ETF (diversificado)",
    "VNQ": "Vanguard Real Estate ETF (diversificado)",
    "XLRE": "Real Estate Select Sector SPDR",
    "REM": "iShares Mortgage Real Estate ETF",
    "MORT": "VanEck Mortgage REIT Income ETF",
}

# REITs individuales por subsector
INDIVIDUAL_REITS = {
    "AMT": {"name": "American Tower", "subsector": "torres_telecomunicaciones"},
    "PLD": {"name": "Prologis", "subsector": "logistica_industrial"},
    "EQIX": {"name": "Equinix", "subsector": "centros_datos"},
    "SPG": {"name": "Simon Property Group", "subsector": "retail_comercial"},
    "O": {"name": "Realty Income", "subsector": "net_lease"},
}

# Benchmark de referencia
BENCHMARK = "SPY"

# RSS inmobiliario en español (sin feedparser, usamos requests + regex XML básico)
REAL_ESTATE_RSS = "https://www.elconfidencial.com/rss/inmobiliario.xml"


def _fetch_rss_headlines(url: str, max_items: int = 5) -> List[str]:
    """
    Obtiene titulares de un feed RSS sin usar feedparser.
    Parseo básico con expresiones regulares sobre el XML.
    """
    headlines = []
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return headlines
        content = resp.text
        # Extraer bloques <item>…</item>
        items = re.findall(r"<item[^>]*>(.*?)</item>", content, re.DOTALL)
        for item in items[:max_items]:
            title_match = re.search(
                r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", item, re.DOTALL
            )
            if title_match:
                title = title_match.group(1).strip()
                # Limpiar entidades HTML básicas
                title = (
                    title.replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&quot;", '"')
                    .replace("&#39;", "'")
                )
                if title and title not in headlines:
                    headlines.append(title)
    except Exception:
        pass
    return headlines


def _generate_demo_reit_data() -> Dict[str, Dict]:
    """Datos sintéticos de REITs cuando yfinance falla completamente."""
    demo = {
        "IYR":  {"price": 88.50,  "change_pct": -0.32},
        "VNQ":  {"price": 85.20,  "change_pct": -0.28},
        "XLRE": {"price": 42.10,  "change_pct": -0.15},
        "REM":  {"price": 22.80,  "change_pct": -0.88},
        "MORT": {"price": 11.50,  "change_pct": -1.20},
        "AMT":  {"price": 185.40, "change_pct":  0.45},
        "PLD":  {"price": 115.60, "change_pct":  0.22},
        "EQIX": {"price": 755.00, "change_pct":  0.65},
        "SPG":  {"price": 148.30, "change_pct": -0.10},
        "O":    {"price": 54.20,  "change_pct": -0.35},
        "SPY":  {"price": 478.50, "change_pct":  0.55},
    }
    return {k: {**v, "symbol": k, "is_demo": True} for k, v in demo.items()}


class RealEstateAgent(BaseAgent):
    name = "real_estate_specialist"
    description = "Analiza el mercado inmobiliario vía REITs, ETFs de real estate y su relación con tipos de interés"

    def run(self) -> Dict:
        self.log("Iniciando análisis del mercado inmobiliario...")

        all_symbols = list(REIT_ETFS.keys()) + list(INDIVIDUAL_REITS.keys()) + [BENCHMARK]

        # 1. Obtener precios de todos los REITs y el benchmark
        self.log(f"Fetching precios de {len(all_symbols)} REITs y ETFs...")
        raw_data_map: Dict[str, Dict] = {}
        data_source = "live"

        try:
            raw_list = get_multiple_stocks(all_symbols)
            for item in raw_list:
                sym = item.get("symbol", "")
                raw_data_map[sym] = item
            # Verificar que al menos varios datos son válidos
            valid_count = sum(1 for d in raw_data_map.values() if d.get("price", 0) > 0)
            if valid_count < 3:
                raise ValueError(f"Solo {valid_count} tickers con datos válidos")
        except Exception as e:
            self.log(f"Error en datos de mercado: {e}. Usando datos demo.")
            raw_data_map = _generate_demo_reit_data()
            data_source = "demo"

        # Guardar precios en historial
        for sym, data in raw_data_map.items():
            price = data.get("price", 0)
            change = data.get("change_pct", 0)
            if price > 0:
                try:
                    asset_type = "etf" if sym in REIT_ETFS or sym == BENCHMARK else "stock"
                    save_price(sym, asset_type, price, change_pct=change)
                except Exception:
                    pass

        # 2. Rendimiento del sector REIT vs mercado amplio
        self.log("Calculando desempeño relativo del sector...")
        spy_change = raw_data_map.get("SPY", {}).get("change_pct", 0.0)

        reit_performance: Dict[str, Dict] = {}
        etf_changes: List[float] = []

        for sym, desc in REIT_ETFS.items():
            data = raw_data_map.get(sym, {})
            price = data.get("price", 0.0)
            change = data.get("change_pct", 0.0)
            vs_spy = round(change - spy_change, 2)
            etf_changes.append(change)
            reit_performance[sym] = {
                "name": desc,
                "price": price,
                "change_pct": change,
                "vs_spy": vs_spy,
                "outperforming_spy": vs_spy > 0,
                "type": "etf",
            }

        for sym, info in INDIVIDUAL_REITS.items():
            data = raw_data_map.get(sym, {})
            price = data.get("price", 0.0)
            change = data.get("change_pct", 0.0)
            vs_spy = round(change - spy_change, 2)
            reit_performance[sym] = {
                "name": info["name"],
                "subsector": info["subsector"],
                "price": price,
                "change_pct": change,
                "vs_spy": vs_spy,
                "outperforming_spy": vs_spy > 0,
                "type": "individual_reit",
            }

        sector_avg_change = round(sum(etf_changes) / len(etf_changes), 2) if etf_changes else 0.0
        sector_vs_spy = round(sector_avg_change - spy_change, 2)

        # 3. Identificar mejores subsectores
        self.log("Identificando mejores subsectores...")
        subsector_perf: Dict[str, List[float]] = {}
        for sym, info in INDIVIDUAL_REITS.items():
            subsector = info["subsector"]
            change = reit_performance.get(sym, {}).get("change_pct", 0.0)
            subsector_perf.setdefault(subsector, []).append(change)

        best_subsectors: List[Dict] = []
        for subsector, changes in subsector_perf.items():
            avg = round(sum(changes) / len(changes), 2)
            best_subsectors.append({
                "subsector": subsector,
                "avg_change_pct": avg,
                "vs_spy": round(avg - spy_change, 2),
                "tickers": [
                    sym for sym, info in INDIVIDUAL_REITS.items()
                    if info["subsector"] == subsector
                ],
            })
        best_subsectors.sort(key=lambda x: x["avg_change_pct"], reverse=True)

        # 4. Análisis de sensibilidad a tipos de interés (US 10Y como proxy)
        self.log("Analizando sensibilidad a tipos de interés...")
        us10y_rate = 4.3
        us10y_change = 0.0
        try:
            us10y_raw = get_multiple_stocks(["^TNX"])
            if us10y_raw and us10y_raw[0].get("price", 0) > 0:
                us10y_rate = us10y_raw[0]["price"]
                us10y_change = us10y_raw[0].get("change_pct", 0.0)
        except Exception:
            pass  # mantener valores por defecto

        rate_sensitivity = {
            "us_10y_rate": us10y_rate,
            "us_10y_change_1d": us10y_change,
            "rates_rising": us10y_change > 0,
            "rate_environment": (
                "ADVERSO" if us10y_rate > 5.0
                else "NEUTRAL" if us10y_rate > 4.0
                else "FAVORABLE"
            ),
            "reits_rate_impact": (
                "Tipos altos presionan valuaciones de REITs: coste de capital sube "
                "y dividendos menos atractivos vs bonos del tesoro"
                if us10y_rate > 4.5
                else "Tipos moderados ofrecen entorno relativamente favorable para REITs"
            ),
            "most_sensitive": ["REM", "MORT", "O"],   # hipotecarios y net-lease más expuestos
            "least_sensitive": ["AMT", "EQIX", "PLD"],  # infraestructura/datos más resiliente
            "note": (
                "REITs hipotecarios (REM, MORT) son los más sensibles a subidas de tipos. "
                "REITs de infraestructura (AMT, EQIX) y logística (PLD) ofrecen mayor resiliencia "
                "por contratos de largo plazo."
            ),
        }

        # 5. Identificar oportunidades
        opportunities: List[Dict] = []
        for sym, perf in reit_performance.items():
            price = perf.get("price", 0)
            change = perf.get("change_pct", 0)
            vs_spy = perf.get("vs_spy", 0)

            if price <= 0:
                continue

            # Caída relativa vs mercado → posible sobreventa
            if vs_spy < -1.5:
                is_mortgage = sym in ("REM", "MORT")
                opportunities.append({
                    "symbol": sym,
                    "name": perf.get("name", sym),
                    "subsector": perf.get("subsector", "etf_diversificado"),
                    "price": price,
                    "change_pct": change,
                    "vs_spy": vs_spy,
                    "reason": f"Caída {vs_spy:.1f}% vs SPY: posible sobreventa relativa",
                    "risk": "ALTO" if is_mortgage else "MEDIO",
                    "type": "dip_opportunity",
                })
            # Momentum positivo que supera al mercado
            elif vs_spy > 1.0 and change > 0:
                opportunities.append({
                    "symbol": sym,
                    "name": perf.get("name", sym),
                    "subsector": perf.get("subsector", "etf_diversificado"),
                    "price": price,
                    "change_pct": change,
                    "vs_spy": vs_spy,
                    "reason": f"Outperforming SPY +{vs_spy:.1f}%: momentum sectorial positivo",
                    "risk": "BAJO-MEDIO",
                    "type": "momentum_opportunity",
                })

        opportunities.sort(key=lambda x: abs(x.get("vs_spy", 0)), reverse=True)

        # 6. Noticias inmobiliarias en español (El Confidencial)
        self.log("Obteniendo noticias inmobiliarias en español...")
        news_headlines: List[str] = []
        try:
            news_headlines = _fetch_rss_headlines(REAL_ESTATE_RSS, max_items=5)
            if news_headlines:
                self.log(f"Obtenidos {len(news_headlines)} titulares inmobiliarios")
            else:
                self.log("Feed RSS sin titulares disponibles")
        except Exception as e:
            self.log(f"No se pudo obtener noticias RSS: {e}")

        if not news_headlines:
            news_headlines = ["(Noticias no disponibles - verificar conexión a elconfidencial.com)"]

        # Guardar lecciones relevantes
        if us10y_rate > 5.0 and sector_vs_spy < -1.5:
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Tipos 10Y={us10y_rate:.2f}%, sector REIT underperforming SPY en {sector_vs_spy:.1f}%",
                    lesson=(
                        f"Con tipos al {us10y_rate:.2f}%, los REITs siguen bajo presión "
                        f"({sector_vs_spy:.1f}% vs SPY). "
                        "Esperar señal de techo en tipos antes de incrementar exposición."
                    ),
                    confidence=0.80,
                )
            except Exception:
                pass

        if best_subsectors and best_subsectors[0]["avg_change_pct"] > 1.0:
            top_sub = best_subsectors[0]
            try:
                save_lesson(
                    lesson_type="market_pattern",
                    agent=self.name,
                    context=f"Líder REIT: {top_sub['subsector']} ({top_sub['avg_change_pct']:+.2f}%)",
                    lesson=(
                        f"Subsector {top_sub['subsector']} lidera el sector REIT "
                        f"con {top_sub['avg_change_pct']:+.2f}%. "
                        f"Tickers: {', '.join(top_sub['tickers'])}."
                    ),
                    confidence=0.70,
                )
            except Exception:
                pass

        # 7. Análisis IA
        self.log("Generando análisis IA del mercado inmobiliario...")
        ai_analysis = ""
        if self.provider != "rules":
            lessons_ctx = self.get_lessons_context()

            perf_summary = "\n".join([
                f"  {sym}: ${perf.get('price', 0):.2f} | {perf.get('change_pct', 0):+.2f}% | "
                f"vs SPY: {perf.get('vs_spy', 0):+.2f}%"
                + (f" [{perf.get('subsector', '')}]" if perf.get("subsector") else "")
                for sym, perf in reit_performance.items()
            ])

            subsector_summary = "\n".join([
                f"  {s['subsector']}: {s['avg_change_pct']:+.2f}% (vs SPY: {s['vs_spy']:+.2f}%)"
                for s in best_subsectors
            ])

            opp_summary = "\n".join([
                f"  {o['symbol']} ({o['name']}): {o['reason']} | Riesgo: {o['risk']}"
                for o in opportunities[:5]
            ]) or "  Ninguna clara identificada"

            news_text = "\n".join(f"  - {h}" for h in news_headlines)

            user_message = f"""Analiza el mercado inmobiliario y REITs con estos datos:

ENTORNO DE TIPOS:
  Bono EEUU 10Y: {us10y_rate:.3f}% ({us10y_change:+.2f}% hoy)
  Entorno: {rate_sensitivity['rate_environment']}

SECTOR REIT vs MERCADO:
  SPY cambio: {spy_change:+.2f}%
  Sector REIT promedio: {sector_avg_change:+.2f}%
  Sector vs SPY: {sector_vs_spy:+.2f}%

PERFORMANCE POR ACTIVO:
{perf_summary}

MEJORES SUBSECTORES:
{subsector_summary}

OPORTUNIDADES IDENTIFICADAS:
{opp_summary}

NOTICIAS INMOBILIARIAS (El Confidencial):
{news_text}

FUENTE DE DATOS: {"mercado en tiempo real" if data_source == "live" else "datos demo (yfinance no disponible)"}

{lessons_ctx}

Proporciona análisis en formato JSON con:
"sector_outlook" (perspectiva 30-90 días),
"best_subsectors" (lista con mejor potencial y razones),
"rate_impact_analysis" (cómo los tipos actuales afectan a diferentes REITs),
"top_opportunities" (lista de 3 mejores: ticker, razón, riesgo, plazo),
"dividend_highlights" (REITs con mejores características de dividendo en este entorno),
"risks" (lista de 3 principales riesgos del sector),
"summary" (párrafo ejecutivo en español, 3-4 frases)
"""
            try:
                ai_analysis = self.ask_ai(
                    SYSTEM_PROMPT + ("\n\n" + lessons_ctx if lessons_ctx else ""),
                    user_message,
                    max_tokens=1500,
                )
            except Exception as e:
                ai_analysis = f"[Error en análisis IA: {e}]"

        self.log(
            f"Análisis inmobiliario completado. "
            f"Sector vs SPY: {sector_vs_spy:+.2f}%, "
            f"Oportunidades: {len(opportunities)}, "
            f"Datos: {data_source}"
        )

        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "data_source": data_source,
            "reit_performance": reit_performance,
            "sector_summary": {
                "sector_avg_change_pct": sector_avg_change,
                "spy_change_pct": spy_change,
                "sector_vs_spy": sector_vs_spy,
                "outperforming_spy": sector_vs_spy > 0,
                "etfs_tracked": list(REIT_ETFS.keys()),
                "individual_reits_tracked": list(INDIVIDUAL_REITS.keys()),
            },
            "best_subsectors": best_subsectors,
            "rate_sensitivity": rate_sensitivity,
            "opportunities": opportunities[:6],
            "news_headlines": news_headlines,
            "ai_analysis": ai_analysis,
        }
