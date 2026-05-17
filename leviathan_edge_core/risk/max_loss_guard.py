class MaxLossGuard:
    def __init__(self, max_loss_percent=0.02):
        self.max_loss = max_loss_percent

    def is_exceeded(self, entry_price, current_price, side, leverage):
        if side == "long":
            loss = (entry_price - current_price) / entry_price * leverage
        else:
            loss = (current_price - entry_price) / entry_price * leverage
        return abs(loss) > self.max_loss
