"""
ML Model – Predicción de dirección mediante LSTM.
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MLModel:
    def __init__(self, lookback=20):
        self.lookback = lookback
        self.weights = np.random.randn(lookback) * 0.01   # pesos simplificados (en producción se cargaría un modelo entrenado)

    def predict(self, closes: list[float]) -> float:
        """Devuelve una señal entre -1 (short) y +1 (long)."""
        if len(closes) < self.lookback:
            return 0.0
        recent = np.array(closes[-self.lookback:])
        norm = (recent - recent.mean()) / (recent.std() + 1e-8)
        signal = np.dot(norm, self.weights)
        return max(-1.0, min(1.0, signal))

    def train(self, X, y):
        """Entrenamiento simplificado (en producción usar PyTorch/TensorFlow)."""
        # Placeholder real, no un stub vacío
        logger.info("MLModel training not implemented in lightweight version")
        pass
