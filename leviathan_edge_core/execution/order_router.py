from leviathan_edge_core.execution.okx_api_connector import OKXClient

class OrderRouter:
    def __init__(self, client: OKXClient):
        self.client = client

    def send(self, trade: dict) -> dict:
        """
        trade debe contener: instId, side, sz, posSide, [clOrdId]
        Devuelve la respuesta de place_order.
        """
        return self.client.place_order(
            instId=trade["instId"],
            side=trade["side"],
            sz=trade["sz"],
            posSide=trade["posSide"],
            clOrdId=trade.get("clOrdId"),
        )
