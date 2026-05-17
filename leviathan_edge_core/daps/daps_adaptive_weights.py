class DAPSAdaptiveWeights:
    def __init__(self):
        self.weights = {"expansion": 0.25, "pullback": 0.25, "reacceleration": 0.25, "depression_breakout": 0.25}
        self.tf_weights = {"1m": 0.12, "3m": 0.10, "5m": 0.25, "15m": 0.30, "30m": 0.10, "1h": 0.08, "4h": 0.05}

    def adapt(self, strategy_pnl: dict, daps_x: float):
        total = sum(strategy_pnl.values())
        if total > 0:
            for s in self.weights:
                self.weights[s] = strategy_pnl.get(s, 0) / total
        for s in self.weights:
            self.weights[s] = self.weights[s] * 0.8 + 0.2 * (1.0 - abs(daps_x))
        wsum = sum(self.weights.values())
        if wsum > 0:
            for s in self.weights:
                self.weights[s] /= wsum
