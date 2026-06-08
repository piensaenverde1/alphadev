"""Agente especializado en criptomonedas."""
from typing import Dict, List
from agents.base import BaseAgent
from tools.crypto_data import get_crypto_signals, get_global_crypto_stats, get_top_coins
from memory.database import save_signal, save_price
from config.settings import DEFAULT_CRYPTO

SYSTEM_PROMPT = """Eres un analista experto en criptomonedas y blockchain.
Tienes profundo conocimiento en:
- Análisis on-chain y métricas de red
- Tokenomics y fundamentos de protocolos
- Ciclos de mercado cripto (halvings, tendencias macro)
- DeFi, NFTs, Layer 2, infraestructura blockchain
- Gestión de riesgo en activos volátiles

Siempre:
1. Advierte sobre la alta volatilidad del mercado cripto
2. Recomienda solo invertir lo que se puede permitir perder
3. Considera la correlación con Bitcoin (BTC dominancia)
4. Analiza el momentum a corto vs potencial a largo plazo
5. Responde en español
"""


class CryptoAgent(BaseAgent):
    name = "crypto_analyst"
    description = "Analiza criptomonedas y genera señales del mercado cripto"

    def run(self, coins: List[str] = None) -> Dict:
        self.log("Iniciando análisis crypto...")
        coins = coins or DEFAULT_CRYPTO

        # 1. Estadísticas globales del mercado
        self.log("Obteniendo estadísticas globales crypto...")
        global_stats = get_global_crypto_stats()

        # 2. Top monedas
        self.log("Obteniendo top monedas...")
        top_coins = get_top_coins(limit=20)

        # 3. Señales técnicas de las monedas monitoreadas
        self.log(f"Analizando señales para {len(coins)} criptos...")
        signals = get_crypto_signals(coins)

        # Guardar precios en historial
        for coin in signals:
            if coin.get("price", 0) > 0:
                save_price(
                    symbol=coin["symbol"],
                    asset_type="crypto",
                    price=coin["price"],
                    change_pct=coin.get("change_24h", 0)
                )

        # 4. Filtrar señales accionables
        actionable = [s for s in signals if s["action"] in ("BUY", "SELL", "WATCH")]

        # 5. Análisis IA
        ai_analysis = ""
        if self.provider != "rules":
            lessons = self.get_lessons_context()
            btc_dom = global_stats.get("btc_dominance", 0)
            market_change = global_stats.get("market_cap_change_24h", 0)

            signals_text = "\n".join([
                f"  {s['name']} ({s['symbol']}): {s['action']} | "
                f"Precio: {s['price']} | 24h: {s.get('change_24h', 0):+.1f}% | "
                f"7d: {s.get('change_7d', 0):+.1f}% | Razones: {'; '.join(s.get('reasons', []))}"
                for s in actionable[:6]
            ])

            ai_analysis = self.ask_ai(
                SYSTEM_PROMPT + ("\n\n" + lessons if lessons else ""),
                f"""Análisis del mercado cripto actual:

ESTADÍSTICAS GLOBALES:
- Capitalización total: {global_stats.get('total_market_cap_eur', 0):,.0f} EUR
- Dominancia BTC: {btc_dom}%
- Cambio mercado 24h: {market_change:+.2f}%

SEÑALES DETECTADAS:
{signals_text}

Proporciona análisis en JSON con:
- "market_phase": fase del mercado (bull/bear/accumulation/distribution)
- "btc_outlook": perspectiva de Bitcoin
- "top_picks": lista de las 3 mejores oportunidades con justificación
- "risks": principales riesgos actuales
- "strategy": estrategia recomendada para el momento
""",
                max_tokens=1500
            )

        # 6. Guardar señales en BD
        saved = []
        for sig in actionable:
            price = sig.get("price", 0)
            if price <= 0:
                continue

            if sig["action"] == "BUY":
                target = price * 1.20
                stop = price * 0.85
            elif sig["action"] == "SELL":
                target = price * 0.80
                stop = price * 1.15
            else:
                target = price * 1.10
                stop = price * 0.90

            signal_id = save_signal(
                symbol=sig["symbol"],
                asset_type="crypto",
                action=sig["action"],
                confidence=min(1.0, abs(sig.get("score", 0)) / 3),
                reasoning=" | ".join(sig.get("reasons", [])),
                price=price,
                target=round(target, 6),
                stop=round(stop, 6),
                horizon="SHORT",
                source=self.name
            )
            saved.append({**sig, "signal_id": signal_id})

        self.log(f"Crypto análisis completado: {len(actionable)} señales")
        return {
            "agent": self.name,
            "global_stats": global_stats,
            "top_coins": top_coins[:10],
            "signals": signals,
            "actionable_signals": saved,
            "ai_analysis": ai_analysis,
        }
