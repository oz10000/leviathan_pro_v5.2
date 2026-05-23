import os
import pandas as pd
import logging

logger = logging.getLogger("leviathan_runtime.cache")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(symbol: str, timeframe: str) -> str:
    tf = timeframe.lower().replace(" ", "")
    return os.path.join(CACHE_DIR, f"{symbol}_{tf}.parquet")


def load_or_fetch(symbol: str, timeframe: str, fetch_func, limit: int = 200):
    """
    Carga datos desde caché Parquet. Si no existe o faltan velas recientes,
    descarga únicamente lo necesario y actualiza el archivo.

    Parámetros
    ----------
    symbol    : str
    timeframe : str  (ej. '5m', '15m', '1H')
    fetch_func: callable(symbol, timeframe, limit) -> DataFrame
                Debe retornar un DataFrame con columnas:
                ts, open, high, low, close, vol
    limit     : int
                Número máximo de velas a solicitar a la API.
    """
    path = _cache_path(symbol, timeframe)

    # --- Intentar cargar caché existente -----------------------------------
    if os.path.exists(path):
        try:
            df_cached = pd.read_parquet(path)
            if not df_cached.empty and 'ts' in df_cached.columns:
                df_cached['ts'] = pd.to_datetime(df_cached['ts'])
                last_ts = df_cached['ts'].max()

                # Descargar velas nuevas
                df_new = fetch_func(symbol, timeframe, limit=limit)
                if df_new is None or df_new.empty:
                    logger.warning(
                        "Sin datos nuevos para %s %s, usando caché", symbol, timeframe
                    )
                    return df_cached

                df_new['ts'] = pd.to_datetime(df_new['ts'])
                df_fresh = df_new[df_new['ts'] > last_ts]

                if not df_fresh.empty:
                    df_combined = pd.concat([df_cached, df_fresh], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['ts'])
                    df_combined = df_combined.sort_values('ts')
                else:
                    df_combined = df_cached

                # Limitar tamaño máximo del caché
                if len(df_combined) > 500:
                    df_combined = df_combined.iloc[-500:]

                df_combined.to_parquet(path, index=False)
                return df_combined

        except Exception as e:
            logger.error("Error leyendo caché %s: %s. Redescargando.", path, e)

    # --- Descarga completa (primera vez o tras error) -----------------------
    df = fetch_func(symbol, timeframe, limit=limit)
    if df is not None and not df.empty:
        df['ts'] = pd.to_datetime(df['ts'])
        df = df.drop_duplicates(subset=['ts']).sort_values('ts')
        if len(df) > 500:
            df = df.iloc[-500:]
        df.to_parquet(path, index=False)

    return df
