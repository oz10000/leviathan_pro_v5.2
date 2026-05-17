import numpy as np

class VolatilityRisk:
    def current_volatility(self, prices, window=20):
        if len(prices) < window:
            return 0.01
        returns = np.diff(prices[-window:]) / prices[-window:-1]
        return np.std(returns)
