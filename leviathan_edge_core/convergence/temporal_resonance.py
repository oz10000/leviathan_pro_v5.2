from datetime import datetime

class TemporalResonance:
    def __init__(self):
        self.hour_perf = {}
        self.session_perf = {}

    def update(self, dt: datetime, pnl: float):
        hour = dt.hour
        session = "ASIA" if 0 <= hour < 8 else "EU" if 8 <= hour < 16 else "US"
        self.hour_perf.setdefault(hour, []).append(pnl)
        self.session_perf.setdefault(session, []).append(pnl)

    def hour_score(self, hour: int) -> float:
        pnls = self.hour_perf.get(hour, [])
        if not pnls:
            return 0.5
        wr = sum(1 for p in pnls if p > 0) / len(pnls)
        return wr

    def session_score(self, dt: datetime) -> float:
        hour = dt.hour
        session = "ASIA" if 0 <= hour < 8 else "EU" if 8 <= hour < 16 else "US"
        return self.hour_score(hour) * 0.7 + self.session_score_raw(session) * 0.3

    def session_score_raw(self, session: str) -> float:
        pnls = self.session_perf.get(session, [])
        if not pnls:
            return 0.5
        return sum(1 for p in pnls if p > 0) / len(pnls)
