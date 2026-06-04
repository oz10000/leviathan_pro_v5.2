import json, time, hmac, hashlib, base64, requests, logging
from config import Config

logger = logging.getLogger(__name__)

class OKXClient:
    def __init__(self):
        self.api_key = Config.OKX_API_KEY
        self.secret = Config.OKX_API_SECRET
        self.passphrase = Config.OKX_API_PASSPHRASE
        self.demo = Config.OKX_DEMO
        self.base_url = Config.REST_URL
        self._offset = 0
        self.sync_time()

    def sync_time(self):
        try:
            resp = requests.get(f"{self.base_url}/api/v5/public/time", timeout=5)
            server_ts = int(resp.json()["data"][0]["ts"])
            self._offset = server_ts - int(time.time() * 1000)
            logger.info(f"Time synced. Offset: {self._offset}ms")
        except Exception as e:
            logger.warning(f"Time sync failed: {e}")
            self._offset = 0

    def _get_timestamp(self) -> str:
        return str(int(time.time() * 1000) + self._offset)

    def _sign(self, method: str, path: str, body: str = "") -> dict:
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

    # Métodos públicos y privados sin cambios,
    # solo se usa self.api_key, etc. que vienen de Config
    # ... (resto igual a la versión anterior)
