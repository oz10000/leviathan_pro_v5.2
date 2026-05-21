import requests, hmac, base64, json, time, pandas as pd
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
        for _ in range(3):
            try:
                if method == "GET":
                    resp = requests.get(url, params=params, headers=headers, timeout=10)
                else:
                    resp = requests.post(url, json=body, headers=headers, timeout=10)
                data = resp.json()
                if data.get("code") == "0":
                    return data
            except Exception:
                time.sleep(1)
        return None

    def get_candles(self, symbol, bar="5m", limit=100):
        instId = f"{symbol}-USDT-SWAP"
        params = {"instId": instId, "bar": bar, "limit": limit}
        data = requests.get(f"{self.base_url}/api/v5/market/candles", params=params, timeout=10).json()
        if data.get("code") != "0":
            return pd.DataFrame()
        cols = ["ts", "open", "high", "low", "close", "vol", "volCcy"]
        df = pd.DataFrame(data["data"], columns=cols)
        for c in ["open", "high", "low", "close", "vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
        df.rename(columns={"vol": "volume"}, inplace=True)
        return df.sort_values("ts").reset_index(drop=True)

    def place_order(self, symbol, side, sz, pos_side, tp=None, sl=None):
        instId = f"{symbol}-USDT-SWAP"
        data = {"instId": instId, "tdMode": "cross", "side": side,
                "ordType": "market", "sz": str(round(sz, 3)), "posSide": pos_side}
        if tp: data["tpTriggerPx"], data["tpOrdPx"] = str(tp), "-1"
        if sl: data["slTriggerPx"], data["slOrdPx"] = str(sl), "-1"
        return self._request("POST", "/api/v5/trade/order", data)

    def close_position(self, symbol, pos_side):
        instId = f"{symbol}-USDT-SWAP"
        close_side = "close_long" if pos_side == "long" else "close_short"
        return self._request("POST", "/api/v5/trade/order",
                             {"instId": instId, "tdMode": "cross", "side": close_side, "ordType": "market", "sz": ""})
