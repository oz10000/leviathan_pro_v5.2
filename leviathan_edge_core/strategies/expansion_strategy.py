import numpy as np
from strategies.base_strategy import BaseStrategy
from config import Config

class ExpansionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("expansion")
        self.threshold = Config.SCORE_THRESHOLD

    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction):
        score = row_5m["score"]
        fw = Config.FEATURE_WEIGHTS
        score += self._volume(row_5m) * fw["volume_impulse"]
        score += self._alignment(row_5m, row_15m) * fw["alignment_5m_15m"]
        score += self._macd(df_5m) * fw["macd_momentum"]
        score += self._trend(row_5m) * fw["trend_strength"]
        score += self._atr(df_5m) * fw["atr_expansion"]
        score += self._rsi(df_5m, direction) * fw["rsi_regime"]
        score += self._volreg(row_5m) * fw["volatility_regime"]
        return max(0.0, score)

    def should_enter(self, score, regime_state, era_active):
        if regime_state == "DEPRESSION":
            return False
        th = self.threshold + (5 if era_active else 0)
        return score >= th

    def _volume(self, row):
        vr = row.get("volume_ratio", 1)
        return 10 if vr > 2 else (5 if vr > 1.5 else (2 if vr > 1.2 else 0))
    def _alignment(self, r5, r15):
        return 5 if r5["trend"] == r15["trend"] and r5["trend"] in ("BULL", "BEAR") else -2
    def _macd(self, df):
        if "macd_hist" not in df.columns:
            return 0
        hist = df["macd_hist"]
        if len(hist) < 2:
            return 0
        return 3 if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2] else (1 if hist.iloc[-1] > 0 else 0)
    def _trend(self, row):
        sep = abs(row["ema20"] - row["ema50"]) / row["close"]
        return 3 if sep > 0.01 and row["slope_ema20"] > 0.001 else (1 if sep > 0.005 else 0)
    def _atr(self, df):
        atr_pct = df["atr_pct"].iloc[-1]
        avg = df["atr_pct"].iloc[-20:].mean()
        return 4 if 1.5 * avg < atr_pct < 0.05 else (-3 if atr_pct > 0.04 else 0)
    def _rsi(self, df, direction):
        rsi = df["rsi_14"].iloc[-1]
        return 2 if (direction == "LONG" and rsi > 55) or (direction == "SHORT" and rsi < 45) else 0
    def _volreg(self, row):
        atr_pct = row["atr_pct"]
        return 2 if 0.005 < atr_pct < 0.025 else (-2 if atr_pct > 0.04 else 0)
