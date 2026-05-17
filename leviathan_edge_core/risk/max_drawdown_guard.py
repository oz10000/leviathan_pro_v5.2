class MaxDrawdownGuard:
    def __init__(self, max_dd=0.15):
        self.max_dd = max_dd
        self.peak = 0

    def check(self, equity):
        self.peak = max(self.peak, equity)
        dd = (self.peak - equity) / self.peak
        return dd < self.max_dd
