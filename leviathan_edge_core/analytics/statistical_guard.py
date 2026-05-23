import numpy as np

class StatisticalGuard:
    """
    Bloquea el trading si el rendimiento reciente cae por debajo de umbrales mínimos.
    """

    @staticmethod
    def validate(pnl_history: list,
                 min_winrate: float = 0.42,
                 min_profit_factor: float = 1.15,
                 min_expectancy: float = 0.0) -> bool:
        if len(pnl_history) < 20:
            return True

        pnl = np.array(pnl_history)
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]

        winrate = len(wins) / len(pnl)
        gp = wins.sum() if len(wins) > 0 else 0.0
        gl = abs(losses.sum()) if len(losses) > 0 else 1e-8
        pf = gp / gl
        expectancy = pnl.mean()

        return (
            winrate >= min_winrate and
            pf >= min_profit_factor and
            expectancy >= min_expectancy
        )
