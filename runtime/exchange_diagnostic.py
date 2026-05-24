#!/usr/bin/env python3
"""Diagnóstico rápido de conectividad con el nuevo conector CCXT."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config
from execution.okx_api_connector import OKXConnector

PASS = "✅"
FAIL = "❌"

def main():
    print("🔍 Diagnóstico de conectividad OKX (CCXT con credenciales hardcodeadas)")

    conn = OKXConnector()
    print(f"   Modo: {Config.EXECUTION_MODE}")

    # Velas
    df = conn.fetch_candles("BTC", "5m", 3)
    if not df.empty:
        print(f"{PASS} Velas públicas OK ({len(df)} filas)")
    else:
        print(f"{FAIL} Velas fallaron")

    # Tickers
    tickers = conn.fetch_tickers()
    if tickers:
        print(f"{PASS} Tickers OK ({len(tickers)} instrumentos)")
    else:
        print(f"{FAIL} Tickers fallaron")

    # Autenticación
    if Config.EXECUTION_MODE != "paper":
        bal = conn.get_balance()
        if bal > 0:
            print(f"{PASS} Balance OK ({bal} USDT)")
        else:
            print(f"{FAIL} Balance no disponible")

        # Orden demo
        resp = conn.place_order("BTC", "buy", 0.001, "long", tp=100000, sl=100)
        if resp.get("code") == "0":
            ordId = resp["data"][0]["ordId"]
            print(f"{PASS} Orden creada ({ordId})")
            conn.close_position("BTC", "long")
            print(f"{PASS} Orden cancelada/cerrada")
        else:
            print(f"{FAIL} Orden falló: {resp}")
    else:
        print("ℹ️ Modo paper, sin pruebas de autenticación")

    print("\n🎉 Diagnóstico completado")

if __name__ == "__main__":
    main()
