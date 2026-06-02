import requests
from config import Config

def fetch_top100_symbols():
    url = f"{Config.BASE_URL}/api/v5/market/tickers"
    params = {"instType": "SWAP"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("code") != "0":
            return _fallback_list()
        tickers = []
        for item in data.get("data", []):
            instId = item.get("instId", "")
            if instId.endswith("-USDT-SWAP"):
                sym = instId.replace("-USDT-SWAP", "")
                vol = float(item.get("vol24h", 0))
                if vol >= Config.MIN_VOL24H:
                    tickers.append((sym, vol))
        tickers.sort(key=lambda x: x[1], reverse=True)
        # Devolver solo los primeros 50 (más seguros en Demo)
        return [sym for sym, _ in tickers[:50]]
    except Exception:
        return _fallback_list()

def _fallback_list():
    # Lista de activos confirmados en OKX Demo
    return [
        "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
        "LTC", "SUI", "INJ", "SEI", "TIA", "OP", "APT", "ARB", "WIF",
        "BONK", "MATIC"
    ]
