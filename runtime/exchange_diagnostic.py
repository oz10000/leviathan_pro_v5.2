#!/usr/bin/env python3
"""
Diagnóstico definitivo de conectividad OKX – versión con respuesta HTTP detallada.
"""

import sys, os, time, json, hmac, base64, requests
from datetime import datetime, timezone

# Ajuste de rutas
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"

BACKUP_API_KEY = "88221589-94dd-4bd7-8a1b-cbeb4a981a60"
BACKUP_API_SECRET = "16F5F3F591BD10B2701686197924E78E"
BACKUP_PASSPHRASE = ""

def get_credentials():
    key = os.getenv("OKX_API_KEY") or BACKUP_API_KEY
    secret = os.getenv("OKX_API_SECRET") or BACKUP_API_SECRET
    passphrase = os.getenv("OKX_PASSPHRASE") or BACKUP_PASSPHRASE
    return key, secret, passphrase

# ------------------------------------------------------------
# Conector mínimo (como el que funciona en Okx-test)
# ------------------------------------------------------------
class DiagConnector:
    def __init__(self):
        self.base = "https://www.okx.com"
        self.key, self.secret, self.passphrase = get_credentials()

    def _sign(self, method, path, body=""):
        ts = datetime.now(timezone.utc).isoformat("T", "milliseconds").split("+")[0] + "Z"
        msg = ts + method + path + body
        mac = hmac.new(self.secret.encode(), msg.encode(), 'sha256').digest()
        return ts, base64.b64encode(mac).decode()

    def _private(self, method, path, body=None):
        body_str = json.dumps(body) if body else ""
        ts, sign = self._sign(method, path, body_str)
        headers = {
            "OK-ACCESS-KEY": self.key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        if self.passphrase and self.passphrase.strip():
            headers["OK-ACCESS-PASSPHRASE"] = self.passphrase

        print(f"   >> Petición: {method} {self.base}{path}")
        print(f"   >> Headers: { {k: v[:20]+'...' if len(str(v))>20 else v for k, v in headers.items()} }")
        try:
            r = requests.request(method, self.base + path, data=body_str, headers=headers, timeout=10)
            print(f"   << HTTP Status: {r.status_code}")
            print(f"   << Respuesta: {r.text[:500]}")
            return r
        except Exception as e:
            print(f"   << Excepción: {e}")
            return None

# ------------------------------------------------------------
# Pruebas
# ------------------------------------------------------------
def log(msg):
    print(msg)

def test_public_candles():
    log("🔍 Probando conectividad pública (velas)...")
    try:
        r = requests.get("https://www.okx.com/api/v5/market/candles",
                         params={"instId": "BTC-USDT-SWAP", "bar": "5m", "limit": 5}, timeout=10)
        data = r.json()
        if data.get("code") == "0" and data.get("data"):
            log(f"{PASS} Velas públicas OK ({len(data['data'])} filas).")
            return True
        else:
            log(f"{FAIL} Velas públicas fallaron: {data}")
            return False
    except Exception as e:
        log(f"{FAIL} Excepción en velas públicas: {e}")
        return False

def test_public_tickers():
    log("🔍 Probando tickers...")
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers",
                         params={"instType": "SWAP"}, timeout=10)
        data = r.json()
        if data.get("code") == "0" and data.get("data"):
            log(f"{PASS} Tickers OK ({len(data['data'])} instrumentos).")
            return True
        else:
            log(f"{FAIL} Tickers fallaron: {data}")
            return False
    except Exception as e:
        log(f"{FAIL} Excepción en tickers: {e}")
        return False

def test_auth(conn):
    log("🔐 Probando autenticación privada...")
    r = conn._private("GET", "/api/v5/account/balance")
    if r is None:
        log(f"{FAIL} No se obtuvo respuesta (posible error de red).")
        return False
    if r.status_code != 200:
        log(f"{FAIL} HTTP {r.status_code}")
        return False
    resp = r.json()
    if resp.get("code") != "0":
        log(f"{FAIL} Error: {resp.get('msg')} (código {resp.get('code')})")
        return False
    for d in resp.get("data", []):
        if d.get("ccy") == "USDT":
            log(f"{PASS} Autenticación OK. Balance: {d.get('availBal')} USDT")
            return True
    log(f"{FAIL} No se encontró USDT en la respuesta.")
    return False

def test_demo_order(conn):
    log("📝 Smoke test de orden demo...")
    body = {
        "instId": "BTC-USDT-SWAP",
        "tdMode": "cross",
        "side": "buy",
        "ordType": "market",
        "sz": "0.001",
        "posSide": "long"
    }
    r = conn._private("POST", "/api/v5/trade/order", body)
    if r is None or r.status_code != 200:
        log(f"{FAIL} No se pudo crear la orden demo.")
        return False
    resp = r.json()
    if resp.get("code") != "0":
        log(f"{FAIL} Error: {resp.get('msg')} (código {resp.get('code')})")
        return False
    ordId = resp.get("data", [{}])[0].get("ordId")
    log(f"{PASS} Orden demo creada (ID: {ordId}). Cancelando...")
    conn._private("POST", "/api/v5/trade/cancel-order", {"ordId": ordId, "instId": "BTC-USDT-SWAP"})
    return True

if __name__ == "__main__":
    conn = DiagConnector()
    results = []
    results.append(("Velas públicas", test_public_candles()))
    results.append(("Tickers públicos", test_public_tickers()))
    results.append(("Autenticación", test_auth(conn)))
    results.append(("Orden demo", test_demo_order(conn)))

    print("\n" + "="*50)
    print("RESUMEN DEL DIAGNÓSTICO")
    for name, ok in results:
        print(f"  {name}: {'OK' if ok else 'FALLO'}")
    if all(ok for _, ok in results):
        print("\n🎉 DIAGNÓSTICO COMPLETO EXITOSO")
        sys.exit(0)
    else:
        print("\n❌ DIAGNÓSTICO FALLIDO")
        sys.exit(1)
