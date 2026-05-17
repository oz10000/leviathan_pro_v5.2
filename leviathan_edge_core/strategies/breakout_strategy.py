from strategies.base_strategy import BaseStrategy

class BreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("breakout")
        self.threshold = 0.8

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        if direction == "LONG":
            recent_high = df_5m["high"].rolling(10).max().iloc[-1]
            if row_5m["close"] > recent_high:
                return 80
        else:
            recent_low = df_5m["low"].rolling(10).min().iloc[-1]
            if row_5m["close"] < recent_low:
                return 80
        return 0

    def should_enter(self, score, regime_state, era_active):
        return score >= 70
