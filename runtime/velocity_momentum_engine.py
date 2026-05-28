import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

class VelocityMomentumEngine:
    """Clasifica los activos por su capacidad de generar PnL rápidamente."""

    def __init__(self, trades_file="runtime/trades.csv", window_days=7):
        self.trades_file = trades_file
        self.window_days = window_days

    def load_trades(self):
        if not os.path.exists(self.trades_file):
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.trades_file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            for col in ['entry', 'exit', 'pnl', 'meta_score', 'duration', 'tp_time', 'sl_time']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_omega_temporal(self, df):
        """Calcula el Omega Temporal Score para un activo."""
        if df.empty or len(df) < 5:
            return 0.0

        total_pnl = df['pnl'].sum()
        total_hours = df['duration'].sum() / 60.0 if 'duration' in df.columns else len(df) * 3
        pnl_per_hour = total_pnl / total_hours if total_hours > 0 else 0.0

        tp_trades = df[df['tp_time'].notnull()] if 'tp_time' in df.columns else pd.DataFrame()
        avg_tp_speed = tp_trades['tp_time'].mean() / 60.0 if not tp_trades.empty else 999
        tp_speed_score = max(0.0, 1.0 - avg_tp_speed / 300)

        adx_eff = df['meta_score'].mean() / 100.0 if 'meta_score' in df.columns else 0.5
        vol_impulse = min(1.0, len(df) / 20)

        if len(df) >= 2:
            pnl_series = df['pnl'].values
            autocorr = np.corrcoef(pnl_series[:-1], pnl_series[1:])[0, 1]
            mom_persistence = max(0.0, autocorr)
        else:
            mom_persistence = 0.5

        wins = (df['pnl'] > 0).sum()
        winrate = wins / len(df) if len(df) > 0 else 0.0

        cumulative = df['pnl'].cumsum()
        max_dd = abs(cumulative.min() - cumulative.max()) / abs(cumulative.max()) if len(cumulative) > 0 and cumulative.max() > 0 else 1.0
        exposure_penalty = 1.0 / (1.0 + total_hours)

        from config import Config
        w = Config
        omega = (
            w.W_PNL_HOUR * pnl_per_hour +
            w.W_TP_SPEED * tp_speed_score * 10 +
            w.W_ADX_EFF * adx_eff * 10 +
            w.W_VOL_IMPULSE * vol_impulse * 5 +
            w.W_MOM_PERSISTENCE * mom_persistence * 5 +
            w.W_WINRATE * (winrate ** 2) * 10
        ) * exposure_penalty / (max_dd + 1)

        return round(omega, 4)

    def rank_assets(self, symbols):
        """Retorna un dict con el Omega Temporal Score de cada activo."""
        df = self.load_trades()
        if df.empty:
            return {}

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        recent = df[df['timestamp'] >= cutoff]

        scores = {}
        for sym in symbols:
            sym_data = recent[recent['symbol'] == sym]
            if len(sym_data) >= 5:
                scores[sym] = self.calculate_omega_temporal(sym_data)
        return scores

    def optimal_universe(self, symbols, min_n=5, max_n=20):
        """Determina dinámicamente el número óptimo de activos."""
        scores = self.rank_assets(symbols)
        if not scores:
            return symbols[:min_n]

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [s for s, sc in sorted_scores if sc > 0][:max_n]
        if len(selected) < min_n:
            selected = [s for s, _ in sorted_scores[:min_n]]
        return selected
