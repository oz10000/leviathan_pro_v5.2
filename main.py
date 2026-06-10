import asyncio
import logging
from runtime.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

async def main():
    orchestrator = Orchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
