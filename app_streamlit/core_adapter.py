import requests
import hmac
import base64
import json
import time
import pandas as pd
from datetime import datetime, timezone


class OKXClient:
    def __init__(self, api_key, secret_key, passphrase, testnet=True):
        self.base_url = "https://demo.okx.com" if testnet else "https://www.okx.com"
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase if not testnet else None

    def _sign(self, method, path, body=""):
        ts = datetime.now(timezone.utc).isoformat("T", "milliseconds").split("+")[0] + "Z"
        msg = ts + method + path + body
        mac = hmac.new(self.secret_key.encode(), msg.encode(), 'sha256').digest()
        sign = base64.b64encode(mac).decode()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        if self.passphrase:
            headers["OK-ACCESS-PASSPHRASE"] = self.passphrase
        return headers

    def _request(self, method, endpoint, params=None, body=None):
        url = self.base_url + endpoint
        headers = self._sign(method, endpoint, body or "")
        try:
            if method == "GET":
                resp = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                resp = requests.post(url, json=body, headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_candles(self, symbol, bar="5m", limit=100):
        instId = f"{symbol}-USDT-SWAP"
        url = f"{self.base_url}/api/v5/market/candles"
        params = {"instId": instId, "bar": bar, "limit": limit}
        try:
            resp = requests.get(url, params=params, timeout=10).json()
            data = resp["data"]
            df = pd.DataFrame(data, columns=["ts","open","high","low","close","vol","volCcy"])
            for col in ["open","high","low","close","vol"]:
                df[col] = pd.to_numeric(df[col])
            df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
            return df.sort_values("ts")
        except:
            return pd.DataFrame()

    def get_balance(self):
        resp = self._request("GET", "/api/v5/account/balance")
        if resp.get("code") == "0":
            for detail in resp["data"][0]["details"]:
                if detail["ccy"] == "USDT":
                    return float(detail["eq"])
        return 0.0

    def market_order(self, symbol, side, size, pos_side):
        body = {
            "instId": f"{symbol}-USDT-SWAP",
            "tdMode": "cross",
            "side": side,
            "ordType": "market",
            "sz": str(size),
            "posSide": pos_side
        }
        return self._request("POST", "/api/v5/trade/order", body=body)

    def close_position(self, symbol, pos_side):
        close_side = "close_long" if pos_side == "long" else "close_short"
        body = {
            "instId": f"{symbol}-USDT-SWAP",
            "tdMode": "cross",
            "side": close_side,
            "ordType": "market",
            "sz": ""
        }
        return self._request("POST", "/api/v5/trade/order", body=body)
