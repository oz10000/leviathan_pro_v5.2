#!/usr/bin/env python3
"""
LEVIATHAN ENGINE RUNNER – Proceso persistente independiente de Streamlit.
Ejecuta el Edge Core en loop infinito, guardando estado en runtime/state.json.
Soporta modos: simulator, testnet, live.
"""
import sys, os, time, traceback, json, signal
from pathlib import Path

# Añadir Edge Core al path (carpeta paralela)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
EDGE_CORE = REPO_ROOT / "leviathan_edge_core"
if str(EDGE_CORE) not in sys.path:
    sys.path.insert(0, str(EDGE_CORE))

from config import Config
from runtime_state import init_state, load_state, save_state, log_trade, log_event
from core_adapter import CoreAdapter

# Configuración del ciclo
CYCLE_INTERVAL = 30          # segundos entre ciclos (modo live/testnet)
SIMULATION_INTERVAL = 5      # segundos para modo simulator
MAX_CONSECUTIVE_ERRORS = 10  # entrar en safe mode tras N errores seguidos

def main():
    state = init_state(Config.INITIAL_CAPITAL)
    if not state.get("start_time"):
        state["start_time"] = time.time()
        save_state(state)

    mode = state.get("mode", "simulator")
    adapter = CoreAdapter(mode=mode, initial_capital=state["balance"])
    adapter.state["balance"] = state["balance"]
    adapter.state["equity"] = state["equity"]
    adapter.state["pnl"] = state["pnl"]
    adapter.state["loop_count"] = state["loop_count"]
    adapter.symbols = state.get("active_symbols", ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"])

    log_event(f"Engine started in {mode} mode")

    consecutive_errors = 0
    interval = SIMULATION_INTERVAL if mode == "simulator" else CYCLE_INTERVAL

    while True:
        # Leer estado actualizado (por si Streamlit cambió configuración)
        state = load_state()
        if not state.get("running", False):
            save_state(state)
            log_event("Engine stopped by user")
            break

        # Actualizar modo si cambió
        new_mode = state.get("mode", "simulator")
        if new_mode != adapter.mode:
            adapter.mode = new_mode
            interval = SIMULATION_INTERVAL if new_mode == "simulator" else CYCLE_INTERVAL
            log_event(f"Mode changed to {new_mode}")

        # Sincronizar lista de activos
        adapter.symbols = state.get("active_symbols", adapter.symbols[:6])

        try:
            # Ejecutar un ciclo
            snapshot = adapter.run_cycle(
                leverage=state.get("leverage") if not state.get("auto_leverage", True) else None
            )

            # Actualizar estado con los resultados del adaptador
            state["balance"] = adapter.state["balance"]
            state["equity"] = adapter.state["equity"]
            state["pnl"] = adapter.state["pnl"]
            state["position"] = adapter.state["position"]
            state["signal"] = adapter.state["signal"]
            state["loop_count"] = adapter.state["loop_count"]
            state["last_execution"] = adapter.state.get("last_execution", "")
            state["oscillators"] = adapter.state.get("oscillators", {})
            state["equity_history"] = adapter.state.get("equity_history", [state["balance"]])

            # Guardar trades nuevos
            new_trades = adapter.state.get("trades", [])[state.get("trades_count", 0):]
            for trade in new_trades:
                log_trade(trade)
            state["trades_count"] = len(adapter.state.get("trades", []))

            save_state(state)
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            log_event(f"Cycle error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {traceback.format_exc()}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                log_event("Entering safe mode – reducing interval and limiting symbols")
                interval = 60
                adapter.symbols = ["BTC", "ETH"]
            time.sleep(5)

        time.sleep(interval)

if __name__ == "__main__":
    # Manejar señales para cierre limpio
    def graceful_shutdown(sig, frame):
        state = load_state()
        state["running"] = False
        save_state(state)
        log_event("Received shutdown signal")
        sys.exit(0)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
    main()
