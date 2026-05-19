"""Discover available USDT perpetual swaps on OKX testnet."""
import requests

def fetch_testnet_symbols():
    url = "https://demo.okx.com/api/v5/public/instruments?instType=SWAP"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp.get("code") == "0":
            return [inst["instId"].replace("-USDT-SWAP","") for inst in resp["data"]
                    if inst["instId"].endswith("-USDT-SWAP") and inst["state"] == "live"]
    except Exception:
        pass
    # Fallback if API fails
    return ["BTC","ETH","SOL","BNB","XRP","DOGE","ADA","LINK","LTC","TRX"]
