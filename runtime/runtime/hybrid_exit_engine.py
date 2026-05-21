import time, logging
from execution.exit_hybrid import HybridExit
from runtime.exchange_failsafe import ExchangeFailsafe
from runtime.okx_client import OKXClient
import os

class HybridExitManager:
    def __init__(self):
        self.client = OKXClient(
            os.getenv("OKX_API_KEY", ""),
            os.getenv("OKX_SECRET_KEY", ""),
            os.getenv("OKX_PASSPHRASE", ""),
            testnet=(os.getenv("LEVIATHAN_MODE", "testnet") == "testnet")
        )
        self.failsafe = ExchangeFailsafe(self.client)

    def manage(self, engine, pos_mgr, market_data):
        for sym in pos_mgr.get_active_symbols():
            pos = pos_mgr.positions[sym]
            df = market_data.get(sym)
            if df is None or len(df) < 1:
                continue
            price = df["close"].iloc[-1]

            exit_sig, reason, exit_price, updated = HybridExit.should_exit(
                pos, price, time.time()
            )
            if updated:
                pos_mgr.positions[sym] = updated

            self.failsafe.ensure_protection(sym, pos)

            if exit_sig:
                pnl = pos_mgr.close(sym, exit_price, reason)
                if pnl is not None:
                    self.client.close_position(sym, "long" if pos["dir"]==1 else "short")
                    engine.capital += pnl
