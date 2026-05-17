import numpy as np

class CorrelationRiskEngine:
    def __init__(self):
        self.prices = {}
        self.corr_matrix = {}

    def update_price(self, symbol: str, price: float):
        if symbol not in self.prices:
            self.prices[symbol] = []
        self.prices[symbol].append(price)
        if len(self.prices[symbol]) > 100:
            self.prices[symbol].pop(0)

    def compute_correlations(self):
        symbols = [s for s, p in self.prices.items() if len(p) >= 30]
        if len(symbols) < 2:
            return
        data = {}
        for s in symbols:
            data[s] = np.array(self.prices[s][-50:])
        matrix = {}
        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                if s1 == s2:
                    matrix[s1][s2] = 1.0
                else:
                    corr = np.corrcoef(data[s1], data[s2])[0, 1]
                    matrix[s1][s2] = corr
        self.corr_matrix = matrix

    def position_correlation_basket(self, positions: list) -> float:
        if len(positions) < 2:
            return 0.0
        corrs = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                if positions[i] in self.corr_matrix and positions[j] in self.corr_matrix[positions[i]]:
                    corrs.append(self.corr_matrix[positions[i]][positions[j]])
        return np.mean(corrs) if corrs else 0.0
