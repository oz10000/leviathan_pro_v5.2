import numpy as np

class StatisticalGuard:
    @staticmethod
    def validate(pnl_history, max_drawdown_pct=0.15, min_trades=10, max_consecutive_losses=5):
        if len(pnl_history) < min_trades:
            return True

        equity = np.cumsum(pnl_history)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-8)
        if np.max(drawdown) > max_drawdown_pct:
            return False

        consecutive = 0
        for pnl in reversed(pnl_history):
            if pnl <= 0:
                consecutive += 1
            else:
                break
        if consecutive >= max_consecutive_losses:
            return False

        return True
