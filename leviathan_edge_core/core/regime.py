import numpy as np
from collections import deque

class RegimeDetector:
    def __init__(self, temp=0.5, alpha=0.2):
        self.temp = temp
        self.alpha = alpha
        self.atr_history = deque(maxlen=100)
        self.probs = {"trend": 0.33, "mean_reversion": 0.34, "high_vol_chop": 0.33}

    def update(self, atr_pct: float, slope_ema20: float) -> dict:
        self.atr_history.append(atr_pct)
        if len(self.atr_history) < 50:
            return self.probs
        p80 = np.percentile(list(self.atr_history), 80)
        trend_lik = 1.0 / (1.0 + np.exp(-(abs(slope_ema20) - 0.002) * 500))
        mr_lik = max(0, 1.0 - abs(slope_ema20) * 200)
        chop_lik = atr_pct / p80 if p80 > 0 else 0.0
        raw = np.array([trend_lik, mr_lik, chop_lik])
        exp_raw = np.exp(raw / self.temp)
        probs_raw = exp_raw / exp_raw.sum()
        new_probs = {"trend": probs_raw[0], "mean_reversion": probs_raw[1], "high_vol_chop": probs_raw[2]}
        for k in self.probs:
            self.probs[k] = self.alpha * new_probs[k] + (1 - self.alpha) * self.probs[k]
        return self.probs
