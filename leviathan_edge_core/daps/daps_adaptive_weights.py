class DAPSAdaptiveWeights:
    """
    Pesos adaptativos para los componentes del Edge Score.
    En función del régimen de mercado, ajusta la importancia relativa de cada filtro.
    """
    def __init__(self):
        self.weights = {
            "mtf": 0.30,
            "divergence": 0.20,
            "entropy": 0.15,
            "persistence": 0.15,
            "exec_quality": 0.20
        }

    def get_weights(self):
        return self.weights

    def adapt(self, regime):
        if regime == "trending":
            self.weights["mtf"] = 0.40
            self.weights["entropy"] = 0.10
        elif regime == "ranging":
            self.weights["mtf"] = 0.20
            self.weights["entropy"] = 0.25
