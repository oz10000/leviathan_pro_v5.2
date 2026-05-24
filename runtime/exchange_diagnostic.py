#!/usr/bin/env python3
"""Diagnóstico de conectividad OKX usando CCXT."""
import sys, os, ccxt
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"

def log(msg):
    print(msg)

def main():
    log("🔍 Diagnóstico de conectividad OKX (CCXT)")

    # 1. Conectar
    exchange = ccxt.okx({
        'apiKey': Config.API_KEY,
        'secret': Config.API_SECRET,
        'password': Config.PASSPHRASE if Config.PASSPHRASE else '',
        'enableRateLimit': True,
        'timeout': 30000,
        'options': {'defaultType': 'swap'}
    })

    if Config.EXECUTION_MODE == "demo":
        exchange.set_sandbox_mode(True)
        log(f"{INFO} Modo sandbox activado para demo.")

    # 2. Probar conectividad básica
    try:
        ts = exchange.fetch_time()
        log(f"{PASS} Servidor OKX responde. Hora: {datetime.fromtimestamp(ts/1000)}")
    except Exception as e:
        log(f"{FAIL} Error de conectividad: {e}")
        sys.exit(1)

    # 3. Probar ticker público
    try:
        ticker = exchange.fetch_ticker("BTC/USDT:USDT")
        log(f"{PASS} Ticker BTC: bid={ticker['bid']} ask={ticker['ask']} last={ticker['last']}")
    except Exception as e:
        log(f"{FAIL} Error al obtener ticker: {e}")
        sys.exit(1)

    # 4. Probar autenticación (solo en demo/live)
    if Config.EXECUTION_MODE != "paper":
        try:
            balance = exchange.fetch_balance()
            usdt = balance.get("USDT", {}).get("free", 0.0)
            log(f"{PASS} Autenticación OK. Balance USDT: {usdt}")
        except Exception as e:
            log(f"{FAIL} Error de autenticación: {e}")
            sys.exit(1)

        # 5. Smoke test de orden (solo demo)
        if Config.EXECUTION_MODE == "demo":
            try:
                log("📝 Probando micro‑orden demo...")
                order = exchange.create_market_order("BTC/USDT:USDT", "buy", 0.001,
                                                     params={"tpTriggerPx": "100000", "tpOrdPx": "-1",
                                                             "slTriggerPx": "100", "slOrdPx": "-1"})
                ordId = order.get("id", "")
                log(f"{PASS} Orden demo creada (ID: {ordId})")
                # Cancelar
                exchange.cancel_order(ordId, "BTC/USDT:USDT")
                log(f"{PASS} Orden cancelada correctamente.")
            except Exception as e:
                log(f"{FAIL} Error en smoke test: {e}")
                sys.exit(1)

    print("\n" + "="*50)
    print("🎉 DIAGNÓSTICO COMPLETADO EXITOSAMENTE")
    sys.exit(0)

if __name__ == "__main__":
    main()
