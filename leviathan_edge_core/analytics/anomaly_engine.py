import numpy as np

class AnomalyEngine:
    """
    Detecta anomalías en el flujo de PnL. Una anomalía es una desviación
    significativa respecto a la distribución esperada de resultados.
    """
    def __init__(self, window=50, threshold=2.0):
        self.window = window
        self.threshold = threshold
        self.pnl_history = []
        self.last_anomaly_score = 0.0

    def anomaly_score(self):
        return self.last_anomaly_score

    def feed(self, pnl, meta_score=0.0):
        self.pnl_history.append(pnl)
        if len(self.pnl_history) > self.window:
            self.pnl_history.pop(0)

        if len(self.pnl_history) < 10:
            self.last_anomaly_score = 0.0
            return

        mean = np.mean(self.pnl_history)
        std = np.std(self.pnl_history) + 1e-8
        z_score = (pnl - mean) / std
        self.last_anomaly_score = abs(z_score) * (1.0 - meta_score)
