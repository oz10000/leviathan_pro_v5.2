import time, json, hmac, base64
import requests
import pandas as pd
from datetime import datetime, timezone
from config import Config
from execution.exchange_connector import ExchangeConnector

class OKXConnector(ExchangeConnector):
    def __init__(self):
        self.base = Config.BASE_URL
        self.key = Config.API_KEY
        self.secret = Config.API_SECRET
        self.passphrase = Config.PASSPHRASE
        self.exec_mode = Config.EXECUTION_MODE

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _public(self, path, params=None):
        for _ in range(3):
            try:
                r = requests.get(self.base + path, params=params, timeout=10)
                data = r.json()
                if data.get("code") == "0":
                    return data
            except Exception:
                pass
            time.sleep(1)
        return None

    def _sign(self, method, path, body=""):
        ts = datetime.now(timezone.utc).isoformat("T", "milliseconds").split("+")[0] + "Z"
        msg = ts + method + path + body
        mac = hmac.new(self.secret.encode(), msg.encode(), 'sha256').digest()
        return ts, base64.b64encode(mac).decode()

    def _private(self, method, path, body=None):
        if self.exec_mode == "paper":
            return None
        body_str = json.dumps(body) if body else ""
        ts, sign = self._sign(method, path, body_str)
        headers = {
            "OK-ACCESS-KEY": self.key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        if self.passphrase:
            headers["OK-ACCESS-PASSPHRASE"] = self.passphrase
        if self.exec_mode == "demo":
            headers["x-simulated-trading"] = "1"

        for _ in range(3):
            try:
                r = requests.request(method, self.base + path, data=body_str,
                                     headers=headers, timeout=10)
                resp = r.json()
                if resp.get("code") == "0":
                    return resp
            except Exception:
                pass
            time.sleep(1)
        return None

    # ------------------------------------------------------------------
    # Market data (público)
    # ------------------------------------------------------------------
    def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
        instId = f"{symbol}-USDT-SWAP"
        data = self._public("/api/v5/market/candles",
                            {"instId": instId, "bar": timeframe, "limit": limit})
        if not data:
            return pd.DataFrame()
        # La API devuelve 9 columnas, nosotros tomamos las primeras 7 que nos interesan
        cols = ["ts", "open", "high", "low", "close", "vol", "volCcy"]
        rows = [row[:7] for row in data["data"]]   # recortar a 7 columnas
        df = pd.DataFrame(rows, columns=cols)
        for c in ["open", "high", "low", "close", "vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
        return df.sort_values("ts").reset_index(drop=True)

    def fetch_tickers(self) -> list:
        data = self._public("/api/v5/market/tickers", {"instType": "SWAP"})
        if not data:
            return []
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Execution (privado)
    # ------------------------------------------------------------------
    def place_order(self, symbol: str, side: str, size: float,
                    pos_side: str, tp: float = None, sl: float = None) -> dict:
        instId = f"{symbol}-USDT-SWAP"
        body = {
            "instId": instId,
            "tdMode": "cross",
            "side": side,
            "ordType": "market",
            "sz": str(round(size, 3)),
            "posSide": pos_side
        }
        if tp and sl:
            body["attachAlgoOrds"] = [
                {"attachAlgoClOrdId": f"tp_{symbol}_{int(time.time())}",
                 "tpTriggerPx": str(tp), "tpOrdPx": "-1", "tpTriggerPxType": "last"},
                {"attachAlgoClOrdId": f"sl_{symbol}_{int(time.time())}",
                 "slTriggerPx": str(sl), "slOrdPx": "-1", "slTriggerPxType": "last"}
            ]
        elif tp:
            body["tpTriggerPx"] = str(tp)
            body["tpOrdPx"] = "-1"
        elif sl:
            body["slTriggerPx"] = str(sl)
            body["slOrdPx"] = "-1"
        return self._private("POST", "/api/v5/trade/order", body)

    def close_position(self, symbol: str, pos_side: str) -> dict:
        instId = f"{symbol}-USDT-SWAP"
        close_side = "close_long" if pos_side == "long" else "close_short"
        return self._private("POST", "/api/v5/trade/order",
                             {"instId": instId, "tdMode": "cross",
                              "side": close_side, "ordType": "market", "sz": ""})

    def get_positions(self) -> dict:
        return self._private("GET", "/api/v5/account/positions")

    def get_balance(self) -> float:
        resp = self._private("GET", "/api/v5/account/balance")
        if resp and resp.get("code") == "0":
            for d in resp.get("data", []):
                if d.get("ccy") == "USDT":
                    return float(d.get("availBal", 0.0))
        return 0.0

    def normalize_symbol(self, raw_symbol: str) -> str:
        return raw_symbol
