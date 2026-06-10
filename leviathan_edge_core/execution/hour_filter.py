from datetime import datetime, timezone

class HourFilter:
    """Filtro horario para evitar operar en horas de baja liquidez."""
    @staticmethod
    def is_tradeable_hour():
        now = datetime.now(timezone.utc)
        if 22 <= now.hour or now.hour < 6:
            return False
        return True
