import time
import pandas as pd
from engine.leviathan_engine import LeviathanEngine
from app_streamlit.okx_client import OKXClient


class TestnetAdapter:
    def __init__(self, api_key, secret_key, passphrase, symbols):
        self.engine = LeviathanEngine(symbols=symbols)
        self.client = OKXClient(api_key, secret_key, passphrase, testnet=True)
        self.symbols = symbols

    def get_market_data(self):
        data = {}
        for sym in self.symbols:
            df = self.client.get_candles(sym, "5m", 100)
            if not df.empty and "volume" not in df.columns:
                df.rename(columns={"vol": "volume"}, inplace=True)
            if not df.empty:
                data[sym] = df
            time.sleep(0.1)
        return data

    def run_cycle(self):
        data = self.get_market_data()
        self.engine.set_asset_data(data)
        return self.engine.run_cycle()
