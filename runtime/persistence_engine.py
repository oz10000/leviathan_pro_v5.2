import json, os, hashlib, time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = RUNTIME_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)
LATEST_PTR = RUNTIME_DIR / "latest_pointer.json"

class PersistenceEngine:
    def save_snapshot(self, engine, pos_mgr):
        snap = {
            "balance": engine.capital,
            "peak_capital": engine.peak_capital,
            "equity": engine.capital,
            "pnl": engine.capital - 100.0,
            "position": engine.position,
            "loop_count": getattr(engine, '_loop_count', 0),
            "equity_history": engine.equity_curve,
            "active_symbols": engine.universe,
            "trades_count": len(pos_mgr.trade_history) if pos_mgr else 0,
            "timestamp": time.time()
        }
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snap_name = f"snap_{timestamp}_{hashlib.md5(json.dumps(snap).encode()).hexdigest()[:8]}.json"
        temp_file = SNAPSHOT_DIR / f".{snap_name}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(snap, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp_file.rename(SNAPSHOT_DIR / snap_name)
        with open(LATEST_PTR, 'w') as f:
            json.dump({"latest": snap_name, "timestamp": snap["timestamp"]}, f)

    def load_latest_snapshot(self):
        if not LATEST_PTR.exists():
            return None
        with open(LATEST_PTR) as f:
            ptr = json.load(f)
        snap_file = SNAPSHOT_DIR / ptr["latest"]
        if snap_file.exists():
            with open(snap_file) as f:
                return json.load(f)
        return None

    def validate(self, snap):
        required = ["balance", "equity", "loop_count", "timestamp"]
        return all(k in snap for k in required)
