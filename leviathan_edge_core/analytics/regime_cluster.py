class RegimeCluster:
    """
    Clasifica el régimen de mercado actual basado en volatilidad y tendencia.
    Regímenes: trending, ranging, volatile, calm.
    """
    def __init__(self):
        self.regime = "neutral"
        self.volatility_history = []
        self.trend_history = []

    def update(self, volatility, trend_strength):
        self.volatility_history.append(volatility)
        self.trend_history.append(trend_strength)
        if len(self.volatility_history) > 20:
            self.volatility_history.pop(0)
            self.trend_history.pop(0)

        avg_vol = sum(self.volatility_history) / len(self.volatility_history)
        avg_trend = sum(self.trend_history) / len(self.trend_history)

        if avg_vol > 0.03 and avg_trend > 0.5:
            self.regime = "trending"
        elif avg_vol < 0.01 and avg_trend < 0.2:
            self.regime = "ranging"
        elif avg_vol > 0.03:
            self.regime = "volatile"
        else:
            self.regime = "calm"

    def get_regime(self):
        return self.regime
