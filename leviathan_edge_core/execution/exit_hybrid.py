from config import Config
import time

class HybridExit:
    """
    Lógica de salida puramente matemática, basada en ATR.
    No depende de ningún exchange ni infraestructura externa.
    Entradas: posición (diccionario con entrada, ATR, dirección, etc.),
              precio actual, timestamp actual, historial de ATR opcional.
    Salidas: (exit_bool, reason, exit_price, updated_position)
    """
    @staticmethod
    def should_exit(pos: dict, price: float, now: float, atr_hist: list = None):
        d = pos.get("dir", 1)          # 1 para LONG, -1 para SHORT
        entry = pos["entry"]
        atr = pos["atr"]
        lev = pos.get("leverage", 5)

        # 1. Cálculo de niveles fijos (Take Profit, Stop Loss)
        tp = entry + d * Config.TP_ATR * atr
        sl = pos.get("sl", entry - d * Config.SL_ATR * atr)
        trail_sl = pos.get("trail_sl", sl)
        be_active = pos.get("be_active", False)
        trail_active = pos.get("trail_active", False)

        # 2. Activación del Break Even
        if not be_active:
            be_th = entry + d * Config.BE_ATR * atr
            if (d == 1 and price >= be_th) or (d == -1 and price <= be_th):
                be_active = True
                cost = entry * 0.0008      # coste de spread/comisión
                sl = entry + d * cost
                trail_sl = sl

        # 3. Activación del Trailing Stop (después del BE)
        if be_active and not trail_active:
            act = entry + d * 0.8 * atr
            if (d == 1 and price >= act) or (d == -1 and price <= act):
                trail_active = True
        if trail_active:
            new_trail = price - d * Config.TRAIL_ATR * atr
            if (d == 1 and new_trail > trail_sl) or (d == -1 and new_trail < trail_sl):
                trail_sl = new_trail

        # 4. Time Decay (salida por tiempo)
        dur_min = (now - pos.get("entry_time", now)) / 60.0
        unreal = (price - entry) / entry * d * lev
        if dur_min > Config.TIME_DECAY_MIN and unreal < 0.002 * lev:
            return True, "time_decay", price, {}

        # 5. Volatility Contraction (salida por compresión de volatilidad)
        if atr_hist and len(atr_hist) > 10:
            cur_atr = (max(atr_hist[-10:]) - min(atr_hist[-10:])) / price
            if cur_atr < Config.VOL_CONTRACTION_RATIO * pos.get("atr_pct_entry", 0.01):
                return True, "vol_contraction", price, {}

        # 6. Disparo de Take Profit
        if (d == 1 and price >= tp) or (d == -1 and price <= tp):
            return True, "tp", tp, {}

        # 7. Disparo del Stop Loss / Trailing Stop
        if (d == 1 and price <= trail_sl) or (d == -1 and price >= trail_sl):
            return True, "trailing_sl", trail_sl, {}

        # 8. Actualizar estado de la posición antes de devolver
        pos["be_active"] = be_active
        pos["trail_active"] = trail_active
        pos["trail_sl"] = trail_sl
        pos["sl"] = sl
        return False, "", price, pos
