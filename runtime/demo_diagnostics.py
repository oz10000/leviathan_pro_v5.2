#!/usr/bin/env python3
"""Pruebas forzadas de infraestructura DEMO. Solo para certificación mecánica."""

def run_diagnostics(conn):
    print("[DIAG] Probando fetch_balance...")
    bal = conn.get_balance()
    print(f"[DIAG] Balance: {bal}")

    print("[DIAG] Probando fetch_positions...")
    pos = conn.get_positions()
    print(f"[DIAG] Posiciones: {pos}")

    print("[DIAG] Enviando orden dummy de compra (0.01 BTC) con TP/SL...")
    resp = conn.place_order("BTC", "buy", 0.01, "long", tp=100000, sl=100)
    print(f"[DIAG] Respuesta orden: {resp}")

    if resp and resp.get("code") == "0":
        ordId = resp["data"][0]["ordId"]
        print(f"[DIAG] Orden creada: {ordId}")

        print("[DIAG] Cancelando orden...")
        cancel = conn.cancel_order(ordId, "BTC")
        print(f"[DIAG] Cancelación: {cancel}")

    print("[DIAG] Probando set_leverage (si falla, no es crítico)...")
    try:
        lev_resp = conn.exchange.set_leverage(2, "BTC/USDT:USDT")
        print(f"[DIAG] Leverage ajustado: {lev_resp}")
    except Exception as e:
        print(f"[DIAG] No se pudo ajustar leverage: {e}")

    print("[DIAG] Forzando persistencia de snapshot...")
    import json
    snapshot = {"timestamp": "diagnostic", "test": True}
    with open("runtime/metrics_snapshots.json", "a") as f:
        f.write(json.dumps(snapshot) + "\n")
    print("[DIAG] Snapshot guardado.")

    print("[DIAG] Diagnóstico DEMO completado exitosamente.")
