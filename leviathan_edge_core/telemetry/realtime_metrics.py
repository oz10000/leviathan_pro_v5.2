import numpy as np

class RealtimeMetrics:
    def __init__(self):
        self.sharpe = 0.0
        self.sortino = 0.0
        self.calmar = 0.0
        self.maxdd = 0.0
        self.equity = []

    def update(self, equity_curve: list):
        self.equity = equity_curve
        if len(equity_curve) < 2:
            return
        rets = np.diff(equity_curve) / equity_curve[:-1]
        self.sharpe = np.mean(rets) / (np.std(rets) + 1e-10) * np.sqrt(365 * 24)
        neg_rets = rets[rets < 0]
        if len(neg_rets) > 0:
            self.sortino = np.mean(rets) / (np.std(neg_rets) + 1e-10) * np.sqrt(365 * 24)
        cummax = np.maximum.accumulate(equity_curve)
        dd = (equity_curve - cummax) / cummax
        self.maxdd = np.min(dd)
        if self.maxdd != 0:
            self.calmar = np.mean(rets) * (365 * 24) / abs(self.maxdd)

    def metrics_dict(self):
        return {
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "calmar": self.calmar,
            "maxdd": self.maxdd
        }
