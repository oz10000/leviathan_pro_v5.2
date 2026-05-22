
import os
import time
import random
import logging
import requests
import pandas as pd
from typing import Dict, List, Tuple

import time, random, logging, requests
import pandas as pd
from typing import Dict, List, Tuple

from core.feature_engine import compute_features
from runtime.okx_client import OKXClient

logger = logging.getLogger("market_data")

class MarketDataFetcher:
    def __init__(self):
        self.client = OKXClient(
            api_key=os.getenv("OKX_API_KEY", ""),
            secret_key=os.getenv("OKX_SECRET_KEY", ""),
            passphrase=os.getenv("OKX_PASSPHRASE", ""),
            testnet=(os.getenv("LEVIATHAN_MODE", "testnet") == "testnet")
        )
        self.error_counts: Dict[str, int] = {}
        self.latency_sum = 0.0
        self.latency_count = 0

    def fetch_with_retry(self, symbols: List[str], max_retries: int = 3, timeout: int = 10) -> Tuple[Dict, List[str]]:
        """
        Descarga velas de todos los símbolos con reintentos y timeout.
        Retorna (market_data, failed_symbols).
        """
        market_data = {}
        failed_symbols = []

        for sym in symbols:
            df = self._fetch_symbol_with_retry(sym, max_retries, timeout)
            if df is not None and not df.empty:
                market_data[sym] = df
            else:
                failed_symbols.append(sym)

        return market_data, failed_symbols

    def _fetch_symbol_with_retry(self, symbol: str, max_retries: int, timeout: int) -> pd.DataFrame:
        """Descarga un símbolo con backoff exponencial y timeout."""
        for attempt in range(1, max_retries + 1):
            try:
                start = time.time()
                # Usamos el cliente OKX con timeout
                df = self.client.get_candles(symbol, "5m", 100)
                latency = time.time() - start
                self.latency_sum += latency
                self.latency_count += 1

                if df is None or df.empty:
                    raise ValueError("Empty DataFrame")

                # Validación de columnas
                if "volume" not in df.columns and "vol" in df.columns:
                    df.rename(columns={"vol": "volume"}, inplace=True)
                required_cols = ["open", "high", "low", "close", "volume"]
                if not all(c in df.columns for c in required_cols):
                    raise ValueError(f"Missing columns in {symbol}")

                # Calcular features (ATR, RSI, scores, etc.)
                df = compute_features(df)

                if df.empty or len(df) < 20:
                    raise ValueError(f"Not enough data for {symbol}")

                self.error_counts.pop(symbol, None)
                logger.info(f"[SCAN] {symbol} success latency={latency:.2f}s rows={len(df)}")
                return df

            except Exception as e:
                logger.warning(f"[SCAN] {symbol} attempt {attempt} failed: {e}")
                self.error_counts[symbol] = self.error_counts.get(symbol, 0) + 1
                time.sleep(random.uniform(1, 3) * attempt)  # backoff

        logger.error(f"[SCAN] {symbol} FAILED after {max_retries} attempts")
        return pd.DataFrame()
