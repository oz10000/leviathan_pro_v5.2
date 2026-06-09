import json
import numpy as np
from analytics.statistics import calculate_sharpe, calculate_sortino, calculate_drawdown

class MetricsReport:
    def __init__(self, trades: list):
        self.trades = trades

    def generate(self) -> dict:
        if not self.trades:
            return {}
        pnl = [t['pnl'] for t in self.trades]
        wins = [p for p in pnl if p > 0]
        losses = [p for p in pnl if p <= 0]
        return {
            "sharpe": calculate_sharpe(pnl),
            "sortino": calculate_sortino(pnl),
            "profit_factor": sum(wins) / abs(sum(losses)) if losses else float('inf'),
            "win_rate": len(wins) / len(pnl) if pnl else 0,
            "max_drawdown": calculate_drawdown(pnl),
            "total_trades": len(pnl),
            "net_profit": sum(pnl),
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
        }
