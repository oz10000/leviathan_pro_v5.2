from strategies.base_strategy import BaseStrategy
from config import Config

class PullbackStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("pullback")
        self.threshold = Config.SCORE_THRESHOLD

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        score = row_5m["score"]
        fw = Config.FEATURE_WEIGHTS
        score += self._volume(row_5m) * fw["volume_impulse"] * 0.8
        score += self._alignment(row_5m, row_15m) * fw["alignment_5m_15m"]
        score += self._macd(df_5m, direction) * fw["macd_momentum"]
        score += self._trend(row_5m) * fw["trend_strength"]
        score += self._atr(df_5m) * fw["atr_expansion"]
        score += self._rsi(df_5m, direction) * fw["rsi_regime"]
        score += self._volreg(row_5m) * fw["volatility_regime"]
        atr = row_5m.get("atr", row_5m["close"] * 0.01)
        if abs(row_5m["close"] - row_5m["ema20"]) < 0.5 * atr:
            score += 3
        return max(0.0, score)

    def should_enter(self, score, regime_state, era_active):
        if regime_state == "DEPRESSION":
            return False
        return score >= (self.threshold + (5 if era_active else 0))

    def _volume(self, row):
        vr = row.get("volume_ratio", 1)
        return 8 if vr > 1.5 else (4 if vr > 1.2 else 0)
    def _alignment(self, r5, r15):
        return 5 if r5["trend"] == r15["trend"] and r5["trend"] in ("BULL", "BEAR") else -2
    def _macd(self, df, direction):
        if "macd_hist" not in df.columns:
            return 0
        hist = df["macd_hist"]
        if len(hist) < 2:
            return 0
        if abs(hist.iloc[-1]) < abs(hist.iloc[-2]):
            return 2
        return 1 if (direction == "LONG" and hist.iloc[-1] > -0.5) or (direction == "SHORT" and hist.iloc[-1] < 0.5) else 0
    def _trend(self, row):
        sep = abs(row["ema20"] - row["ema50"]) / row["close"]
        return 3 if sep > 0.008 and row["slope_ema20"] > 0.0005 else (1 if sep > 0.004 else 0)
    def _atr(self, df):
        atr_pct = df["atr_pct"].iloc[-1]
        avg = df["atr_pct"].iloc[-20:].mean()
        return 3 if 1.3 * avg < atr_pct < 0.04 else (-2 if atr_pct > 0.04 else 0)
    def _rsi(self, df, direction):
        rsi = df["rsi_14"].iloc[-1]
        return 2 if 40 < rsi < 60 else 0
    def _volreg(self, row):
        atr_pct = row["atr_pct"]
        return 2 if 0.004 < atr_pct < 0.020 else (-1 if atr_pct > 0.035 else 0)
