from collections import defaultdict

class LossReasonEngine:
    def __init__(self):
        self.reasons = defaultdict(list)

    def log_trade(self, pnl: float, features: dict):
        if pnl < 0:
            cause = "unknown"
            if features.get("divergence", 0) > 0.5:
                cause = "divergence"
            elif features.get("entropy", 0) > 0.7:
                cause = "high_entropy"
            elif features.get("mtf_convergence", 1) < 0.6:
                cause = "mtf_conflict"
            self.reasons[cause].append(pnl)

    def report(self):
        return {k: len(v) for k, v in self.reasons.items()}
