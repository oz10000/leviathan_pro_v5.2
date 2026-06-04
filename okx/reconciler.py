import asyncio
import logging

logger = logging.getLogger(__name__)

class Reconciler:
    def __init__(self, client, state, interval=60):
        self.client = client
        self.state = state
        self.interval = interval
        self.ws_positions = {}

    async def on_ws_position(self, data):
        key = f"{data['instId']}:{data['posSide']}"
        self.ws_positions[key] = float(data.get("pos", 0))

    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.reconcile()

    async def reconcile(self):
        rest_positions = self.client.get_positions()
        for rp in rest_positions:
            key = f"{rp['instId']}:{rp['posSide']}"
            rest_pos = float(rp.get("pos", 0))
            ws_pos = self.ws_positions.get(key, 0)
            if rest_pos > 0 and ws_pos == 0:
                logger.warning(f"Ghost position {key} detected. Closing.")
                instId, posSide = key.split(":")
                self.client.close_position(instId, posSide)
