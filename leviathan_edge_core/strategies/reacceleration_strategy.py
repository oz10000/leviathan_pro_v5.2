from strategies.base_strategy import BaseStrategy
from config import Config

class ReaccelerationStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("reacceleration")
        self.threshold = Config.SCORE_THRESHOLD

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        score = row_5m["score"]
        fw = Config.FEATURE_WEIGHTS
        score += self._volume(row_5m) * fw["volume_impulse"]
        score += self._alignment(row_5m, row_15m) * fw["alignment_5m_15m"]
        score += self._macd_accel(df_5m) * fw["macd_momentum"]
        score += self._trend(row_5m) * fw["trend_strength"]
        score += self._atr(df_5m) * fw["atr_expansion"]
        score += self._rsi(row_5m, direction) * fw["rsi_regime"]
        score += self._volreg(row_5m) * fw["volatility_regime"]
        if row_5m["slope_ema20"] > 0.002:
            score += 3
        return max(0.0, score)

    def should_enter(self, score, regime_state, era_active):
        if regime_state == "DEPRESSION":
            return False
        return score >= (self.threshold + (5 if era_active else 0))

    def _volume(self, row):
        vr = row.get("volume_ratio", 1)
        return 9 if vr > 2.0 else (5 if vr > 1.5 else (1 if vr > 1.0 else 0))
    def _alignment(self, r5, r15):
        return 5 if r5["trend"] == r15["trend"] and r5["trend"] in ("BULL", "BEAR") else -2
    def _macd_accel(self, df):
        if "macd_hist" not in df.columns:
            return 0
        hist = df["macd_hist"]
        if len(hist) >= 3:
            accel = hist.iloc[-1] - 2 * hist.iloc[-2] + hist.iloc[-3]
            if accel > 0 and hist.iloc[-1] > 0:
                return 4
            if accel > 0:
                return 2
        return 1 if hist.iloc[-1] > 0 else 0
    def _trend(self, row):
        sep = abs(row["ema20"] - row["ema50"]) / row["close"]
        return 3 if sep > 0.012 and row["slope_ema20"] > 0.002 else (1 if sep > 0.006 else 0)
    def _atr(self, df):
        atr_pct = df["atr_pct"].iloc[-1]
        avg = df["atr_pct"].iloc[-20:].mean()
        return 3 if 1.4 * avg < atr_pct < 0.045 else (-2 if atr_pct > 0.045 else 0)
    def _rsi(self, row, direction):
        return 1 if (direction == "LONG" and row["momentum_score"] > 60) or (direction == "SHORT" and row["momentum_score"] < 40) else 0
    def _volreg(self, row):
        atr_pct = row["atr_pct"]
        return 2 if 0.006 < atr_pct < 0.028 else (-1 if atr_pct > 0.04 else 0)
