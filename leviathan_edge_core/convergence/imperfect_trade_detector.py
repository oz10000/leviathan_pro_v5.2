from config import Config

class ImperfectTradeDetector:
    def __init__(self):
        self.threshold = Config.TRADE_QUALITY_MIN_SCORE

    def is_defective(self, meta_score: float, divergence: float, entropy: float, mtf_conv: float) -> bool:
        quality = meta_score * (1 - divergence) * (1 - entropy) * mtf_conv
        return quality < self.threshold
