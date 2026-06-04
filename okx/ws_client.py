import asyncio
import json
import time
import logging
import websockets
from config import Config
from okx.auth import sign  # misma función de firma que usa REST

logger = logging.getLogger(__name__)

class OKXWebSocket:
    def __init__(self, bus=None):
        self.bus = bus
        self.ws_public = None
        self.ws_private = None
        self.shutdown_flag = False
        self.reconnect_delay = 1

    async def connect(self):
        while not self.shutdown_flag:
            try:
                extra = {"x-simulated-trading": "1"} if Config.OKX_DEMO else {}
                self.ws_public = await websockets.connect(
                    Config.WS_PUBLIC_URL,
                    ping_interval=Config.WS_PING_INTERVAL,
                )
                self.ws_private = await websockets.connect(
                    Config.WS_PRIVATE_URL,
                    extra_headers=extra,
                    ping_interval=Config.WS_PING_INTERVAL,
                )
                await self._login()
                logger.info("WebSocket connected")
                self.reconnect_delay = 1
                return
            except Exception as e:
                logger.error(f"WS connection failed: {e}. Retrying in {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 300)

    async def _login(self):
        ts = str(int(time.time() * 1000))
        sig = sign(Config.OKX_API_SECRET, ts, "GET", "/users/self/verify")
        msg = {
            "op": "login",
            "args": [{
                "apiKey": Config.OKX_API_KEY,
                "passphrase": Config.OKX_API_PASSPHRASE,
                "timestamp": ts,
                "sign": sig
            }]
        }
        await self.ws_private.send(json.dumps(msg))
        resp = await self.ws_private.recv()
        data = json.loads(resp)
        if data.get("event") != "login" or data.get("code") != "0":
            raise Exception(f"WS login failed: {data}")

    async def subscribe_public(self, symbols: list[str]):
        for sym in symbols:
            msg = {"op": "subscribe", "args": [{"channel": "candle5m", "instId": sym}]}
            await self.ws_public.send(json.dumps(msg))

    async def subscribe_private(self):
        for ch in ["orders", "positions"]:
            msg = {"op": "subscribe", "args": [{"channel": ch, "instType": "SWAP"}]}
            await self.ws_private.send(json.dumps(msg))

    async def listen(self, on_candle, on_order, on_position):
        async def handle_ws(ws, source):
            try:
                async for raw in ws:
                    data = json.loads(raw)
                    if "data" not in data:
                        continue
                    ch = data.get("arg", {}).get("channel")
                    for item in data["data"]:
                        if ch == "candle5m":
                            await on_candle(data["arg"]["instId"], item)
                        elif ch == "orders":
                            await on_order(item)
                        elif ch == "positions":
                            await on_position(item)
            except websockets.ConnectionClosed:
                logger.warning(f"WS {source} closed")
        tasks = [
            asyncio.create_task(handle_ws(self.ws_public, "public")),
            asyncio.create_task(handle_ws(self.ws_private, "private")),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        self.shutdown_flag = True
        if self.ws_public:
            await self.ws_public.close()
        if self.ws_private:
            await self.ws_private.close()
