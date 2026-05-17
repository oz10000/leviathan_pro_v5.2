import numpy as np
from collections import deque
from config import Config

class ERAModule:
    def __init__(self):
        self.atr_hist = {}
        self.vol_hist = {}
        self.active = {}
        self.global_active = False

    def update(self, symbol: str, atr: float, vol: float):
        if symbol not in self.atr_hist:
            self.atr_hist[symbol] = deque(maxlen=100)
            self.vol_hist[symbol] = deque(maxlen=50)
            self.active[symbol] = False
        self.atr_hist[symbol].append(atr)
        self.vol_hist[symbol].append(vol)
        cond = 0
        if len(self.atr_hist[symbol]) >= 20:
            if atr > np.percentile(list(self.atr_hist[symbol]), Config.ERA_ATR_PERC):
                cond += 1
        if len(self.vol_hist[symbol]) >= 50:
            if vol > Config.ERA_VOL_MULT * np.mean(list(self.vol_hist[symbol])):
                cond += 1
        self.active[symbol] = (cond >= 2)
        self.global_active = any(self.active.values())

    def get_multipliers(self) -> dict:
        if not self.global_active:
            return {"leverage": 1.0, "capital": 1.0, "trail": 1.0}
        return {"leverage": Config.ERA_LEV_MULT, "capital": Config.ERA_CAPITAL_MULT, "trail": Config.ERA_TRAIL_MULT}
