import ccxt
from config import Config

class OKXExecutionBridge:
    def __init__(self):
        self.exchange = ccxt.okx({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'password': Config.PASSPHRASE,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'},
            'headers': {'x-simulated-trading': '1'} if Config.EXECUTION_MODE == 'demo' else {}
        })
        if Config.EXECUTION_MODE == 'demo':
            self.exchange.set_sandbox_mode(True)
        self.exchange.load_markets()

    def place_order(self, symbol, side, amount, tp=None, sl=None):
        params = {}
        if tp:
            params['tpTriggerPx'] = tp
            params['tpOrdPx'] = '-1'
        if sl:
            params['slTriggerPx'] = sl
            params['slOrdPx'] = '-1'
        return self.exchange.create_market_order(
            f"{symbol}/USDT:USDT", side.lower(), amount, params=params
        )

    def update_sl(self, symbol, sl_price):
        # OKX requiere modificar la posición, no la orden
        pass

    def update_tp(self, symbol, tp_price):
        pass

    def get_positions(self):
        return self.exchange.fetch_positions()

    def get_balance(self):
        bal = self.exchange.fetch_balance()
        return bal.get('USDT', {}).get('free', 0.0)

    def cancel_order(self, order_id, symbol):
        return self.exchange.cancel_order(order_id, f"{symbol}/USDT:USDT")
