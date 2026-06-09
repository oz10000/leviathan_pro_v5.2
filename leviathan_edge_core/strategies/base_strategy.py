from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseStrategy(ABC):
    """Clase base de la que heredan todas las estrategias de entrada."""

    @abstractmethod
    def calculate_score(self, symbol: str, features: Dict[str, Any]) -> float:
        """
        Calcula una puntuación entre 0 y 100 para un símbolo dado.
        - symbol: ID del instrumento (ej. "BTC-USDT-SWAP")
        - features: diccionario con ATR, EMA, RSI, MACD, etc.
        """
        pass
