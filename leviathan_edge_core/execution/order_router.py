from execution.okx_api_connector import OKXConnector


class OrderRouter:
    def __init__(self, live=False):
        self.live = live
        self.conn = OKXConnector() if live else None

    def send(self, symbol: str, direction: str, size: float, atr: float, leverage: int) -> dict:
        if not self.live:
            return {"status": "filled", "price": 0, "size": size}
        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"
        tp = 2.5 * atr
        sl = 0.7 * atr
        return self.conn.place_order(symbol, side, size, pos_side, tp=tp, sl=sl)

    def close(self, symbol: str, direction: str):
        if not self.live:
            return {"status": "closed"}
        pos_side = "long" if direction == "LONG" else "short"
        return self.conn.close_position(symbol, pos_side)
