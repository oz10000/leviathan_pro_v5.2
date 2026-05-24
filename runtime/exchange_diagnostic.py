#!/usr/bin/env python3
"""Diagnóstico de conectividad con OKX."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config
from execution.okx_api_connector import OKXConnector

def test_public():
    print("🔍 Probando conectividad pública (velas)...")
    conn = OKXConnector()
    df = conn.fetch_candles("BTC", "5m", 5)
    if df.empty:
        print("❌ No se pudieron obtener velas públicas.")
        return False
    print(f"✅ Velas públicas OK ({len(df)} filas).")
    return True

def test_auth():
    if Config.EXECUTION_MODE == "paper":
        print("ℹ️ Modo paper: no se requiere autenticación.")
        return True
    print("🔐 Probando autenticación privada...")
    conn = OKXConnector()
    bal = conn.get_balance()
    if bal == 0.0 and Config.EXECUTION_MODE != "paper":
        print("❌ Falló la autenticación privada (balance 0).")
        return False
    print(f"✅ Autenticación OK. Balance: {bal} USDT")
    return True

def test_demo_orders():
    if Config.EXECUTION_MODE != "demo":
        print("ℹ️ No estamos en modo demo, omitiendo prueba de órdenes.")
        return True
    print("📝 Probando orden demo mínima...")
    conn = OKXConnector()
    resp = conn.place_order("BTC", "buy", 0.001, "long", tp=100000.0, sl=100.0)
    if resp and resp.get("code") == "0":
        ordId = resp.get("data", [{}])[0].get("ordId", "")
        print(f"✅ Orden demo creada: {ordId}")
        # Cancelar inmediatamente
        cancel = conn._private("POST", "/api/v5/trade/cancel-order", {"ordId": ordId, "instId": "BTC-USDT-SWAP"})
        if cancel and cancel.get("code") == "0":
            print("✅ Orden cancelada correctamente.")
        return True
    else:
        print(f"❌ Falló la orden demo: {resp}")
        return False

if __name__ == "__main__":
    results = []
    results.append(test_public())
    results.append(test_auth())
    results.append(test_demo_orders())
    if all(results):
        print("\n🎉 DIAGNÓSTICO COMPLETO EXITOSO")
        sys.exit(0)
    else:
        print("\n❌ DIAGNÓSTICO FALLIDO")
        sys.exit(1)
