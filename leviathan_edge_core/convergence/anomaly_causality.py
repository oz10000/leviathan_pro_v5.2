class AnomalyCausality:
    def analyze(self, features: dict) -> float:
        score = 0.0
        if features.get("divergence", 0) > 0.4:
            score += 0.3
        if features.get("entropy", 0) > 0.6:
            score += 0.25
        if features.get("mtf_convergence", 1) < 0.5:
            score += 0.2
        vol_ratio = features.get("volume_ratio", 1)
        if vol_ratio < 0.5 or vol_ratio > 3.0:
            score += 0.15
        atr_pct = features.get("atr_pct", 0.01)
        if atr_pct > 0.05:
            score += 0.1
        rsi = features.get("rsi", 50)
        if rsi < 25 or rsi > 75:
            score += 0.1
        macd_hist = features.get("macd_hist", 0)
        if (features.get("direction", 1) == 1 and macd_hist < -0.5) or (features.get("direction", 1) == -1 and macd_hist > 0.5):
            score += 0.15
        return min(score, 1.0)
