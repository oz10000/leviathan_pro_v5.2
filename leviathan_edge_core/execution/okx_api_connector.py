import requests, pandas as pd, time, json, hmac, base64
from datetime import datetime, timezone
from config import Config

class OKXConnector:
    def __init__(self):
        self.base = Config.BASE_URL
        self.key = Config.API_KEY
        self.secret = Config.API_SECRET
        self.passphrase = Config.PASSPHRASE

    def _sign(self, method, path, body=""):
        ts = datetime.now(timezone.utc).isoformat("T","milliseconds").split("+")[0]+"Z"
        msg = ts + method + path + body
        mac = hmac.new(self.secret.encode(), msg.encode(), 'sha256').digest()
        return ts, base64.b64encode(mac).decode()

    def _private(self, method, path, data=None):
        body = json.dumps(data) if data else ""
        ts, sign = self._sign(method, path, body)
        headers = {"OK-ACCESS-KEY":self.key,"OK-ACCESS-SIGN":sign,
                   "OK-ACCESS-TIMESTAMP":ts,"Content-Type":"application/json"}
        if self.passphrase: headers["OK-ACCESS-PASSPHRASE"]=self.passphrase
        for _ in range(3):
            try:
                r = requests.request(method, self.base+path, data=body, headers=headers, timeout=10)
                resp = r.json()
                if resp.get("code")=="0": return resp
            except: pass
            time.sleep(1)
        return None

    def get_candles(self, symbol, bar="5m", limit=200):
        instId = f"{symbol}-USDT-SWAP"
        data = requests.get(f"{self.base}/api/v5/market/candles?instId={instId}&bar={bar}&limit={limit}").json()
        if not data.get("data"): return pd.DataFrame()
        cols = ["ts","open","high","low","close","vol","volCcy"]
        df = pd.DataFrame(data["data"], columns=cols)
        for c in ["open","high","low","close","vol"]: df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
        return df.sort_values("ts").reset_index(drop=True)

    def place_order(self, symbol, side, sz, pos_side, tp=None, sl=None):
        instId = f"{symbol}-USDT-SWAP"
        data = {"instId":instId,"tdMode":"cross","side":side,"ordType":"market",
                "sz":str(round(sz,3)),"posSide":pos_side}
        if tp: data["tpTriggerPx"], data["tpOrdPx"] = str(tp), "-1"
        if sl: data["slTriggerPx"], data["slOrdPx"] = str(sl), "-1"
        return self._private("POST","/api/v5/trade/order", data)

    def close_position(self, symbol, pos_side):
        instId = f"{symbol}-USDT-SWAP"
        close_side = "close_long" if pos_side=="long" else "close_short"
        return self._private("POST","/api/v5/trade/order",
                             {"instId":instId,"tdMode":"cross","side":close_side,"ordType":"market","sz":""})
