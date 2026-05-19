import numpy as np

class KellySizer:
    def __init__(self):
        self.trade_pnls = []

    def update(self, pnl_pct):
        self.trade_pnls.append(pnl_pct)

    def fraction(self):
        if len(self.trade_pnls) < 5:
            return 0.02
        wins = [x for x in self.trade_pnls[-20:] if x > 0]
        losses = [abs(x) for x in self.trade_pnls[-20:] if x <= 0]
        if not losses:
            return 0.04
        b = np.mean(wins) / np.mean(losses)
        p = len(wins) / len(self.trade_pnls[-20:])
        f = (b * p - (1 - p)) / b if b > 0 else 0.0
        return min(0.25 * f, 0.04)
