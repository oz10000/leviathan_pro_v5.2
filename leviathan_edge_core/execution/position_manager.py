from datetime import datetime


class PositionManager:
    def __init__(self):
        self.positions = {}
        self.trade_history = []

    def open(self, trade: dict):
        trade["entry_time"] = datetime.utcnow().timestamp()
        self.positions[trade["symbol"]] = trade

    def close(self, symbol: str, exit_price: float, reason: str):
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None
        pnl = ((exit_price - pos["entry"]) * pos.get("dir", 1) *
               pos.get("leverage", 1) * pos.get("size", 0) / pos["entry"])
        self.trade_history.append({**pos, "exit_price": exit_price, "reason": reason, "pnl": pnl})
        return pnl

    def active_count(self) -> int:
        return len(self.positions)

    def get_active_symbols(self) -> list:
        return list(self.positions.keys())
