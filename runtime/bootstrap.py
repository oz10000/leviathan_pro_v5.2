from runtime.persistence_engine import PersistenceEngine

def bootstrap_runtime():
    pers = PersistenceEngine()
    snap = pers.load_latest_snapshot()
    if snap and pers.validate(snap):
        return snap
    return {
        "balance": 100.0,
        "equity": 100.0,
        "peak_capital": 100.0,
        "loop_count": 0,
        "equity_history": [100.0],
        "position": None,
        "symbols": None
    }
