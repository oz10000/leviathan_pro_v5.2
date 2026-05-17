import numpy as np
from collections import deque

class EdgeDecay:
    def __init__(self, window=50):
        self.expectancy_ema = None
        self.history = deque(maxlen=window)
        self.alpha = 0.1

    def update(self, expectancy: float):
        self.history.append(expectancy)
        if self.expectancy_ema is None:
            self.expectancy_ema = expectancy
        else:
            self.expectancy_ema = self.alpha * expectancy + (1 - self.alpha) * self.expectancy_ema

    def decay_factor(self) -> float:
        if len(self.history) < 5:
            return 1.0
        recent = np.mean(list(self.history)[-10:]) if len(self.history) >= 10 else np.mean(list(self.history))
        return np.clip(recent / (self.expectancy_ema + 1e-8), 0.3, 1.5)
