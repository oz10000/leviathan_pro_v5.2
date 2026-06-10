class StreakDetector:
    """
    Detecta rachas de operaciones ganadoras o perdedoras.
    Ayuda a activar medidas de protección cuando las rachas perdedoras se alargan.
    """
    def __init__(self, max_loss_streak=5):
        self.current_streak = 0
        self.max_loss_streak = max_loss_streak
        self.longest_win = 0
        self.longest_loss = 0

    def add_trade(self, trade):
        pnl = trade.get("pnl", 0)
        if pnl > 0:
            if self.current_streak > 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
        else:
            if self.current_streak < 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1

        if self.current_streak > self.longest_win:
            self.longest_win = self.current_streak
        if abs(self.current_streak) > self.longest_loss:
            self.longest_loss = abs(self.current_streak)

    def is_protected(self):
        return self.current_streak <= -self.max_loss_streak
