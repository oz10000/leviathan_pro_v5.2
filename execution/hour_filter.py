from datetime import datetime, timezone

class HourFilter:
    """
    Evita operar en horas UTC de baja liquidez.
    """

    @staticmethod
    def is_tradeable_hour() -> bool:
        h = datetime.now(timezone.utc).hour
        blocked = {2, 3, 4, 11, 17}
        return h not in blocked
