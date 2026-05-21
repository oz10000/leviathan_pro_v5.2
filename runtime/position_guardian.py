import json, logging
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
POSITIONS_FILE = RUNTIME_DIR / "open_positions.json"

class PersistentPositionGuardian:
    def restore(self):
        if POSITIONS_FILE.exists():
            with open(POSITIONS_FILE) as f:
                positions = json.load(f)
            if positions:
                logging.info(f"Restored {len(positions)} open positions")
                return positions
        return None
