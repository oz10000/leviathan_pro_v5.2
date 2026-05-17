class LeverageSafetyEngine:
    def __init__(self):
        self.base_leverage = 5.0

    def safe_leverage(self, sharpe_roll: float, mtf_conv: float, divergence: float, drawdown: float,
                      entropy: float) -> float:
        score = (sharpe_roll / 7.0) * mtf_conv * (1 - divergence) * (1 - drawdown) * (1 - entropy)
        return max(1.5, min(8.0, score * 8.0))
