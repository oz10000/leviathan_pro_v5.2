import aiosqlite
import logging
from config import Config

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.db_path = Config.DB_PATH
        self.db = None

    async def initialize(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await self.db.commit()

    async def get_capital(self) -> float:
        cursor = await self.db.execute("SELECT value FROM state WHERE key='capital'")
        row = await cursor.fetchone()
        return float(row[0]) if row else Config.CAPITAL

    async def save(self):
        # Se actualizan valores específicos en otras partes del código
        pass

    async def close(self):
        if self.db:
            await self.db.close()
