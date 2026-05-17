from strategies.base_strategy import BaseStrategy
from config import Config

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("momentum")
        self.threshold = Config.SCORE_THRESHOLD + 2

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        score = row_5m["score"]
        score += row_5m.get("momentum", 0) * 10
        return score

    def should_enter(self, score, regime_state, era_active):
        return score >= self.threshold
