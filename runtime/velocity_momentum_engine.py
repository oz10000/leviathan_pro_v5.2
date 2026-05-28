import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import os, json

class VelocityMomentumEngine:
    def __init__(self, trades_file="runtime/trades.csv", window_days=7):
        self.trades_file = trades_file
        self.window_days = window_days
        self.weights = self._load_weights()

    def _load_weights(self):
        if os.path.exists('runtime/omega_weights.json'):
            with open('runtime/omega_weights.json') as f:
                return json.load(f)
        from config import Config
        return {
            'W_PNL_HOUR': Config.W_PNL_HOUR,
            'W_TP_SPEED': Config.W_TP_SPEED,
            'W_ADX_EFF': Config.W_ADX_EFF,
            'W_VOL_IMPULSE': Config.W_VOL_IMPULSE,
            'W_MOM_PERSISTENCE': Config.W_MOM_PERSISTENCE,
            'W_WINRATE': Config.W_WINRATE
        }

    def compute_adx_atr(self, df_ohlc, period=14):
        high = df_ohlc['high']
        low = df_ohlc['low']
        close = df_ohlc['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        atr_norm = atr / close.iloc[-1] if close.iloc[-1] != 0 else 0.0
        up = high.diff()
        down = -low.diff()
        plus_dm = np.where((up > down) & (up > 0), up, 0.0)
        minus_dm = np.where((down > up) & (down > 0), down, 0.0)
        atr_dm = tr.rolling(period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / atr_dm)
        minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / atr_dm)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean().iloc[-1]
        return adx, atr_norm

    def load_trades(self):
        if not os.path.exists(self.trades_file):
            return pd.DataFrame()
        df = pd.read_csv(self.trades_file)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        for col in ['entry','exit','pnl','meta_score','duration','tp_time','sl_time']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def calculate_omega_temporal(self, df, adx=None, atr_norm=None):
        if df.empty or len(df) < 5:
            return 0.0
        total_pnl = df['pnl'].sum()
        total_hours = df['duration'].sum() / 60.0 if 'duration' in df.columns else len(df) * 3
        pnl_per_hour = total_pnl / total_hours if total_hours > 0 else 0.0
        tp_trades = df[df['tp_time'].notnull()] if 'tp_time' in df.columns else pd.DataFrame()
        avg_tp_speed = tp_trades['tp_time'].mean() / 60.0 if not tp_trades.empty else 999
        tp_speed_score = max(0.0, 1.0 - avg_tp_speed / 300)
        adx_eff = (adx / 100.0) if adx is not None else (df['meta_score'].mean() / 100.0)
        vol_impulse = min(1.0, len(df) / 20)
        if len(df) >= 2:
            pnl_series = df['pnl'].values
            autocorr = np.corrcoef(pnl_series[:-1], pnl_series[1:])[0,1]
            mom_persistence = max(0.0, autocorr)
        else:
            mom_persistence = 0.5
        wins = (df['pnl'] > 0).sum()
        winrate = wins / len(df) if len(df) > 0 else 0.0
        cumulative = df['pnl'].cumsum()
        max_dd = abs(cumulative.min() - cumulative.max()) / abs(cumulative.max()) if len(cumulative) > 0 and cumulative.max() > 0 else 1.0
        exposure_penalty = 1.0 / (1.0 + total_hours)
        omega = (
            self.weights['W_PNL_HOUR'] * pnl_per_hour +
            self.weights['W_TP_SPEED'] * tp_speed_score * 10 +
            self.weights['W_ADX_EFF'] * adx_eff * 10 +
            self.weights['W_VOL_IMPULSE'] * vol_impulse * 5 +
            self.weights['W_MOM_PERSISTENCE'] * mom_persistence * 5 +
            self.weights['W_WINRATE'] * (winrate ** 2) * 10
        ) * exposure_penalty / (max_dd + 1)
        return round(omega, 4)

    def rank_assets(self, symbols, market_data=None):
        df = self.load_trades()
        if df.empty:
            return {}
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        recent = df[df['timestamp'] >= cutoff]
        scores = {}
        for sym in symbols:
            sym_data = recent[recent['symbol'] == sym]
            if len(sym_data) >= 5:
                adx, atr_norm = None, None
                if market_data and sym in market_data:
                    ohlc = market_data[sym].get('5m')
                    if ohlc is not None and len(ohlc) >= 14:
                        adx, atr_norm = self.compute_adx_atr(ohlc)
                scores[sym] = self.calculate_omega_temporal(sym_data, adx, atr_norm)
        return scores

    def optimal_universe(self, symbols, market_data=None, min_n=5, max_n=20):
        scores = self.rank_assets(symbols, market_data)
        if not scores:
            return symbols[:min_n]
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [s for s, sc in sorted_scores if sc > 0][:max_n]
        if len(selected) < min_n:
            selected = [s for s, _ in sorted_scores[:min_n]]
        return selected
