#!/usr/bin/env python3
"""Watchdog operativo para Leviathan. Verifica coherencia de estado."""

import os
import json
import time
from datetime import datetime, timezone

HEARTBEAT_FILE = "runtime/heartbeat.log"
STATE_FILE    = "runtime/state.json"
MAX_SILENCE_SECONDS = 600   # 10 minutos sin heartbeat → anomalía


def check_health(state, pos_mgr, exchange):
    """
    Revisa el último heartbeat y la consistencia de posiciones.
    Si detecta una anomalía, registra [WATCHDOG] y puede activar recovery.
    """
    issues = []

    # 1. Verificar heartbeat reciente
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                lines = f.readlines()
            if lines:
                last_line = lines[-1]
                # Extraer timestamp (formato ISO)
                ts_str = last_line.split(" | ")[0].replace("[HEARTBEAT] ", "").strip()
                last_ts = datetime.fromisoformat(ts_str)
                now = datetime.now(timezone.utc)
                silence = (now - last_ts).total_seconds()
                if silence > MAX_SILENCE_SECONDS:
                    issues.append(f"Heartbeat silencioso por {silence:.0f}s")
        except Exception as e:
            issues.append(f"No se pudo leer heartbeat: {e}")
    else:
        issues.append("Archivo heartbeat.log no encontrado")

    # 2. Verificar coherencia de posiciones
    try:
        local_positions = len(pos_mgr.positions)
        exchange_positions = len(exchange.get_positions())
        if local_positions != exchange_positions:
            issues.append(f"Posiciones locales ({local_positions}) != exchange ({exchange_positions})")
    except Exception as e:
        issues.append(f"No se pudo verificar posiciones: {e}")

    # 3. Verificar que state.json sea reciente
    if os.path.exists(STATE_FILE):
        try:
            mtime = os.path.getmtime(STATE_FILE)
            age = time.time() - mtime
            if age > MAX_SILENCE_SECONDS:
                issues.append(f"state.json sin actualizar por {age:.0f}s")
        except Exception as e:
            issues.append(f"No se pudo verificar state.json: {e}")

    # Emitir diagnóstico
    if issues:
        for msg in issues:
            print(f"[WATCHDOG] ANOMALY: {msg}", flush=True)
        print("[WATCHDOG] RECOVERY_ACTIVATED", flush=True)
    else:
        print("[WATCHDOG] OK", flush=True)
