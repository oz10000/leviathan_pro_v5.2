from collections import deque
import numpy as np

class TemporalProfiler:
    def __init__(self):
        self.tf_perf = {tf: deque(maxlen=200) for tf in ["1m", "3m", "5m", "15m", "30m", "1h", "4h"]}
        self.tf_weights = {"1m": 0.12, "3m": 0.10, "5m": 0.25, "15m": 0.30, "30m": 0.10, "1h": 0.08, "4h": 0.05}

    def update_tf_pnl(self, tf_scores: dict, final_pnl: float):
        for tf, score in tf_scores.items():
            if tf in self.tf_perf:
                self.tf_perf[tf].append(score if final_pnl > 0 else -score)

    def adaptive_weights(self) -> dict:
        mean_perf = {tf: np.mean(list(self.tf_perf[tf])) if self.tf_perf[tf] else 0.0 for tf in self.tf_weights}
        total = sum(max(v, 0) for v in mean_perf.values())
        if total <= 0:
            return self.tf_weights
        new_w = {tf: max(v, 0) / total for tf, v in mean_perf.items()}
        blended = {tf: 0.7 * new_w[tf] + 0.3 * self.tf_weights[tf] for tf in self.tf_weights}
        wsum = sum(blended.values())
        return {tf: v / wsum for tf, v in blended.items()}
