import numpy as np
from config import Config

class AdaptiveCapitalAllocator:
    def __init__(self, daps_core, persistence_engine, exec_quality, asset_scores):
        self.daps = daps_core
        self.persistence = persistence_engine
        self.exec_qual = exec_quality
        self.asset_scores = asset_scores

    def allocate(self, total_capital: float) -> dict:
        syms = list(self.asset_scores.keys())
        if not syms:
            return {}
        raw = np.array([self.asset_scores[s] for s in syms])
        eq_factor = 1.0 + 0.5 * (1.0 - abs(self.daps.x))
        modifier = eq_factor * self.persistence.persistence_score() * self.exec_qual.quality_score()
        raw *= modifier
        exp_scores = np.exp(raw / Config.SOFTMAX_TEMP)
        probs = exp_scores / exp_scores.sum()
        allocs = {}
        for i, sym in enumerate(syms):
            allocs[sym] = min(probs[i], Config.MAX_ALLOCATION) * total_capital
        return allocs
