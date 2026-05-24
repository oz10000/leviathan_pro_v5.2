#!/usr/bin/env python3
"""
Diagnóstico de conectividad y ejecución OKX.
Valida datos públicos, autenticación y el flujo real de órdenes demo con TP/SL.
"""

import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "leviathan_edge_core"))

from config import Config
from execution.okx_api_connector import OKXConnector

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️"

def log(msg):
    print(msg)

def test_public_candles(conn):
    log("🔍 Probando conectividad pública (velas)...")
    df = conn.fetch_candles("BTC", "5m", 5)
    if df.empty:
        log(f"{FAIL} No se pudieron obtener velas públicas.")
        return False
    log(f"{PASS} Velas públicas OK ({len(df)} filas).")
    return True

def test_public_tickers(conn):
    log("🔍 Probando tickers...")
    tickers = conn.fetch_tickers()
    if not tickers:
        log(f"{FAIL} No se pudieron obtener tickers.")
        return False
    log(f"{PASS} Tickers OK ({len(tickers)} instrumentos).")
    return True

def test_auth(conn):
    if Config.EXECUTION_MODE == "paper":
        log(f"{INFO} Modo paper: no se requiere autenticación.")
        return True
    log("🔐 Probando autenticación privada...")
    bal = conn.get_balance()
    if bal == 0.0 and Config.EXECUTION_MODE != "paper":
        log(f"{FAIL} Falló la autenticación (balance 0). Verifica las credenciales.")
        return False
    log(f"{PASS} Autenticación OK. Balance: {bal} USDT")
    return True

def test_demo_order_flow(conn):
    """
    Solo se ejecuta en modo 'demo'.
    Flujo completo:
    1. Abrir una micro‑orden con TP y SL.
    2. Verificar que la orden fue creada.
    3. Consultar órdenes algorítmicas pendientes para confirmar TP y SL.
    4. Cancelar la orden.
    5. Verificar que las órdenes algorítmicas asociadas se cancelan o desaparecen.
    """
    if Config.EXECUTION_MODE != "demo":
        log(f"{INFO} No estamos en modo demo. Omitiendo smoke test de órdenes.")
        return True

    log("📝 Smoke test de orden demo (con TP/SL)...")

    symbol = "BTC"
    size = 0.001   # cantidad mínima
    tp_price = 100000.0
    sl_price = 100.0

    # 1. Colocar orden
    resp = conn.place_order(symbol, "buy", size, "long", tp=tp_price, sl=sl_price)
    if not resp or resp.get("code") != "0":
        log(f"{FAIL} Falló la colocación de la orden demo.")
        log(f"   Respuesta: {resp}")
        return False

    ord_info = resp.get("data", [{}])[0]
    ordId = ord_info.get("ordId", "")
    if not ordId:
        log(f"{FAIL} No se obtuvo ordId tras la orden.")
        return False
    log(f"{PASS} Orden demo creada (ID: {ordId}).")

    # 2. Verificar que la orden existe
    time.sleep(2)  # breve espera para propagación
    order_check = conn._private("GET", f"/api/v5/trade/order?ordId={ordId}")
    if not order_check or order_check.get("code") != "0":
        log(f"{FAIL} No se pudo verificar la orden creada.")
        return False
    log(f"{PASS} Orden verificada en el exchange.")

    # 3. Verificar TP/SL pendientes (órdenes algorítmicas)
    algo_resp = conn._private("GET", "/api/v5/trade/orders-algo-pending")
    if not algo_resp or algo_resp.get("code") != "0":
        log(f"{FAIL} No se pudieron consultar órdenes algorítmicas.")
        return False

    algo_data = algo_resp.get("data", [])
    tp_found = any(
        "tp" in str(a.get("algoId", "")).lower() or a.get("triggerPx", "") == str(tp_price)
        for a in algo_data
    )
    sl_found = any(
        "sl" in str(a.get("algoId", "")).lower() or a.get("triggerPx", "") == str(sl_price)
        for a in algo_data
    )
    if not tp_found:
        log(f"{FAIL} TP no encontrado entre órdenes algorítmicas pendientes.")
        log(f"   Algo orders: {algo_data}")
        return False
    if not sl_found:
        log(f"{FAIL} SL no encontrado entre órdenes algorítmicas pendientes.")
        log(f"   Algo orders: {algo_data}")
        return False
    log(f"{PASS} TP y SL confirmados en el exchange.")

    # 4. Cancelar la orden principal (la demo no se ejecutará en el mercado,
    #    pero la orden existe y debe cancelarse para no dejar residuos)
    cancel = conn._private("POST", "/api/v5/trade/cancel-order", {"ordId": ordId, "instId": "BTC-USDT-SWAP"})
    if cancel and cancel.get("code") == "0":
        log(f"{PASS} Orden cancelada correctamente.")
    else:
        log(f"⚠️ No se pudo cancelar la orden (puede que ya esté completa en demo).")

    # 5. Verificar que ya no haya órdenes algorítmicas asociadas (o que estén canceladas)
    time.sleep(1)
    algo_resp2 = conn._private("GET", "/api/v5/trade/orders-algo-pending")
    remaining = algo_resp2.get("data", []) if algo_resp2 and algo_resp2.get("code") == "0" else []
    if any("tp" in str(a.get("algoId", "")).lower() for a in remaining):
        log(f"{FAIL} TP aún aparece después de cancelar (posible error).")
        return False
    if any("sl" in str(a.get("algoId", "")).lower() for a in remaining):
        log(f"{FAIL} SL aún aparece después de cancelar (posible error).")
        return False
    log(f"{PASS} Limpieza de TP/SL verificada.")

    return True


if __name__ == "__main__":
    conn = OKXConnector()
    results = []
    results.append(("Velas públicas", test_public_candles(conn)))
    results.append(("Tickers públicos", test_public_tickers(conn)))
    results.append(("Autenticación", test_auth(conn)))
    results.append(("Smoke test demo", test_demo_order_flow(conn)))

    all_ok = all(r[1] for r in results)
    print("\n" + "="*50)
    print("RESUMEN DEL DIAGNÓSTICO")
    for name, ok in results:
        print(f"  {name}: {'OK' if ok else 'FALLO'}")
    if all_ok:
        print("\n🎉 DIAGNÓSTICO COMPLETO EXITOSO")
        sys.exit(0)
    else:
        print("\n❌ DIAGNÓSTICO FALLIDO")
        sys.exit(1)
