from collections import defaultdict
import numpy as np

class HourlyFilter:
    def __init__(self, min_trades=5):
        self.hour_pnl = defaultdict(list)
        self.min_trades = min_trades
        self.blocked_hours = set()

    def record(self, hour, pnl):
        self.hour_pnl[hour].append(pnl)

    def update_blocks(self, negative_threshold=-0.5, winrate_threshold=0.40):
        for hour, pnls in self.hour_pnl.items():
            if len(pnls) < self.min_trades: continue
            avg_pnl = np.mean(pnls)
            wr = sum(1 for p in pnls if p > 0) / len(pnls)
            if avg_pnl < negative_threshold or wr < winrate_threshold:
                self.blocked_hours.add(hour)

    def is_allowed(self, hour):
        return hour not in self.blocked_hours
