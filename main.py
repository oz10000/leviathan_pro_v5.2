import asyncio
import logging
from runtime.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class Supervisor:
    def __init__(self):
        self.orch = Orchestrator()

    async def run(self):
        while True:
            try:
                await self.orch.run_forever()
            except Exception as e:
                logger.critical(f"Orchestrator crashed: {e}. Restarting in 10s...")
                await asyncio.sleep(10)
