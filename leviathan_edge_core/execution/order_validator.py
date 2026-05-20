class OrderValidator:
    def __init__(self):
        self.min_notional = 5.0
    def validate(self, symbol, size, entry_price, leverage):
        notional = size * entry_price
        if notional < self.min_notional:
            return False, f"Notional {notional:.2f} < min {self.min_notional}"
        return True, "OK"
