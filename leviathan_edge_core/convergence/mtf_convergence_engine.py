class MTFConvergenceEngine:
    def __init__(self):
        self.tf_weights = {"1m": 0.15, "3m": 0.10, "5m": 0.25, "15m": 0.20, "30m": 0.15, "1h": 0.10, "4h": 0.05}

    def compute(self, tf_data: dict) -> float:
        if not tf_data:
            return 0.5
        trends = [d['trend'] for d in tf_data.values()]
        pos = sum(1 for t in trends if t > 0)
        neg = sum(1 for t in trends if t < 0)
        total = len(trends)
        agreement = max(pos, neg) / total if total > 0 else 0
        return agreement
