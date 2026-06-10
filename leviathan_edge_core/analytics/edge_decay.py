import numpy as np

class EdgeDecay:
    """
    Modela la degradación temporal del Edge.
    Si el Profit Factor reciente cae por debajo de un umbral, el Edge se considera en decadencia.
    """
    def __init__(self, window=50, threshold=1.1):
        self.window = window
        self.threshold = threshold
        self.recent_pnl = []

    def update(self, pnl):
        self.recent_pnl.append(pnl)
        if len(self.recent_pnl) > self.window:
            self.recent_pnl.pop(0)

    def is_decaying(self):
        if len(self.recent_pnl) < 10:
            return False
        wins = [p for p in self.recent_pnl if p > 0]
        losses = [abs(p) for p in self.recent_pnl if p <= 0]
        if sum(losses) == 0:
            return False
        pf = sum(wins) / sum(losses)
        return pf < self.threshold
