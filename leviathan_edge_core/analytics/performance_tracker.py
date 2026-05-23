import numpy as np
from collections import deque

class PerformanceTracker:
    """
    Calcula el Sharpe ratio rodante basado en snapshots de equity.
    Ventana configurable, solo usa datos pasados.
    """

    def __init__(self, window: int = 25):
        self.window = window
        self.equity_snapshots = deque(maxlen=window + 1)

    def add_equity_snapshot(self, equity: float):
        self.equity_snapshots.append(equity)

    def realtime_sharpe(self) -> float:
        if len(self.equity_snapshots) < 2:
            return 0.0
        eq = np.array(self.equity_snapshots)
        returns = np.diff(eq) / (eq[:-1] + 1e-8)
        if len(returns) < 2:
            return 0.0
        sharpe = np.sqrt(252) * returns.mean() / (returns.std() + 1e-8)
        return float(np.clip(sharpe, -3.0, 6.0))
