class ExecutionQuality:
    """
    Mide la calidad de ejecución comparando el precio de entrada real
    con el precio esperado en el momento de la señal.
    """
    def __init__(self):
        self.slippage_history = []
        self.quality = 1.0

    def quality_score(self):
        return self.quality

    def update(self, expected_price, actual_price):
        if expected_price > 0:
            slippage = abs(actual_price - expected_price) / expected_price
            self.slippage_history.append(slippage)
            if len(self.slippage_history) > 50:
                self.slippage_history.pop(0)
            avg_slippage = sum(self.slippage_history) / len(self.slippage_history)
            self.quality = max(0.0, 1.0 - avg_slippage * 100)
