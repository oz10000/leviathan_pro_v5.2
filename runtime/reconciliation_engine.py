import json, os, time, logging
from pathlib import Path
from runtime.okx_client import OKXClient

RUNTIME_DIR = Path(__file__).resolve().parent
POSITIONS_FILE = RUNTIME_DIR / "open_positions.json"

class ExchangeReconciliationEngine:
    def __init__(self):
        self.client = OKXClient(
            os.getenv("OKX_API_KEY", ""),
            os.getenv("OKX_SECRET_KEY", ""),
            os.getenv("OKX_PASSPHRASE", ""),
            testnet=(os.getenv("LEVIATHAN_MODE", "testnet") == "testnet")
        )

    def run(self):
        exchange_pos = self._fetch_exchange_positions()
        local_pos = self._load_local_positions()

        for ep in exchange_pos:
            sym = ep["instId"]
            if sym not in local_pos:
                logging.warning(f"Orphan exchange position: {sym}, reconstructing")
                self._reconstruct_position(ep)
            else:
                local = local_pos[sym]
                if abs(float(ep["pos"]) - local.get("size", 0)) > 1e-8:
                    logging.warning(f"Size mismatch {sym}")

        for sym in list(local_pos.keys()):
            if sym not in [p["instId"] for p in exchange_pos]:
                logging.warning(f"Local position {sym} missing on exchange, removing")
                del local_pos[sym]

        self._save_local_positions(local_pos)

    def _fetch_exchange_positions(self):
        resp = self.client._request("GET", "/api/v5/account/positions")
        if resp and resp.get("code") == "0":
            return [p for p in resp["data"] if float(p.get("pos", 0)) != 0]
        return []

    def _load_local_positions(self):
        if POSITIONS_FILE.exists():
            with open(POSITIONS_FILE) as f:
                return json.load(f)
        return {}

    def _save_local_positions(self, positions):
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions, f, indent=2)

    def _reconstruct_position(self, ep):
        local = {
            "symbol": ep["instId"],
            "dir": 1 if float(ep.get("pos", 0)) > 0 else -1,
            "entry": float(ep["avgPx"]),
            "size": abs(float(ep["pos"])),
            "leverage": int(ep.get("lever", 5)),
            "be_active": False,
            "trail_active": False,
            "atr": 0.01 * float(ep["markPx"]),
            "entry_time": time.time()
        }
        locals = self._load_local_positions()
        locals[ep["instId"]] = local
        self._save_local_positions(locals)
