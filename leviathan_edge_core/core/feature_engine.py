import numpy as np
import pandas as pd

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # --- Asegurar que existe la columna 'volume' ---
    if "volume" not in df.columns and "vol" in df.columns:
        df.rename(columns={"vol": "volume"}, inplace=True)
    if "volume" not in df.columns and "volCcy" in df.columns:
        # Último recurso: usar volCcy como volumen
        df.rename(columns={"volCcy": "volume"}, inplace=True)
    if "volume" not in df.columns:
        df["volume"] = 1.0  # valor mínimo para evitar división por cero

    df["prev_close"] = df["close"].shift(1)
    df["tr"] = np.maximum(df["high"] - df["low"],
                          np.maximum(abs(df["high"] - df["prev_close"]),
                                     abs(df["low"] - df["prev_close"])))
    df["atr"] = df["tr"].rolling(14).mean()
    df["atr_pct"] = df["atr"] / df["close"]
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["slope_ema20"] = df["ema20"].diff(5) / df["ema20"].shift(5)
    df["volume_avg"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_avg"]
    df["momentum"] = df["close"].pct_change(5)
    df["rsi_14"] = compute_rsi(df["close"], 14)
    macd_line, signal_line, histogram = compute_macd(df["close"])
    df["macd_line"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = histogram

    df["trend"] = np.where(df["ema20"] > df["ema50"], "BULL",
                           np.where(df["ema20"] < df["ema50"], "BEAR", "NEUTRAL"))
    df["trend_score"] = np.where(
        (df["ema20"] > df["ema50"]) & (df["slope_ema20"] > 0), 100,
        np.where((df["ema20"] > df["ema50"]) & (df["slope_ema20"] <= 0), 70,
                 np.where((df["ema20"] < df["ema50"]) & (df["slope_ema20"] < 0), 0, 30)))
    df["volatility_score"] = (100 - np.abs(df["atr_pct"] - 0.01) * 10000).clip(0, 100)
    df["volume_score"] = ((df["volume_ratio"].clip(0.5, 2) - 0.5) / 1.5 * 100)
    df["momentum_score"] = df["momentum"].rolling(50).rank(pct=True) * 100
    from config import Config
    df["score"] = (Config.W_TREND * df["trend_score"] + Config.W_MOMENTUM * df["momentum_score"] +
                   Config.W_VOL_EFF * df["volatility_score"] + Config.W_VOLUME * df["volume_score"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0.0).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
