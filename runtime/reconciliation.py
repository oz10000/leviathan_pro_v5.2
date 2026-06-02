from datetime import datetime, timezone

def reconcile_positions(state, exchange, pos_mgr):
    """Sincroniza las posiciones locales con las del exchange."""
    exchange_positions = exchange.get_positions()
    for pos in exchange_positions:
        if float(pos.get('contracts', 0)) == 0:
            continue
        symbol = pos['symbol'].replace('/USDT:USDT', '')
        if symbol not in pos_mgr.positions:
            pos_mgr.positions[symbol] = {
                'symbol': symbol,
                'dir': 1 if pos['side'] == 'long' else -1,
                'entry': float(pos['entryPrice']),
                'size': float(pos['contracts']),
                'leverage': float(pos['leverage']),
                'atr': 0.0,
                'meta_score': 0.0,
                'entry_time': datetime.now(timezone.utc).timestamp()
            }
            print(f"[RECONCILE] Posición {symbol} restaurada desde exchange", flush=True)
    for sym in list(pos_mgr.positions.keys()):
        if not any(p['symbol'].replace('/USDT:USDT', '') == sym for p in exchange_positions):
            pos_mgr.close(sym, 0, 'sync')
            print(f"[RECONCILE] Posición {sym} eliminada localmente", flush=True)
