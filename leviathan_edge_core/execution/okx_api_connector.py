import ccxt
import pandas as pd
import time
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

    def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
        """
        Descarga velas. Normaliza el timeframe a minúsculas (OKX espera '1h', no '1H').
        """
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
                    pos_side: str = None, tp: float = None, sl: float = None) -> dict:
        """
        Envía orden de mercado con TP/SL condicionales.
        Retorna 'order_id', 'sl_order_id', 'tp_order_id' y 'status'.
        """
        ccxt_symbol = f"{symbol}/USDT:USDT"
        try:
            # Cargar mercado bajo demanda para obtener min_size
            try:
                self.exchange.load_markets(reload=True, params={'instType': 'SWAP'})
                market = self.exchange.market(ccxt_symbol)
                min_size = market['limits']['amount']['min'] or 0.01
            except:
                min_size = 0.01
            if size < min_size:
                print(f"[SIZE ADJUST] {symbol}: {size} → {min_size}", flush=True)
                size = min_size

            params = {}
            if tp and sl:
                params.update({
                    "tpTriggerPx": str(tp), "tpOrdPx": "-1",
                    "slTriggerPx": str(sl), "slOrdPx": "-1"
                })
            order = self.exchange.create_market_order(ccxt_symbol, side.lower(), size, params=params)
            order_id = order.get("id", "")

            # Obtener IDs de las órdenes condicionales (SL/TP)
            sl_order_id = None
            tp_order_id = None
            if tp and sl:
                time.sleep(1)  # breve espera para que se creen las órdenes condicionales
                try:
                    algo_orders = self.exchange.fetch_open_orders(ccxt_symbol, params={"orderType": "algo"})
                    for ao in algo_orders:
                        if ao.get("type") == "stop":
                            sl_order_id = ao.get("id")
                        elif ao.get("type") == "take_profit":
                            tp_order_id = ao.get("id")
                except Exception:
                    pass

            print(f"[ORDER PAYLOAD] {symbol} {side} size={size} tp={tp} sl={sl}", flush=True)
            print(f"[ORDER RESPONSE] order_id={order_id} sl_id={sl_order_id} tp_id={tp_order_id}", flush=True)
            return {
                "order_id": order_id,
                "sl_order_id": sl_order_id,
                "tp_order_id": tp_order_id,
                "status": "filled"
            }
        except Exception as e:
            print(f"[ORDER EXCEPTION] {e}", flush=True)
            return {"order_id": "", "sl_order_id": None, "tp_order_id": None,
                    "status": "failed", "error": str(e)}

    def modify_sl(self, symbol: str, sl_order_id: str, new_sl: float,
                  amount: float, side: str) -> bool:
        if not sl_order_id:
            return False
        try:
            self.exchange.edit_order(
                id=sl_order_id,
                symbol=f"{symbol}/USDT:USDT",
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
        ccxt_symbol = f"{symbol}/USDT:USDT"
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
            self.exchange.cancel_order(order_id, f"{symbol}/USDT:USDT")
            return True
        except Exception as e:
            print(f"[CANCEL ERROR] {e}", flush=True)
            return False
