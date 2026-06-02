import os, time, json
from datetime import datetime, timezone

HEARTBEAT_FILE = "runtime/heartbeat.log"
STATE_FILE    = "runtime/state.json"
MAX_SILENCE_SECONDS = 600

def check_health(state, pos_mgr, exchange):
    issues = []
    first_run = not os.path.exists(HEARTBEAT_FILE)

    if not first_run:
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                lines = f.readlines()
            if lines:
                last_line = lines[-1]
                ts_str = last_line.split(" | ")[0].replace("[HEARTBEAT] ", "").strip()
                last_ts = datetime.fromisoformat(ts_str)
                silence = (datetime.now(timezone.utc) - last_ts).total_seconds()
                if silence > MAX_SILENCE_SECONDS:
                    issues.append(f"Heartbeat silencioso por {silence:.0f}s")
        except Exception as e:
            issues.append(f"No se pudo leer heartbeat: {e}")

    # Verificar coherencia de posiciones
    try:
        local_positions = len(pos_mgr.positions)
        exchange_positions = len(exchange.get_positions())
        if local_positions != exchange_positions:
            issues.append(f"Posiciones locales ({local_positions}) != exchange ({exchange_positions})")
    except Exception as e:
        issues.append(f"No se pudo verificar posiciones: {e}")

    # Verificar state.json reciente
    if os.path.exists(STATE_FILE):
        try:
            mtime = os.path.getmtime(STATE_FILE)
            age = time.time() - mtime
            if age > MAX_SILENCE_SECONDS:
                issues.append(f"state.json sin actualizar por {age:.0f}s")
        except Exception as e:
            issues.append(f"No se pudo verificar state.json: {e}")

    if issues:
        for msg in issues:
            print(f"[WATCHDOG] ANOMALY: {msg}", flush=True)
        print("[WATCHDOG] RECOVERY_ACTIVATED", flush=True)
    else:
        print("[WATCHDOG] OK", flush=True)
