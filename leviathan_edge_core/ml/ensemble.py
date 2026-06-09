"""
Ensemble – Fusión bayesiana de señales.
"""
import numpy as np
from leviathan_edge_core.ml.ml_model import MLModel

class Ensemble:
    def __init__(self):
        self.models = [MLModel() for _ in range(3)]   # 3 modelos con inicializaciones distintas
        self.weights = [0.4, 0.35, 0.25]              # pesos de cada modelo

    def fuse(self, closes: list[float]) -> float:
        """Combina las predicciones de los modelos en una sola señal."""
        if len(closes) < 20:
            return 0.0
        signals = [model.predict(closes) for model in self.models]
        weighted = sum(w * s for w, s in zip(self.weights, signals))
        return max(-1.0, min(1.0, weighted))
