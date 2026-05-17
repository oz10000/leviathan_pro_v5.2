import numpy as np

class FractalConfirmation:
    def check(self, df_5m, df_1h) -> float:
        if df_5m is None or df_1h is None or len(df_5m) < 5 or len(df_1h) < 5:
            return 0.5
        slope5 = df_5m['close'].pct_change(5).iloc[-1]
        slope1h = df_1h['close'].pct_change(2).iloc[-1]
        if np.sign(slope5) == np.sign(slope1h):
            return 0.9
        return 0.2
