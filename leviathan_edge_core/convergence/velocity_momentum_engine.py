import requests
from config import Config

class VelocityMomentumEngine:
    """
    Selecciona los activos con mayor velocidad y momentum utilizando
    los datos públicos de tickers de OKX (24h).
    Devuelve los top_n símbolos ordenados por un Omega Score compuesto.
    """
    def __init__(self, momentum_weight=0.6, velocity_weight=0.4):
        self.momentum_weight = momentum_weight
        self.velocity_weight = velocity_weight
        self.tickers_url = f"{Config.REST_URL}/api/v5/market/tickers?instType=SWAP"

    def filter(self, symbols: list, top_n: int = 12) -> list:
        """
        symbols: lista de símbolos candidatos (top 100).
        top_n: cuántos devolver.
        Retorna los top_n símbolos con mayor Omega Score.
        """
        if not symbols:
            return []

        # Obtener datos de todos los tickers SWAP (público, no requiere autenticación)
        try:
            resp = requests.get(self.tickers_url, timeout=10)
            data = resp.json().get("data", [])
        except Exception:
            return symbols[:top_n]  # fallback seguro

        # Construir diccionario symbol -> datos del ticker
        ticker_map = {item["instId"]: item for item in data if item.get("instId") in symbols}

        scores = {}
        for sym in symbols:
            tick = ticker_map.get(sym)
            if tick is None:
                continue

            # Momentum: cambio porcentual 24h
            open24h = float(tick.get("open24h", 0))
            last = float(tick.get("last", 0))
            if open24h > 0:
                momentum = (last - open24h) / open24h * 100  # porcentaje
            else:
                momentum = 0.0

            # Velocidad: combinación de volumen 24h y rango (high-low)
            vol24h = float(tick.get("vol24h", 0))
            high24h = float(tick.get("high24h", 0))
            low24h = float(tick.get("low24h", 0))
            velocity = vol24h * (high24h - low24h) if low24h > 0 else 0.0
            # Normalización simple (dividir entre el promedio de volumen*rango de los símbolos)
            # Como es ranking, valores absolutos no necesitan normalización perfecta.

            omega = (self.momentum_weight * momentum) + (self.velocity_weight * velocity * 1e-6)
            scores[sym] = omega

        sorted_syms = sorted(scores, key=scores.get, reverse=True)
        return sorted_syms[:top_n] if sorted_syms else symbols[:top_n]
