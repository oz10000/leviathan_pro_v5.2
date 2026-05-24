from abc import ABC, abstractmethod
import pandas as pd

class ExchangeConnector(ABC):
    @abstractmethod
    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        ...

    @abstractmethod
    def fetch_tickers(self) -> list:
        ...

    @abstractmethod
    def place_order(self, symbol: str, side: str, size: float,
                    pos_side: str, tp: float = None, sl: float = None) -> dict:
        ...

    @abstractmethod
    def close_position(self, symbol: str, pos_side: str) -> dict:
        ...

    @abstractmethod
    def get_positions(self) -> dict:
        ...

    @abstractmethod
    def get_balance(self) -> float:
        ...

    @abstractmethod
    def normalize_symbol(self, raw_symbol: str) -> str:
        ...
