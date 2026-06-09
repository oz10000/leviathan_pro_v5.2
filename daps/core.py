import numpy as np
from config import Config

class DAPSEngine:
    def __init__(self, decay_lambda=None):
        self.decay_lambda = decay_lambda if decay_lambda is not None else Config.DAPS_DECAY_LAMBDA
        self.symbol_stats = {}
        self.regime = "neutral"

    def step(self, symbol, closes, signal_quality=0.5):
        if symbol not in self.symbol_stats:
            self.symbol_stats[symbol] = {'mean': 0.0, 'variance': 1.0, 'x': 0.0, 'n': 0}
        stats = self.symbol_stats[symbol]
        if len(closes) < 20:
            return 0.5

        short_window = closes[-5:]
        long_window = closes[-20:]
        anomaly = np.std(short_window) / (np.std(long_window) + 1e-8) - 1.0
        expectation = (closes[-1] - long_window[0]) / (long_window[0] + 1e-8)

        lam = self.decay_lambda
        old_mean = stats['mean']
        old_variance = stats['variance']
        stats['mean'] = lam * old_mean + (1 - lam) * anomaly
        stats['variance'] = lam * old_variance + (1 - lam) * (anomaly - old_mean) ** 2

        alpha, beta, gamma = 0.1, 0.05, 0.02
        stats['x'] = (1 - alpha) * stats['x'] + beta * anomaly + gamma * expectation
        omega = max(0.0, min(1.0, 0.5 - stats['x'] * 10))
        return omega

    def get_state(self, symbol):
        stats = self.symbol_stats.get(symbol)
        if not stats:
            return None
        return {k: v for k, v in stats.items()}

    def set_state(self, symbol, state):
        self.symbol_stats[symbol] = state.copy()
