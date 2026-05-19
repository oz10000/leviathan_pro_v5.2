import requests

def fetch_top100_symbols():
    url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
    try:
        data = requests.get(url, timeout=10).json()["data"]
        tickers = []
        for item in data:
            instId = item["instId"]
            if instId.endswith("-USDT-SWAP"):
                vol = float(item["vol24h"])
                if vol >= 5_000_000:
                    tickers.append((instId.replace("-USDT-SWAP",""), vol))
        tickers.sort(key=lambda x: x[1], reverse=True)
        return [sym for sym, _ in tickers[:100]]
    except:
        return ["BTC","ETH","SOL","BNB","XRP","DOGE","ADA","LINK","LTC","TRX"]
