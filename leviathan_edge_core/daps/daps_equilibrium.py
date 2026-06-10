class DAPSEquilibrium:
    """
    Factor de equilibrio que modula el Edge Score en función del estado DAPS.
    Un valor de x cercano a 0 produce un factor cercano a 0.5 (neutral).
    Valores extremos de x reducen o amplifican el factor.
    """
    def __init__(self):
        self.factor_value = 0.5

    def factor(self, x):
        self.factor_value = max(0.0, min(1.0, 0.5 - x * 0.5))
        return self.factor_value
