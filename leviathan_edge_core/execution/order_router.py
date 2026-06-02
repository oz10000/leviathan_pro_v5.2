import time
from execution.okx_api_connector import OKXConnector

class OrderRouter:
    def __init__(self, connector: OKXConnector = None, live: bool = False):
        """
        connector: instancia de OKXConnector ya autenticada.
        Si no se proporciona, se crea una nueva (requiere credenciales en Config).
        """
        self.live = live
        self.conn = connector if connector else OKXConnector()

    def send(self, symbol, direction, size, atr, leverage):
        if not self.live:
            return {"status": "filled", "price": 0.0, "size": size}
        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"
        tp_price = round(atr * 2.5, 1)
        sl_price = round(atr * 0.7, 1)
        resp = self.conn.place_order(symbol, side, size, pos_side, tp=tp_price, sl=sl_price)
        if resp and resp.get("status") == "filled":
            return {"status": "filled", "price": 0.0, "size": size, "order_id": resp.get("order_id")}
        return {"status": "rejected", "price": 0.0, "size": 0}

    def send_with_feedback(self, symbol, direction, size, atr, leverage):
        t0 = time.time()
        if not self.live:
            latency = (time.time() - t0) * 1000
            return {"status": "filled", "price": 0.0, "size": size, "latency_ms": latency, "slippage_pct": 0.0}
        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"
        tp_price = round(atr * 2.5, 1)
        sl_price = round(atr * 0.7, 1)
        resp = self.conn.place_order(symbol, side, size, pos_side, tp=tp_price, sl=sl_price)
        latency = (time.time() - t0) * 1000
        if resp and resp.get("status") == "filled":
            return {
                "status": "filled",
                "price": 0.0,
                "size": size,
                "latency_ms": latency,
                "slippage_pct": 0.0,
                "order_id": resp.get("order_id"),
                "sl_order_id": resp.get("sl_order_id"),
                "tp_order_id": resp.get("tp_order_id")
            }
        return {"status": "rejected", "price": 0.0, "size": 0, "latency_ms": latency, "slippage_pct": 0.0}
