import time, random, pandas as pd
from core.feature_engine import compute_features
from runtime.okx_client import OKXClient
import os

class MarketDataFetcher:
    def __init__(self):
        self.client = OKXClient(
            os.getenv("OKX_API_KEY", ""),
            os.getenv("OKX_SECRET_KEY", ""),
            os.getenv("OKX_PASSPHRASE", ""),
            testnet=(os.getenv("LEVIATHAN_MODE", "testnet") == "testnet")
        )

    def fetch(self, symbols):
        data = {}
        for sym in symbols:
            time.sleep(random.uniform(0.1, 0.5))
            df = self.client.get_candles(sym, "5m", 100)
            if not df.empty:
                if "volume" not in df.columns and "vol" in df.columns:
                    df.rename(columns={"vol": "volume"}, inplace=True)
                df = compute_features(df)
                data[sym] = df
        return data
