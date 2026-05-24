#!/usr/bin/env python3
"""Diagnóstico final de conectividad OKX (CCXT)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config
from execution.okx_api_connector import OKXConnector

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"

def main():
    print("🔍 Diagnóstico de conectividad OKX (CCXT)")

    conn = OKXConnector()
    print(f"   Modo: {Config.EXECUTION_MODE}")

    # Velas públicas
    df = conn.fetch_candles("BTC", "5m", 3)
    if not df.empty:
        print(f"{PASS} Velas públicas OK ({len(df)} filas)")
    else:
        print(f"{FAIL} Velas fallaron")
        sys.exit(1)

    # Tickers públicos
    tickers = conn.fetch_tickers()
    if tickers:
        print(f"{PASS} Tickers OK ({len(tickers)} instrumentos)")
    else:
        print(f"{FAIL} Tickers fallaron")
        sys.exit(1)

    # Autenticación y balance (solo demo/live)
    if Config.EXECUTION_MODE != "paper":
        bal = conn.get_balance()
        if bal > 0:
            print(f"{PASS} Balance OK ({bal} USDT)")
        else:
            print(f"{INFO} Balance 0 (posiblemente la cuenta demo no tiene fondos virtuales todavía)")
            # No forzamos el fallo por esto, puede estar recién creada

        # Prueba de orden con tamaño mínimo válido (0.01 BTC)
        print("📝 Probando orden demo con tamaño mínimo (0.01)...")
        resp = conn.place_order("BTC", "buy", 0.01, "long", tp=100000, sl=100)
        if resp.get("code") == "0":
            ordId = resp["data"][0]["ordId"]
            print(f"{PASS} Orden creada ({ordId})")
            conn.close_position("BTC", "long")
            print(f"{PASS} Orden cancelada/cerrada")
        else:
            print(f"{FAIL} Orden falló: {resp}")
            sys.exit(1)

    print("\n🎉 DIAGNÓSTICO COMPLETADO EXITOSAMENTE")

if __name__ == "__main__":
    main()
