import numpy as np
from collections import deque

class ExpectancyEngine:
    def __init__(self, window=100):
        self.wins = deque(maxlen=window)
        self.losses = deque(maxlen=window)

    def add(self, pnl: float):
        if pnl > 0:
            self.wins.append(pnl)
        else:
            self.losses.append(abs(pnl))

    def compute(self):
        wins = list(self.wins)
        losses = list(self.losses)
        if not wins and not losses:
            return 0.0
        pw = len(wins) / (len(wins) + len(losses))
        pl = 1 - pw
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        return pw * avg_win - pl * avg_loss
