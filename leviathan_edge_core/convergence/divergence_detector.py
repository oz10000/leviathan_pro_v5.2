import numpy as np

class DivergenceDetector:
    def compute(self, price: np.ndarray, volume: np.ndarray, rsi: np.ndarray, macd_hist: np.ndarray) -> float:
        div_score = 0.0
        if len(price) < 5:
            return 0.0
        if (price[-1] > price[-5] and rsi[-1] < rsi[-5]) or (price[-1] < price[-5] and rsi[-1] > rsi[-5]):
            div_score += 0.4
        if price[-1] > price[-5] and volume[-1] < volume[-5]:
            div_score += 0.3
        if len(macd_hist) >= 2 and price[-1] > price[-2] and macd_hist[-1] < macd_hist[-2]:
            div_score += 0.2
        return min(div_score, 1.0)
