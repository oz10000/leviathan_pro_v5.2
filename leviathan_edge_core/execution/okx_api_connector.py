import json
import time
import hmac
import hashlib
import base64
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class OKXClient:
    """
    Cliente REST unificado para OKX API v5.
    - Firma HMAC manual con timestamp sincronizado.
    - Cabecera x-simulated-trading para demo trading.
    - Reintentos automáticos con backoff.
    - Métodos públicos y privados completos.
    """
    def __init__(self):
        self.api_key = Config.OKX_API_KEY
        self.secret = Config.OKX_API_SECRET
        self.passphrase = Config.OKX_API_PASSPHRASE
        self.demo = Config.OKX_DEMO
        self.base_url = Config.REST_URL
        self._offset = 0
        self.sync_time()

    def sync_time(self):
        """Sincroniza el reloj local con el servidor de OKX."""
        try:
            resp = requests.get(f"{self.base_url}/api/v5/public/time", timeout=5)
            server_ts = int(resp.json()["data"][0]["ts"])
            self._offset = server_ts - int(time.time() * 1000)
            logger.info(f"Time synced. Offset: {self._offset}ms")
        except Exception as e:
            logger.warning(f"Time sync failed: {e}")
            self._offset = 0

    def _get_timestamp(self) -> str:
        """Devuelve el timestamp ajustado con el offset del servidor."""
        return str(int(time.time() * 1000) + self._offset)

    def _sign(self, method: str, path: str, body: str = "") -> dict:
        """Genera las cabeceras de autenticación para una petición."""
        timestamp = self._get_timestamp()
        message = timestamp + method.upper() + path + body
        mac = hmac.new(self.secret.encode(), message.encode(), hashlib.sha256)
        sign = base64.b64encode(mac.digest()).decode()
        headers = {
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"
        return headers

    def _request(self, method: str, path: str, body: dict = None, retry: int = 3) -> dict:
        """Realiza una petición HTTP con reintentos."""
        url = self.base_url + path
        body_str = json.dumps(body) if body else ""
        for attempt in range(1, retry + 1):
            try:
                headers = self._sign(method, path, body_str)
                if method == "GET":
                    resp = requests.get(url, headers=headers, timeout=10)
                else:
                    resp = requests.post(url, headers=headers, data=body_str, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.error(f"HTTP {resp.status_code}: {resp.text}")
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt}/{retry}): {e}")
                if attempt < retry:
                    time.sleep(2 ** attempt)
        return {"code": "-1", "msg": "request_failed"}

    # ---------- Métodos públicos (mercado) ----------
    def get_instruments(self, instType: str = "SWAP") -> list:
        """Obtiene la lista de instrumentos disponibles."""
        data = self._request("GET", f"/api/v5/public/instruments?instType={instType}")
        return data.get("data", [])

    def get_candles(self, instId: str, bar: str = "5m", limit: int = 100) -> list:
        """Obtiene velas históricas para un símbolo."""
        data = self._request("GET", f"/api/v5/market/candles?instId={instId}&bar={bar}&limit={limit}")
        return data.get("data", [])

    def get_tickers(self, instType: str = "SWAP") -> list:
        """Obtiene los tickers públicos de todos los instrumentos."""
        data = self._request("GET", f"/api/v5/market/tickers?instType={instType}")
        return data.get("data", [])

    # ---------- Métodos privados (cuenta) ----------
    def set_position_mode(self, posMode: str = "long_short_mode") -> dict:
        """Configura el modo de posición (long/short simultáneos)."""
        return self._request("POST", "/api/v5/account/set-position-mode", {"posMode": posMode})

    def set_leverage(self, instId: str, lever: int, mgnMode: str = "isolated") -> dict:
        """Establece el apalancamiento para un símbolo."""
        return self._request("POST", "/api/v5/account/set-leverage", {
            "instId": instId, "lever": str(lever), "mgnMode": mgnMode
        })

    def place_order(self, instId: str, side: str, sz: float, posSide: str,
                    reduceOnly: bool = False, clOrdId: str = None) -> dict:
        """
        Envía una orden de mercado.
        - side: "buy" / "sell"
        - posSide: "long" / "short"
        - reduceOnly: True para cerrar posición.
        """
        body = {
            "instId": instId,
            "tdMode": "isolated",
            "side": side,
            "ordType": "market",
            "sz": str(sz),
            "posSide": posSide,
            "tgtCcy": "base_ccy",
        }
        if reduceOnly:
            body["reduceOnly"] = True
        if clOrdId:
            body["clOrdId"] = clOrdId
        return self._request("POST", "/api/v5/trade/order", body)

    def get_positions(self, instType: str = "SWAP", instId: str = None) -> list:
        """Obtiene las posiciones abiertas."""
        params = f"/api/v5/account/positions?instType={instType}"
        if instId:
            params += f"&instId={instId}"
        data = self._request("GET", params)
        return data.get("data", [])

    def close_position(self, instId: str, posSide: str) -> dict:
        """Cierra una posición abierta enviando una orden reduce-only."""
        positions = self.get_positions(instId=instId)
        for p in positions:
            if p.get("posSide") == posSide:
                sz = float(p.get("pos", 0))
                if sz > 0:
                    side = "sell" if posSide == "long" else "buy"
                    return self.place_order(instId, side, sz, posSide, reduceOnly=True)
        return {"code": "-1", "msg": "no_position"}
