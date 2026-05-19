from config import Config
import time

class HybridExit:
    @staticmethod
    def should_exit(pos: dict, price: float, now: float, atr_hist: list = None):
        # Protección completa contra claves faltantes
        d = pos.get("dir", 1)
        entry = pos.get("entry", price)
        atr = pos.get("atr", entry * 0.01)

        tp = pos.get("tp", entry + d * Config.TP_ATR * atr)
        sl = pos.get("sl", entry - d * Config.SL_ATR * atr)
        trail_sl = pos.get("trail_sl", sl)
        be_active = pos.get("be_active", False)
        trail_active = pos.get("trail_active", False)

        if not be_active:
            be_th = entry + d * Config.BE_ATR * atr
            if (d == 1 and price >= be_th) or (d == -1 and price <= be_th):
                be_active = True
                cost = entry * 0.0008
                sl = entry + d * cost
                trail_sl = sl

        if be_active and not trail_active:
            act = entry + d * 0.8 * atr
            if (d == 1 and price >= act) or (d == -1 and price <= act):
                trail_active = True
        if trail_active:
            new_trail = price - d * Config.TRAIL_ATR * atr
            if (d == 1 and new_trail > trail_sl) or (d == -1 and new_trail < trail_sl):
                trail_sl = new_trail

        dur_min = (now - pos.get("entry_time", now)) / 60.0
        lev = pos.get("leverage", 5)
        unreal = (price - entry) / entry * d * lev if entry != 0 else 0
        if dur_min > Config.TIME_DECAY_MIN and unreal < 0.002 * lev:
            return True, "time_decay", price, {}

        if atr_hist and len(atr_hist) > 10:
            cur_atr = (max(atr_hist[-10:]) - min(atr_hist[-10:])) / price if price != 0 else 0
            if cur_atr < Config.VOL_CONTRACTION_RATIO * pos.get("atr_pct_entry", 0.01):
                return True, "vol_contraction", price, {}

        if (d == 1 and price >= tp) or (d == -1 and price <= tp):
            return True, "tp", tp, {}
        if (d == 1 and price <= trail_sl) or (d == -1 and price >= trail_sl):
            return True, "trailing_sl", trail_sl, {}

        pos["be_active"] = be_active
        pos["trail_active"] = trail_active
        pos["trail_sl"] = trail_sl
        pos["sl"] = sl
        pos["tp"] = tp
        return False, "", price, pos
