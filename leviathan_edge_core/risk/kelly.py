import numpy as np
from config import Config

class KellySizer:
    def __init__(self):
        self.trade_pnls = []

    def update(self, pnl_pct: float):
        self.trade_pnls.append(pnl_pct)

    def fraction(self, sharpe: float = None) -> float:
        if len(self.trade_pnls) < 5:
            base_risk = Config.RISK_CAP * 0.5
        else:
            wins = [x for x in self.trade_pnls[-20:] if x > 0]
            losses = [abs(x) for x in self.trade_pnls[-20:] if x <= 0]
            if not losses:
                base_risk = Config.RISK_CAP
            else:
                b = np.mean(wins) / np.mean(losses)
                p = len(wins) / len(self.trade_pnls[-20:])
                f = (b * p - (1 - p)) / b if b > 0 else 0.0
                base_risk = Config.KELLY_FRACTION * f

        # Safe-risk dinámico basado en Sharpe rodante
        safe_factor = 1.0
        if sharpe is not None:
            if sharpe < 0.5:
                safe_factor = 0.35
            elif sharpe < 1.0:
                safe_factor = 0.55
            elif sharpe < 1.5:
                safe_factor = 0.75
        return min(base_risk * safe_factor, Config.RISK_CAP)
