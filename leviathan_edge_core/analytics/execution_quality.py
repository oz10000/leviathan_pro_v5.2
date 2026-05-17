import numpy as np
from collections import deque

class ExecutionQuality:
    def __init__(self):
        self.slippages = deque(maxlen=200)
        self.latency_ms = deque(maxlen=200)
        self.fills = 0
        self.attempts = 0

    def record(self, slippage_bps: float, latency_ms: float, filled: bool):
        self.slippages.append(abs(slippage_bps))
        self.latency_ms.append(latency_ms)
        if filled:
            self.fills += 1
        self.attempts += 1

    def quality_score(self) -> float:
        fill_rate = self.fills / max(1, self.attempts)
        avg_slip = np.mean(self.slippages) if self.slippages else 0
        avg_lat = np.mean(self.latency_ms) if self.latency_ms else 0
        slip_score = max(0, 1 - avg_slip / 10.0)
        lat_score = max(0, 1 - avg_lat / 200.0)
        return 0.5 * fill_rate + 0.3 * slip_score + 0.2 * lat_score
