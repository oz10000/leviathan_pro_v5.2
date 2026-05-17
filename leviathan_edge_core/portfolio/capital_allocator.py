import numpy as np
from config import Config

class CapitalAllocator:
    def __init__(self, asset_scores: dict):
        self.scores = asset_scores

    def allocate(self, total_capital: float) -> dict:
        syms = list(self.scores.keys())
        if not syms:
            return {}
        raw = np.array([self.scores[s] for s in syms])
        exp_scores = np.exp(raw / Config.SOFTMAX_TEMP)
        probs = exp_scores / exp_scores.sum()
        allocs = {}
        for i, sym in enumerate(syms):
            allocs[sym] = min(probs[i], Config.MAX_ALLOCATION) * total_capital
        return allocs
