import asyncio
import logging
from workflow.supervisor import Supervisor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

async def main():
    supervisor = Supervisor()
    await supervisor.run()

if __name__ == "__main__":
    asyncio.run(main())
