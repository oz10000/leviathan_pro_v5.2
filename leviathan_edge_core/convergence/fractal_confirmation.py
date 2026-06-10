class FractalConfirmation:
    """
    Busca confirmación fractal: patrones de precios que se repiten en diferentes escalas temporales.
    """
    def __init__(self):
        self.confirmed = False

    def check(self, price_5m, price_15m, price_1h):
        dir_5m = 1 if len(price_5m) >= 2 and price_5m[-1] > price_5m[-2] else -1
        dir_15m = 1 if len(price_15m) >= 2 and price_15m[-1] > price_15m[-2] else -1
        dir_1h = 1 if len(price_1h) >= 2 and price_1h[-1] > price_1h[-2] else -1
        self.confirmed = (dir_5m == dir_15m == dir_1h)
        return self.confirmed
