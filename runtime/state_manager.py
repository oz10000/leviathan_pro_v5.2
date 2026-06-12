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

    def get_capital(self) -> float:
        """Devuelve el capital actual desde la configuración."""
        return Config.CAPITAL

    def _path(self, filename):
        return os.path.join(self.state_dir, filename)

    def load_json(self, filename):
        path = self._path(filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def save_json(self, filename, data):
        path = self._path(filename)
        with open(path, "w") as f:
            json.dump(data, f)

    def load_positions(self):
        return self.load_json("open_positions.json") or []

    def save_positions(self, positions):
        self.save_json("open_positions.json", positions)

    def load_daps_state(self):
        return self.load_json("daps_state.json") or {}

    def save_daps_state(self, state):
        self.save_json("daps_state.json", state)

    async def close(self):
        if self.db:
            await self.db.close()
