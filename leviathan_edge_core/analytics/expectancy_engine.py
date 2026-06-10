class ExpectancyEngine:
    """
    Calcula la expectancia (ganancia esperada por operación) basada en el historial reciente.
    """
    def __init__(self, window=100):
        self.window = window
        self.pnl_history = []

    def add(self, pnl):
        self.pnl_history.append(pnl)
        if len(self.pnl_history) > self.window:
            self.pnl_history.pop(0)

    def compute(self):
        if not self.pnl_history:
            return 0.0
        return sum(self.pnl_history) / len(self.pnl_history)
