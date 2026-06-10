import numpy as np

class PerformanceTracker:
    """
    Rastrea el rendimiento en tiempo real: Sharpe, Sortino, drawdown, etc.
    """
    def __init__(self, window=25):
        self.window = window
        self.equity_curve = []
        self.pnl_history = []

    def add_equity_snapshot(self, capital):
        self.equity_curve.append(capital)

    def add_trade(self, pnl):
        self.pnl_history.append(pnl)
        if len(self.pnl_history) > self.window * 4:
            self.pnl_history.pop(0)

    def realtime_sharpe(self):
        if len(self.pnl_history) < 5:
            return 0.0
        returns = self.pnl_history[-self.window:]
        if np.std(returns) == 0:
            return 0.0
        return (np.mean(returns) / np.std(returns)) * np.sqrt(252)

    def current_drawdown(self):
        if len(self.equity_curve) < 2:
            return 0.0
        peak = max(self.equity_curve)
        current = self.equity_curve[-1]
        return (peak - current) / peak if peak > 0 else 0.0
