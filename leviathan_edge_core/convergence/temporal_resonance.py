from datetime import datetime, timezone

class TemporalResonance:
    """
    Detecta patrones de resonancia temporal: momentos del día donde las operaciones
    tienen mayor probabilidad de éxito.
    """
    def __init__(self):
        self.hourly_stats = {h: {"count": 0, "wins": 0} for h in range(24)}

    def update(self, timestamp, pnl):
        if isinstance(timestamp, datetime):
            hour = timestamp.hour
        else:
            hour = datetime.fromtimestamp(timestamp, tz=timezone.utc).hour
        self.hourly_stats[hour]["count"] += 1
        if pnl > 0:
            self.hourly_stats[hour]["wins"] += 1

    def resonance_score(self, hour=None):
        if hour is None:
            hour = datetime.now(timezone.utc).hour
        stats = self.hourly_stats[hour]
        if stats["count"] < 5:
            return 0.5
        return stats["wins"] / stats["count"]
