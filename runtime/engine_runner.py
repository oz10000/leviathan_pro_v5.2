#!/usr/bin/env python3
"""
Leviathan Engine Runner – Workflow Persistent Loop.
"""
import sys, os, time, json, signal, logging
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine.leviathan_engine import LeviathanEngine
from adapters.testnet_adapter import TestnetAdapter
from adapters.live_adapter import LiveAdapter
from portfolio.testnet_assets import fetch_testnet_symbols

RUNTIME_DIR = REPO_ROOT / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)
LOG_FILE = RUNTIME_DIR / "logs" / "engine.log"
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

STATE_FILE = RUNTIME_DIR / "state.json"
TRADES_FILE = RUNTIME_DIR / "trades.csv"
STOP_FILE = RUNTIME_DIR / "stop.txt"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

def save_state(engine):
    snap = engine.get_snapshot()
    # Exclude large lists for JSON size
    snap.pop("trades", None)
    snap.pop("equity_history", None)   # we'll keep it in separate file if needed
    with open(STATE_FILE, 'w') as f:
        json.dump(snap, f, indent=2)

def append_trades(trades, since_index):
    write_header = not TRADES_FILE.exists()
    with open(TRADES_FILE, 'a', newline='') as f:
        import csv
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["time","symbol","strategy","direction","entry","exit","pnl","reason"])
        for t in trades[since_index:]:
            writer.writerow([
                t.get("time",""), t.get("symbol",""), t.get("strategy",""),
                t.get("direction",""), t.get("entry",0), t.get("exit_price",0),
                t.get("pnl",0), t.get("reason","")
            ])

def should_stop():
    return STOP_FILE.exists()

def main():
    mode = os.getenv("LEVIATHAN_MODE", "testnet")
    use_live = (mode == "live")
    symbols = os.getenv("LEVIATHAN_SYMBOLS", "").split(",") if not use_live else None

    if use_live:
        # Live: top 100 by volume
        from portfolio.top100_selector import fetch_top100_symbols
        symbols = fetch_top100_symbols()
        adapter = LiveAdapter(
            os.getenv("OKX_API_KEY",""),
            os.getenv("OKX_SECRET_KEY",""),
            os.getenv("OKX_PASSPHRASE",""),
            symbols
        )
    else:
        if not symbols or symbols == [""]:
            symbols = fetch_testnet_symbols()  # auto-discover testnet assets
        adapter = TestnetAdapter(
            os.getenv("OKX_API_KEY",""),
            os.getenv("OKX_SECRET_KEY",""),
            os.getenv("OKX_PASSPHRASE",""),
            symbols
        )

    engine = adapter.engine
    state = load_state()
    if state:
        engine.state.update({
            "balance": state.get("balance", 100.0),
            "equity": state.get("equity", 100.0),
            "pnl": state.get("pnl", 0.0),
            "loop_count": state.get("loop_count", 0),
            "position": state.get("position"),
            "signal": state.get("signal"),
            "last_execution": state.get("last_execution", "")
        })
        # Equity history can be reloaded from file if saved separately; omitted for brevity

    logging.info(f"Engine started in {mode} mode with {len(symbols)} symbols")

    # Graceful shutdown on signals
    def graceful_shutdown(sig, frame):
        save_state(engine)
        logging.info("Shutdown signal received")
        sys.exit(0)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)

    trades_index = len(engine.state.get("trades", []))
    cycle_count = 0
    max_cycles = int(os.getenv("MAX_CYCLES", "500"))  # safety limit for Workflow
    interval = int(os.getenv("CYCLE_INTERVAL", "30"))

    while cycle_count < max_cycles and not should_stop():
        try:
            snapshot = adapter.run_cycle()
            engine.state["loop_count"] = cycle_count + 1
            save_state(engine)

            new_trades = engine.state["trades"]
            if len(new_trades) > trades_index:
                append_trades(new_trades, trades_index)
                trades_index = len(new_trades)

            logging.info(f"Cycle {engine.state['loop_count']} | Balance: {snapshot['balance']:.2f} | "
                         f"Position: {snapshot.get('position')}")
            cycle_count += 1
        except Exception as e:
            logging.error(f"Cycle error: {e}", exc_info=True)

        time.sleep(interval)

    # Final save before exit
    save_state(engine)
    if should_stop():
        logging.info("Stop file detected, exiting.")
        STOP_FILE.unlink()

if __name__ == "__main__":
    main()
