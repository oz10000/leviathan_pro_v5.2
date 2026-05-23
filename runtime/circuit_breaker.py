import time

class CircuitBreaker:
    """
    Protección sistémica contra degradación extrema.
    Si se alcanza el máximo de pérdidas consecutivas o el drawdown
    supera el umbral, se activa un cooldown durante el cual no se
    permite operar.
    """

    def __init__(self, max_consecutive_losses=5, max_drawdown_pct=0.12,
                 cooldown_minutes=60):
        self.max_consecutive_losses = max_consecutive_losses
        self.max_drawdown_pct = max_drawdown_pct
        self.cooldown_minutes = cooldown_minutes

        self.loss_streak = 0
        self.peak_equity = None
        self.cooldown_until = 0.0

    # ------------------------------------------------------------------
    # Actualización de estado
    # ------------------------------------------------------------------
    def update(self, equity: float, pnl: float):
        now = time.time()
        if self.peak_equity is None:
            self.peak_equity = equity
        self.peak_equity = max(self.peak_equity, equity)

        dd = 1.0 - (equity / (self.peak_equity + 1e-8))

        if pnl < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

        triggered = (
            self.loss_streak >= self.max_consecutive_losses or
            dd >= self.max_drawdown_pct
        )
        if triggered:
            self.cooldown_until = now + self.cooldown_minutes * 60

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def can_trade(self) -> bool:
        return time.time() >= self.cooldown_until

    def status(self) -> dict:
        return {
            "loss_streak": self.loss_streak,
            "peak_equity": self.peak_equity,
            "cooldown_until": self.cooldown_until,
            "cooldown_active": not self.can_trade()
        }
