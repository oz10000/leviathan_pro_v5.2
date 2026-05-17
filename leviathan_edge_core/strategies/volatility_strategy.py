from strategies.base_strategy import BaseStrategy

class VolatilityStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("volatility")
        self.threshold = 0.03

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        atr_pct = row_5m["atr_pct"]
        return atr_pct * 100

    def should_enter(self, score, regime_state, era_active):
        return score > self.threshold
