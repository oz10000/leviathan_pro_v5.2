"""
Edge Monitor – Monitoreo en tiempo real del Profit Factor y alertas.
"""
import json
import logging
import time
import os
from collections import deque

logger = logging.getLogger(__name__)

class EdgeMonitor:
    def __init__(self, window_size=100, alert_threshold=1.15):
        self.window = deque(maxlen=window_size)
        self.alert_threshold = alert_threshold
        self.alert_active = False

    def record_trade(self, pnl: float):
        self.window.append(pnl)

    def calculate_metrics(self) -> dict:
        if len(self.window) < 5:
            return {}
        wins = [p for p in self.window if p > 0]
        losses = [p for p in self.window if p <= 0]
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        win_rate = len(wins) / len(self.window) * 100
        return {
            "profit_factor": round(profit_factor, 3),
            "win_rate": round(win_rate, 1),
            "n_trades": len(self.window),
            "timestamp": int(time.time()),
        }

    def should_alert(self) -> bool:
        metrics = self.calculate_metrics()
        if not metrics:
            return False
        if metrics["profit_factor"] < self.alert_threshold and not self.alert_active:
            self.alert_active = True
            logger.warning(f"Edge alert: Profit Factor {metrics['profit_factor']} < {self.alert_threshold}")
            return True
        if metrics["profit_factor"] >= self.alert_threshold:
            self.alert_active = False
        return False

    def save_metrics(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "window": list(self.window),
                "alert_active": self.alert_active,
                **self.calculate_metrics()
            }, f)

    def load_metrics(self, path: str):
        """
        Restaura el historial del monitor desde un archivo JSON.
        Si el archivo no existe o está corrupto, se inicia en blanco.
        """
        if not os.path.exists(path):
            logger.debug(f"No metrics file found at {path}, starting fresh.")
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Restaurar la ventana de trades
            if "window" in data and isinstance(data["window"], list):
                for pnl in data["window"]:
                    self.window.append(float(pnl))
            # Restaurar el estado de alerta
            if "alert_active" in data:
                self.alert_active = bool(data["alert_active"])
            logger.info(f"EdgeMonitor restored from {path} with {len(self.window)} trades.")
        except Exception as e:
            logger.warning(f"Failed to load metrics from {path}: {e}. Starting fresh.")
