import numpy as np

class DAPSEquilibrium:
    def __init__(self):
        self.equilibrium_score = 1.0

    def factor(self, x: float) -> float:
        proximity = 1.0 - np.clip(abs(x) / 2.0, 0.0, 1.0)
        self.equilibrium_score = 0.9 * self.equilibrium_score + 0.1 * proximity
        return self.equilibrium_score
