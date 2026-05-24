import pandas as pd
import ccxt
from datetime import datetime, timezone
from execution.exchange_connector import ExchangeConnector

class OKXConnector(ExchangeConnector):
    def __init__(self):
        # ⚠️ CREDENCIALES HARDCODEADAS DIRECTAMENTE (SOLO PRUEBAS)
        api_key = "76254b4d-2126-4bb5-a0f1-8c0aa463d90e"
        api_secret = "36F40E60584E4561E1E2475B979ABDDF"
        passphrase = ""

        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {'defaultType': 'swap'}
        })

        self.exchange.set_sandbox_mode(True)
        self.exchange.load_markets()

    # ------------------------------------------------------------------
    # Market data (público)
    # ------------------------------------------------------------------
    def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
        try:
            ccxt_symbol = f"{symbol}/USDT:USDT"
            ohlcv = self.exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
            if not ohlcv:
                return pd.DataFrame()
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "vol"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            return df.sort_values("ts").reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    def fetch_tickers(self) -> list:
        try:
            tickers = self.exchange.fetch_tickers()
            result = []
            for s, t in tickers.items():
                if s.endswith("/USDT:USDT"):
                    result.append({
                        "symbol": s.replace("/USDT:USDT", ""),
                        "last": t.get("last"),
                        "quoteVolume": t.get("quoteVolume", 0)
                    })
            return result
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Execution (privado)
    # ------------------------------------------------------------------
    def place_order(self, symbol: str, side: str, size: float,
                    pos_side: str, tp: float = None, sl: float = None) -> dict:
        try:
            ccxt_symbol = f"{symbol}/USDT:USDT"
            params = {}
            if tp and sl:
                params["tpTriggerPx"] = str(tp)
                params["tpOrdPx"] = "-1"
                params["slTriggerPx"] = str(sl)
                params["slOrdPx"] = "-1"
            order = self.exchange.create_market_order(ccxt_symbol, side.lower(), size, params=params)
            return {"code": "0", "data": [{"ordId": order.get("id", "")}]}
        except Exception as e:
            return {"code": "1", "msg": str(e)}

    def close_position(self, symbol: str, pos_side: str) -> dict:
        try:
            ccxt_symbol = f"{symbol}/USDT:USDT"
            side = "sell" if pos_side == "long" else "buy"
            self.exchange.create_market_order(ccxt_symbol, side, 0, params={"reduceOnly": True})
            return {"code": "0"}
        except Exception as e:
            return {"code": "1", "msg": str(e)}

    def get_positions(self) -> dict:
        try:
            positions = self.exchange.fetch_positions()
            return {"code": "0", "data": positions}
        except Exception as e:
            return {"code": "1", "msg": str(e)}

    def get_balance(self) -> float:
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get("USDT", {}).get("free", 0.0))
        except Exception:
            return 0.0

    def normalize_symbol(self, raw_symbol: str) -> str:
        return raw_symbol
