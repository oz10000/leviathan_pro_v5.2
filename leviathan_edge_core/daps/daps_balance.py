import numpy as np
from collections import deque

class DAPSBalance:
    def __init__(self):
        self.history = deque(maxlen=200)
        self.balance = 1.0

    def update(self, daps_x: float):
        self.history.append(daps_x)
        if len(self.history) > 20:
            mean_abs = np.mean(np.abs(list(self.history)))
            self.balance = np.clip(1.0 - mean_abs * 2.0, 0.5, 1.5)
        return self.balance
