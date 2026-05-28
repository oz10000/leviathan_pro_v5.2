import time
from collections import defaultdict

class PnLTracker:
    """Registra métricas de velocidad de cada activo en tiempo real."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.trades = defaultdict(list)
        self.last_report = time.time()

    def record_trade(self, symbol, pnl, duration_min, direction):
        self.trades[symbol].append({
            'pnl': pnl,
            'duration_min': duration_min,
            'direction': direction,
            'timestamp': time.time()
        })

    def get_velocity_stats(self, symbol, window_min=10080):
        """Retorna métricas de velocidad del activo (ventana en minutos, default 7 días)."""
        now = time.time()
        recent = [t for t in self.trades[symbol] if now - t['timestamp'] < window_min * 60]
        if not recent:
            return None
        total_pnl = sum(t['pnl'] for t in recent)
        avg_duration = sum(t['duration_min'] for t in recent) / len(recent)
        trades_per_hour = len(recent) / (window_min / 60) if window_min > 0 else 0.0
        pnl_per_hour = total_pnl / (window_min / 60) if window_min > 0 else 0.0
        wins = sum(1 for t in recent if t['pnl'] > 0)
        winrate = wins / len(recent) if recent else 0.0
        return {
            'pnl_per_hour': pnl_per_hour,
            'trades_per_hour': trades_per_hour,
            'avg_duration_min': avg_duration,
            'winrate': winrate
        }
