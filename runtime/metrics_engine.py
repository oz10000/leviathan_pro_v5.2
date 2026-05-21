import json, numpy as np
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
TRADES_FILE = RUNTIME_DIR / "trades.csv"
METRICS_OUTPUT = RUNTIME_DIR / "metrics.json"

def compute():
    if not TRADES_FILE.exists():
        return
    import pandas as pd
    trades = pd.read_csv(TRADES_FILE)
    if trades.empty:
        return
    pnls = trades["pnl"].values
    wins = pnls[pnls > 0]; losses = pnls[pnls <= 0]
    winrate = len(wins) / len(pnls)
    profit_factor = sum(wins) / abs(sum(losses)) if sum(losses) != 0 else float('inf')
    avg_win = np.mean(wins) if len(wins) else 0
    avg_loss = np.mean(losses) if len(losses) else 0
    expectancy = winrate * avg_win - (1 - winrate) * abs(avg_loss)
    equity = 100 + np.cumsum(pnls)
    rets = np.diff(equity) / equity[:-1]
    sharpe = np.mean(rets) / np.std(rets) * np.sqrt(365 * 24) if len(rets) > 1 else 0
    maxdd = (np.maximum.accumulate(equity) - equity).max() / np.maximum.accumulate(equity).max()
    metrics = {
        "trades": len(pnls),
        "winrate": winrate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "sharpe": sharpe,
        "maxdd": maxdd
    }
    with open(METRICS_OUTPUT, 'w') as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    compute()
