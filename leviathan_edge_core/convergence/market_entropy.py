import numpy as np

class MarketEntropy:
    def shannon_entropy(self, close_prices: np.ndarray, bins=10) -> float:
        if len(close_prices) < 2:
            return 0.0
        rets = np.diff(close_prices) / close_prices[:-1]
        hist, _ = np.histogram(rets, bins=bins, density=True)
        hist = hist[hist > 0]
        entropy = -np.sum(hist * np.log2(hist))
        max_entropy = np.log2(bins)
        return entropy / max_entropy if max_entropy > 0 else 0.0
