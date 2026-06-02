import ccxt
import time
import pandas as pd
from datetime import datetime, timezone
from config import Config

class OKXConnector:
    def __init__(self):
        self.exchange = ccxt.okx({
            'apiKey': Config.OKX_API_KEY,
            'secret': Config.OKX_API_SECRET,
            'password': Config.OKX_PASSPHRASE if Config.OKX_PASSPHRASE else '',
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {'defaultType': 'swap'},
        })
        self.exchange.headers.update({'x-simulated-trading': '1'})

    def normalize_symbol(self, symbol: str) -> str:
        if "/" in symbol and ":" in symbol:
            base, rest = symbol.split("/")
            quote = rest.split(":")[0]
            return f"{base}-{quote}-SWAP"
        return symbol

    def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
        ccxt_symbol = f"{symbol}/USDT:USDT"
        timeframe = timeframe.lower().replace(" ", "")
        try:
            ohlcv = self.exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
            if not ohlcv:
                return pd.DataFrame()
            df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            return df.sort_values("ts").reset_index(drop=True)
        except Exception as e:
            print(f"[FETCH ERROR] {symbol} ({timeframe}): {e}", flush=True)
            return pd.DataFrame()

    def fetch_tickers(self) -> list:
        try:
            tickers = self.exchange.fetch_tickers()
            return [
                {"symbol": s.replace("/USDT:USDT", ""), "last": t.get("last"),
                 "quoteVolume": t.get("quoteVolume", 0)}
                for s, t in tickers.items() if s.endswith("/USDT:USDT")
            ]
        except Exception:
            return []

    def place_order(self, symbol: str, side: str, size: float,
                    pos_side: str = None, leverage: int = 5, tp: float = None, sl: float = None) -> dict:
        ccxt_symbol = self.normalize_symbol(symbol)
        params = {
            "posSide": pos_side,
            "mgnMode": "isolated",
            "leverage": str(leverage),
            "tdMode": "isolated"
        }
        print(f"[ORDER_REQUEST] {ccxt_symbol} {side} {size} params={params}", flush=True)
        try:
            order = self.exchange.create_market_order(ccxt_symbol, side.lower(), size, params=params)
            print(f"[ORDER_RESPONSE] order_id={order.get('id')} status={order.get('status')}", flush=True)
            time.sleep(2)
            filled_order = self.exchange.fetch_order(order['id'], ccxt_symbol)
            print(f"[EXCHANGE_CONFIRMATION] id={filled_order['id']} filled={filled_order.get('filled',0)}", flush=True)
            return {
                "order_id": filled_order["id"],
                "status": "filled" if filled_order.get("filled", 0) > 0 else "open",
                "filled_amount": filled_order.get("filled", 0)
            }
        except Exception as e:
            print(f"[ORDER_ERROR_RAW] {repr(e)}", flush=True)
            if hasattr(e, 'args') and len(e.args) > 0:
                print(f"[ORDER_ERROR_DETAIL] {e.args}", flush=True)
            return {"status": "failed", "order_id": "N/A", "error": str(e)}

    def modify_sl(self, symbol: str, sl_order_id: str, new_sl: float, amount: float, side: str) -> bool:
        if not sl_order_id:
            return False
        try:
            self.exchange.edit_order(
                id=sl_order_id,
                symbol=self.normalize_symbol(symbol),
                type='stop_market',
                side=side,
                amount=amount,
                price=None,
                params={'stopLossPrice': new_sl}
            )
            print(f"[MODIFY SL] {symbol}: SL actualizado a {new_sl}", flush=True)
            return True
        except Exception as e:
            print(f"[MODIFY SL ERROR] {e}", flush=True)
            return False

    def close_position(self, symbol: str, pos_side: str) -> dict:
        ccxt_symbol = self.normalize_symbol(symbol)
        side = "sell" if pos_side == "long" else "buy"
        try:
            self.exchange.create_market_order(ccxt_symbol, side, 0, params={"reduceOnly": True})
            return {"status": "closed"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def get_positions(self) -> list:
        try:
            return self.exchange.fetch_positions()
        except Exception:
            return []

    def get_balance(self) -> float:
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get("USDT", {}).get("free", 0.0))
        except Exception:
            return 0.0

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            self.exchange.cancel_order(order_id, self.normalize_symbol(symbol))
            return True
        except Exception as e:
            print(f"[CANCEL ERROR] {e}", flush=True)
            return False
