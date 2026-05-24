import pandas as pd
import ccxt
from datetime import datetime, timezone
from config import Config
from execution.exchange_connector import ExchangeConnector

class OKXConnector(ExchangeConnector):
    def __init__(self):
        self.exec_mode = Config.EXECUTION_MODE

        # Credenciales desde Config (hardcodeadas para pruebas)
        api_key = Config.API_KEY
        api_secret = Config.API_SECRET
        passphrase = Config.PASSPHRASE if Config.PASSPHRASE else ""

        # Inicializar CCXT exactamente como en Okx-test
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {'defaultType': 'swap'}
        })

        if self.exec_mode == "demo":
            self.exchange.set_sandbox_mode(True)

        self.exchange.load_markets()

    # ------------------------------------------------------------------
    # Market data (público)
    # ------------------------------------------------------------------
    def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
        """Devuelve DataFrame con columnas ts, open, high, low, close, vol."""
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
        """Retorna lista de dicts con symbol, last, quoteVolume."""
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
        """Retorna dict con code y data[ordId] como antes."""
        if self.exec_mode == "paper":
            return {"code": "0", "data": [{"ordId": f"paper_{int(datetime.now().timestamp())}"}]}
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
        """Cierra la posición abierta."""
        if self.exec_mode == "paper":
            return {"code": "0"}
        try:
            ccxt_symbol = f"{symbol}/USDT:USDT"
            side = "sell" if pos_side == "long" else "buy"
            self.exchange.create_market_order(ccxt_symbol, side, 0, params={"reduceOnly": True})
            return {"code": "0"}
        except Exception as e:
            return {"code": "1", "msg": str(e)}

    def get_positions(self) -> dict:
        """Retorna dict con code y data (lista de posiciones)."""
        if self.exec_mode == "paper":
            return {"code": "0", "data": []}
        try:
            positions = self.exchange.fetch_positions()
            return {"code": "0", "data": positions}
        except Exception as e:
            return {"code": "1", "msg": str(e)}

    def get_balance(self) -> float:
        """Retorna el balance en USDT."""
        if self.exec_mode == "paper":
            return 0.0
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get("USDT", {}).get("free", 0.0))
        except Exception:
            return 0.0

    def normalize_symbol(self, raw_symbol: str) -> str:
        return raw_symbol
