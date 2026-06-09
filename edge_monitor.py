"""
Edge Monitor – Monitoreo en tiempo real del Profit Factor y alertas.
"""
import json
import logging
import time
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
            json.dump(self.calculate_metrics(), f)
