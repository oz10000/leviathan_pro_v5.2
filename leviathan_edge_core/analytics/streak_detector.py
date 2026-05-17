import numpy as np
import pandas as pd

class StreakDetector:
    def __init__(self):
        self.trade_log = []

    def add_trade(self, trade: dict):
        self.trade_log.append(trade)

    def analyze(self, lookback=100):
        if len(self.trade_log) < 20:
            return {"positive_persistence": 0.0, "context_strength": 0.0}
        df = pd.DataFrame(self.trade_log[-lookback:])
        df['pnl'] = df.get('pnl', 0)
        df['win'] = (df['pnl'] > 0).astype(int)
        df['hour'] = pd.to_datetime(df['time']).dt.hour
        df['weekday'] = pd.to_datetime(df['time']).dt.weekday
        df['session'] = df['hour'].apply(lambda h: 'ASIA' if 0 <= h < 8 else 'EU' if 8 <= h < 16 else 'US')
        contexts = df.groupby(['weekday', 'hour', 'session']).agg(
            winrate=('win', 'mean'), count=('win', 'count'), total_pnl=('pnl', 'sum')
        ).reset_index()
        contexts = contexts[contexts['count'] >= 3]
        if contexts.empty:
            return {"positive_persistence": 0.0, "context_strength": 0.0}
        contexts['score'] = contexts['winrate'] * np.sqrt(contexts['count'])
        max_score = contexts['score'].max()
        positive = contexts[contexts['winrate'] > 0.55]['score'].sum() / contexts['score'].sum() if contexts['score'].sum() > 0 else 0
        return {"positive_persistence": float(positive), "context_strength": float(max_score / 10)}
