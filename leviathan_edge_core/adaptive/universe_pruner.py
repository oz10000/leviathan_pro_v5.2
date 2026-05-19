from collections import defaultdict
import numpy as np

class UniversePruner:
    def __init__(self, min_trades=20, sharpe_threshold=3.0, winrate_threshold=0.60,
                 max_fake_breakout=0.15, entropy_limit=0.7):
        self.symbol_stats = defaultdict(lambda: {"trades":0,"wins":0,"pnls":[],"fake_breakouts":0,"entropy":[]})
        self.blacklist = set()
        self.min_trades = min_trades
        self.sharpe_threshold = sharpe_threshold
        self.winrate_threshold = winrate_threshold
        self.max_fake_breakout = max_fake_breakout
        self.entropy_limit = entropy_limit

    def update(self, symbol, pnl, fake_breakout=False, entropy=0.5, slippage_bps=0):
        stats = self.symbol_stats[symbol]
        stats["trades"] += 1
        stats["pnls"].append(pnl)
        if pnl > 0: stats["wins"] += 1
        if fake_breakout: stats["fake_breakouts"] += 1
        stats["entropy"].append(entropy)

    def evaluate_all(self):
        for sym, stats in self.symbol_stats.items():
            if stats["trades"] < self.min_trades: continue
            pnls = np.array(stats["pnls"])
            sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(len(pnls))
            winrate = stats["wins"] / stats["trades"]
            fake_rate = stats["fake_breakouts"] / stats["trades"]
            avg_entropy = np.mean(stats["entropy"])
            if (sharpe < self.sharpe_threshold or winrate < self.winrate_threshold or
                fake_rate > self.max_fake_breakout or avg_entropy > self.entropy_limit):
                self.blacklist.add(sym)

    def is_allowed(self, symbol):
        return symbol not in self.blacklist
