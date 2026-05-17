from strategies.base_strategy import BaseStrategy
from config import Config

class DepressionBreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("depression_breakout")
        self.threshold = Config.SCORE_THRESHOLD - 3
        self._was_depression = False

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        score = row_5m["score"]
        fw = Config.FEATURE_WEIGHTS
        score += self._volume(row_5m) * fw["volume_impulse"] * 1.2
        score += self._alignment(row_5m, row_15m) * fw["alignment_5m_15m"]
        score += self._atr_breakout(df_5m) * fw["atr_expansion"] * 1.5
        score += self._trend(row_5m) * fw["trend_strength"]
        score += self._volreg(row_5m) * fw["volatility_regime"]
        return max(0.0, score)

    def should_enter(self, score, regime_state, era_active):
        if regime_state == "DEPRESSION":
            self._was_depression = True
            return False
        if self._was_depression and regime_state in ("EXPANSION", "COMPRESSION"):
            self._was_depression = False
            return score >= (self.threshold + (5 if era_active else 0))
        self._was_depression = False
        return False

    def _volume(self, row):
        vr = row.get("volume_ratio", 1)
        return 12 if vr > 2.5 else (7 if vr > 2.0 else (3 if vr > 1.5 else 0))
    def _alignment(self, r5, r15):
        return 5 if r5["trend"] == r15["trend"] and r5["trend"] in ("BULL", "BEAR") else -2
    def _atr_breakout(self, df):
        atr_pct = df["atr_pct"].iloc[-1]
        avg = df["atr_pct"].iloc[-20:].mean()
        return 6 if atr_pct > 2.0 * avg and atr_pct < 0.05 else (3 if atr_pct > 1.5 * avg else (-1 if atr_pct < 0.003 else 0))
    def _trend(self, row):
        sep = abs(row["ema20"] - row["ema50"]) / row["close"]
        return 2 if sep > 0.005 and row["slope_ema20"] > 0.001 else 0
    def _volreg(self, row):
        atr_pct = row["atr_pct"]
        return 3 if 0.008 < atr_pct < 0.030 else 0
