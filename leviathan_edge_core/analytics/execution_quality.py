import numpy as np
from collections import deque

class ExecutionQuality:
    """
    Métrica viva de calidad de ejecución.
    Se alimenta con latencia y slippage reales de cada orden y afecta el meta-score.
    """

    def __init__(self):
        self.slippages_bps = deque(maxlen=200)
        self.latencies_ms = deque(maxlen=200)
        self.fills = 0
        self.attempts = 0

    def feed_execution(self, latency_ms: float, slippage_pct: float,
                       filled: bool, rejected: bool = False):
        """
        Registra una ejecución real.

        latency_ms   : milisegundos desde envío hasta fill
        slippage_pct : (fill_price - requested_price) / requested_price (decimal)
        filled       : True si se ejecutó completamente
        rejected     : True si la orden fue rechazada
        """
        self.latencies_ms.append(latency_ms)
        if filled and not rejected:
            self.slippages_bps.append(abs(slippage_pct) * 10000)   # a bps
            self.fills += 1
        else:
            self.slippages_bps.append(100)   # 100 bps (1%) penalización
        self.attempts += 1

    def quality_score(self) -> float:
        """
        Devuelve un score entre 0.2 y 1.0 basado en el historial reciente.
        """
        fill_rate = self.fills / max(1, self.attempts)
        avg_slip = np.mean(self.slippages_bps) if self.slippages_bps else 0
        avg_lat  = np.mean(self.latencies_ms) if self.latencies_ms else 0

        slip_score = max(0.0, 1.0 - avg_slip / 1000.0)   # 1000 bps = 10% → 0
        lat_score  = max(0.0, 1.0 - avg_lat / 500.0)     # 500 ms → 0

        quality = 0.5 * fill_rate + 0.3 * slip_score + 0.2 * lat_score
        return float(np.clip(quality, 0.2, 1.0))
