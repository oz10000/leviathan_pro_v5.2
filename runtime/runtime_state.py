import json, os, csv
from datetime import datetime

RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "runtime")
STATE_FILE = os.path.join(RUNTIME_DIR, "state.json")
TRADES_FILE = os.path.join(RUNTIME_DIR, "trades.csv")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def log_trade(trade):
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    file_exists = os.path.isfile(TRADES_FILE)
    with open(TRADES_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["time", "symbol", "strategy", "direction", "entry", "exit", "pnl", "reason"])
        writer.writerow([
            trade.get("time", datetime.now().isoformat()),
            trade.get("symbol", ""),
            trade.get("strategy", ""),
            trade.get("direction", ""),
            trade.get("entry", 0),
            trade.get("exit_price", 0),
            trade.get("pnl", 0),
            trade.get("reason", "")
        ])
