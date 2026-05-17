class LiquidationRisk:
    def estimate(self, margin, position_size, entry_price, mark_price, side, maintenance_margin=0.005):
        if side == "long":
            liq_price = entry_price * (1 - (margin - maintenance_margin * position_size) / position_size)
        else:
            liq_price = entry_price * (1 + (margin - maintenance_margin * position_size) / position_size)
        return liq_price, abs(liq_price - mark_price) / mark_price
