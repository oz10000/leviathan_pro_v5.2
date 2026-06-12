import os
import json
import aiosqlite
import logging
from config import Config

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.db_path = Config.DB_PATH
        self.db = None
        self.state_dir = "state"

    async def initialize(self):
        os.makedirs(self.state_dir, exist_ok=True)
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await self.db.commit()

    # ... (métodos existentes sin cambios)
