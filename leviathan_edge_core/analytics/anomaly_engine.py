import numpy as np
from collections import deque

class AnomalyEngine:
    def __init__(self):
        self.pnl_hist = deque(maxlen=200)
        self.score_hist = deque(maxlen=200)

    def feed(self, pnl: float, score: float):
        self.pnl_hist.append(pnl)
        self.score_hist.append(score)

    def anomaly_score(self) -> float:
        if len(self.pnl_hist) < 20:
            return 0.0
        pnl_arr = np.array(self.pnl_hist)
        z = (pnl_arr[-1] - np.mean(pnl_arr)) / (np.std(pnl_arr) + 1e-8)
        return np.clip(abs(z) / 3.0, 0, 1)
