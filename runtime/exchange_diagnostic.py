#!/usr/bin/env python3
"""Diagnóstico OKX – no depende de Config."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from execution.okx_api_connector import OKXConnector

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"

def main():
    print("🔍 Diagnóstico OKX (CCXT hardcodeado)")

    conn = OKXConnector()

    # Velas
    df = conn.fetch_candles("BTC", "5m", 3)
    if not df.empty:
        print(f"{PASS} Velas públicas OK ({len(df)} filas)")
    else:
        print(f"{FAIL} Velas fallaron")
        sys.exit(1)

    # Tickers
    tickers = conn.fetch_tickers()
    if tickers:
        print(f"{PASS} Tickers OK ({len(tickers)} instrumentos)")
    else:
        print(f"{FAIL} Tickers fallaron")
        sys.exit(1)

    # Balance
    bal = conn.get_balance()
    if bal > 0:
        print(f"{PASS} Balance OK ({bal} USDT)")
    else:
        print(f"{INFO} Balance 0 (fondos virtuales no asignados aún)")

    # Orden mínima
    print("📝 Orden demo (0.01 BTC)...")
    resp = conn.place_order("BTC", "buy", 0.01, "long", tp=100000, sl=100)
    if resp.get("code") == "0":
        ordId = resp["data"][0]["ordId"]
        print(f"{PASS} Orden creada ({ordId})")
        conn.close_position("BTC", "long")
        print(f"{PASS} Posición cerrada")
    else:
        print(f"{FAIL} Orden falló: {resp}")
        sys.exit(1)

    print("\n🎉 Diagnóstico completado")

if __name__ == "__main__":
    main()
