import time
from execution.okx_api_connector import OKXConnector

class OrderRouter:
    """
    Enrutador de órdenes hacia OKX.
    Dispone de dos interfaces:
    - send()        : compatible con código existente, devuelve dict simple.
    - send_with_feedback() : añade latencia, slippage y estado real para ExecutionQuality.
    """

    def __init__(self, live: bool = False):
        self.live = live
        self.conn = OKXConnector() if live else None

    # ------------------------------------------------------------------
    # Interfaz legacy (sin feedback)
    # ------------------------------------------------------------------
    def send(self, symbol: str, direction: str, size: float,
             atr: float, leverage: int) -> dict:
        """
        Envía una orden de mercado. Retorna un dict con al menos 'status'.
        """
        if not self.live:
            return {"status": "filled", "price": 0.0, "size": size}

        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"
        tp = 2.5 * atr
        sl = 0.7 * atr
        resp = self.conn.place_order(symbol, side, size, pos_side, tp=tp, sl=sl)
        if resp and resp.get("code") == "0":
            return {"status": "filled", "price": float(resp.get("data", [{}])[0].get("fillPx", 0)),
                    "size": size}
        return {"status": "rejected", "price": 0.0, "size": 0}

    # ------------------------------------------------------------------
    # Interfaz con feedback para ExecutionQuality
    # ------------------------------------------------------------------
    def send_with_feedback(self, symbol: str, direction: str, size: float,
                           atr: float, leverage: int) -> dict:
        """
        Envía orden y retorna latencia, slippage y estado.
        """
        t0 = time.time()
        if not self.live:
            latency = (time.time() - t0) * 1000
            return {
                "status": "filled",
                "price": 0.0,
                "size": size,
                "latency_ms": latency,
                "slippage_pct": 0.0
            }

        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"
        tp = 2.5 * atr
        sl = 0.7 * atr
        resp = self.conn.place_order(symbol, side, size, pos_side, tp=tp, sl=sl)
        latency = (time.time() - t0) * 1000

        if resp and resp.get("code") == "0":
            fill_price = float(resp.get("data", [{}])[0].get("fillPx", 0))
            # En un entorno real obtendríamos el requested_price del libro;
            # aquí asumimos slippage 0 para simplificar la simulación.
            slippage = 0.0
            return {
                "status": "filled",
                "price": fill_price,
                "size": size,
                "latency_ms": latency,
                "slippage_pct": slippage
            }
        return {
            "status": "rejected",
            "price": 0.0,
            "size": 0,
            "latency_ms": latency,
            "slippage_pct": 0.0
        }
