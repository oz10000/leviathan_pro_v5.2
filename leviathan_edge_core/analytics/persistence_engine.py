import numpy as np
from collections import deque

class PersistenceEngine:
    def __init__(self):
        self.expectancy_history = deque(maxlen=200)

    def update(self, expectancy: float):
        self.expectancy_history.append(expectancy)

    def persistence_score(self) -> float:
        if len(self.expectancy_history) < 30:
            return 0.5
        arr = np.array(self.expectancy_history)
        if np.std(arr) == 0:
            return 0.5
        ac1 = np.corrcoef(arr[:-1], arr[1:])[0, 1]
        return np.clip((ac1 + 1) / 2, 0.1, 1.0)
