import requests
import time
from config import Config

HEADERS = {
    "User-Agent": "Leviathan/5.2"
}

def fetch_top100_symbols() -> list:
    """
    Obtiene los 100 contratos perpetuos USDT con mayor volumen 24h desde OKX.
    Retorna una lista de símbolos (sin el sufijo -USDT-SWAP).
    """
    url = f"{Config.BASE_URL}/api/v5/market/tickers"
    params = {"instType": "SWAP"}
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            if data.get("code") != "0":
                time.sleep(1)
                continue
            tickers = []
            for item in data.get("data", []):
                instId = item.get("instId", "")
                if not instId.endswith("-USDT-SWAP"):
                    continue
                vol = float(item.get("vol24h", 0))
                if vol >= Config.MIN_VOL24H:
                    tickers.append((instId.replace("-USDT-SWAP", ""), vol))
            tickers.sort(key=lambda x: x[1], reverse=True)
            return [sym for sym, _ in tickers[:Config.TOP_N]]
        except Exception:
            time.sleep(1)
    # Fallback mínimo
    return ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "LTC",
            "SUI", "INJ", "SEI", "TIA", "OP", "RUNE", "APT", "ARB", "WIF", "BONK"]


def adaptive_universe(symbols: list, market_regime_score: float) -> list:
    """
    Reduce el universo operativo según la puntuación del régimen de mercado.
    market_regime_score: 0.0 (hostil) a 1.0 (óptimo).
    """
    if market_regime_score >= 0.8:
        return symbols[:100]
    elif market_regime_score >= 0.6:
        return symbols[:60]
    elif market_regime_score >= 0.4:
        return symbols[:30]
    else:
        return symbols[:10]
