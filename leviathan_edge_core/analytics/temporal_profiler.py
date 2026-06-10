from datetime import datetime, timezone

class TemporalProfiler:
    """
    Analiza patrones temporales en el rendimiento de las operaciones.
    Identifica las mejores y peores horas del día para operar.
    """
    def __init__(self):
        self.hourly_pnl = {h: [] for h in range(24)}

    def add_trade(self, timestamp, pnl):
        hour = timestamp.hour if isinstance(timestamp, datetime) else datetime.fromtimestamp(timestamp, tz=timezone.utc).hour
        self.hourly_pnl[hour].append(pnl)

    def best_hours(self, top_n=3):
        avg = {h: sum(p) / len(p) for h, p in self.hourly_pnl.items() if p}
        return sorted(avg, key=avg.get, reverse=True)[:top_n]

    def worst_hours(self, top_n=3):
        avg = {h: sum(p) / len(p) for h, p in self.hourly_pnl.items() if p}
        return sorted(avg, key=avg.get)[:top_n]
