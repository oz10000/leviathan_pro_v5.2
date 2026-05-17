from abc import ABC, abstractmethod
import numpy as np

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.trade_history = []

    @abstractmethod
    def compute_score(self, df_5m, df_15m, row_5m, row_15m, direction: str) -> float:
        pass

    @abstractmethod
    def should_enter(self, score: float, regime_state: str, era_active: bool) -> bool:
        pass

    def update_history(self, pnl_pct: float):
        self.trade_history.append(pnl_pct)

    def kelly_stats(self):
        if len(self.trade_history) < 5:
            return 2.0, 0.5
        wins = [x for x in self.trade_history if x > 0]
        losses = [abs(x) for x in self.trade_history if x <= 0]
        b = np.mean(wins) / np.mean(losses) if losses else 2.0
        p = len(wins) / len(self.trade_history)
        return b, p
