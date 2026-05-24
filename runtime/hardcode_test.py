#!/usr/bin/env python3
"""Test TEMPORAL con hardcodeo. ELIMINAR DESPUÉS DE USAR."""
import ccxt
import sys, os

# ⚠️ Credenciales hardcodeadas (SOLO PARA DIAGNÓSTICO)
API_KEY = "76254b4d-2126-4bb5-a0f1-8c0aa463d90e"
API_SECRET = "36F40E60584E4561E1E2475B979ABDDF"
PASSPHRASE = ""  # no tiene

print("🔍 Probando autenticación con hardcodeo...")

exchange = ccxt.okx({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'password': PASSPHRASE,
    'enableRateLimit': True,
    'timeout': 30000,
    'options': {'defaultType': 'swap'}
})

exchange.set_sandbox_mode(True)

# 1. Conectividad
try:
    ts = exchange.fetch_time()
    print(f"✅ Conectividad OK")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# 2. Balance
try:
    balance = exchange.fetch_balance()
    usdt = balance.get("USDT", {}).get("free", 0.0)
    print(f"✅ Balance USDT: {usdt}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# 3. Ticker
try:
    ticker = exchange.fetch_ticker("BTC/USDT:USDT")
    print(f"✅ Ticker: {ticker['last']}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("🎉 Hardcode test completado con éxito")
print("⚠️ RECUERDA ELIMINAR ESTE ARCHIVO Y REVOCAR LAS CREDENCIALES")
