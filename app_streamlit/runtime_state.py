import json
import os
import csv
from datetime import datetime

RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "runtime")
STATE_FILE = os.path.join(RUNTIME_DIR, "state.json")
TRADES_FILE = os.path.join(RUNTIME_DIR, "trades.csv")
LOGS_FILE = os.path.join(RUNTIME_DIR, "logs.txt")

os.makedirs(RUNTIME_DIR, exist_ok=True)

def init_state(initial_capital=100.0):
    if not os.path.exists(STATE_FILE):
        state = {
            "running": False,
            "mode": "simulator",
            "capital": initial_capital,
            "balance": initial_capital,
            "equity": initial_capital,
            "pnl": 0.0,
            "position": None,
            "signal": None,
            "loop_count": 0,
            "last_execution": "",
            "oscillators": {},
            "backtest_metrics": None,
            "live_metrics": None,
            "trades_count": 0,
            "leverage": 5,
            "auto_leverage": True,
            "start_time": None,
            "active_symbols": ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"],
            "equity_history": [initial_capital]
        }
        save_state(state)
    return load_state()

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return init_state()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_trade(trade):
    file_exists = os.path.isfile(TRADES_FILE)
    with open(TRADES_FILE, "a", newline="") as f:
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

def log_event(msg):
    with open(LOGS_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} – {msg}\n")
