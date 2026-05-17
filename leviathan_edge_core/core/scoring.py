import pandas as pd
from core.feature_engine import compute_features

class BaseScorer:
    def __init__(self, tf_weights=None):
        self.tf_weights = tf_weights or {"1m": 0.12, "3m": 0.10, "5m": 0.25, "15m": 0.30,
                                         "30m": 0.10, "1h": 0.08, "4h": 0.05}
        self.freq_map = {"1m": "1T", "3m": "3T", "5m": "5T", "15m": "15T",
                         "30m": "30T", "1h": "1H", "4h": "4H"}

    def compute(self, df_1m: pd.DataFrame) -> float:
        total = 0.0
        for tf, w in self.tf_weights.items():
            freq = self.freq_map[tf]
            try:
                resampled = df_1m.resample(freq, on="ts").agg({
                    "open": "first", "high": "max", "low": "min",
                    "close": "last", "vol": "sum"
                }).dropna().reset_index()
                resampled = compute_features(resampled)
                if not resampled.empty and len(resampled) >= 10:
                    total += resampled["score"].iloc[-1] * w
            except Exception:
                pass
        return total
