import logging
from runtime.okx_client import OKXClient

class ExchangeFailsafe:
    def __init__(self, client: OKXClient):
        self.client = client

    def ensure_protection(self, symbol, pos):
        atr = pos.get("atr", pos["entry"] * 0.01)
        direction = pos.get("dir", 1)
        hard_sl = pos["entry"] - direction * 3.0 * atr
        hard_tp = pos["entry"] + direction * 7.0 * atr
        try:
            self.client._request("POST", "/api/v5/trade/amend-order", {
                "instId": f"{symbol}-USDT-SWAP",
                "slTriggerPx": str(round(hard_sl, 2)),
                "tpTriggerPx": str(round(hard_tp, 2))
            })
        except Exception as e:
            logging.error(f"Failsafe error for {symbol}: {e}")
