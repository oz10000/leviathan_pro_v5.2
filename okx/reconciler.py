import logging
import time
import aiosqlite
from config import Config

logger = logging.getLogger(__name__)

class Reconciler:
    def __init__(self, client):
        self.client = client
        self.db_path = Config.DB_PATH
        self._ws_positions = {}
        self._last_close = {}

    async def restore_state(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sent_orders (
                    clOrdId TEXT PRIMARY KEY,
                    timestamp INTEGER,
                    symbol TEXT,
                    side TEXT,
                    size REAL
                )
            """)
            await db.commit()

    async def was_order_sent(self, clOrdId):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM sent_orders WHERE clOrdId=?", (clOrdId,))
            row = await cursor.fetchone()
            return row is not None

    async def mark_order_sent(self, clOrdId, symbol, side, size):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO sent_orders VALUES (?,?,?,?,?)",
                (clOrdId, int(time.time()), symbol, side, size)
            )
            await db.commit()

    def reconcile_positions(self, local_positions):
        remote_data = self.client.get_positions().get('data', [])
        remote_map = {f"{p['instId']}:{p['posSide']}": float(p.get('pos', 0)) for p in remote_data}
        local_map = {f"{p['instId']}:{p['posSide']}": float(p.get('pos', 0)) for p in local_positions}
        for key in set(remote_map) | set(local_map):
            r_pos = remote_map.get(key, 0)
            l_pos = local_map.get(key, 0)
            if abs(r_pos - l_pos) > 0.001:
                instId, posSide = key.split(":")
                if r_pos > 0 and l_pos == 0:
                    logger.warning(f"Ghost position {key}, closing")
                    self.client.close_position(instId, posSide)
                elif l_pos > 0 and r_pos == 0:
                    logger.warning(f"Missing position {key} locally, removing")
        return [{"instId": p["instId"], "posSide": p["posSide"], "pos": p["pos"], "avgPx": p.get("avgPx", 0)}
                for p in remote_data if float(p.get("pos", 0)) > 0]

    def save_state(self, positions):
        pass
