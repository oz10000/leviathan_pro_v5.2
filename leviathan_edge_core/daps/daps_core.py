import numpy as np
from config import Config

class DAPSCore:
    def __init__(self):
        self.x = 0.0
        self.alpha = Config.DAPS_INIT_ALPHA
        self.beta = Config.DAPS_INIT_BETA
        self.gamma = Config.DAPS_INIT_GAMMA

    def step(self, epsilon: float, x_hat: float) -> float:
        total = self.alpha + self.beta + self.gamma
        if abs(total - 1.0) > 1e-9:
            self.alpha /= total
            self.beta /= total
            self.gamma /= total
        x_next = (self.alpha * (1.0 - 1.0 / Config.PI) * self.x +
                  self.beta * epsilon +
                  self.gamma * x_hat)
        self.x = x_next
        error = abs(self.x)
        self.beta = max(0.1, min(0.8, self.beta * (1.0 - Config.DAPS_DECAY) + 0.1 * error))
        self.gamma = max(0.1, min(0.8, self.gamma * (1.0 - Config.DAPS_DECAY) + 0.1 * (1.0 - error)))
        self.alpha = 1.0 - self.beta - self.gamma
        return self.x
        # Añadir al final del archivo daps_core.py:
class DAPSCore:
    def __init__(self):
        self.x = 0.0

    def step(self, epsilon, x_hat):
        self.x = 0.9 * self.x + 0.05 * epsilon + 0.02 * x_hat
