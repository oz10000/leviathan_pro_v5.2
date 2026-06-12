# PATCH E3: añadir aliases para OKXClient (usa Config.OKX_API_KEY etc.)
# PATCH E4: añadir MIN_VOL24H
# PATCH E5: añadir TP_ATR, BE_ATR, TRAIL_ATR, TIME_DECAY_MIN, VOL_CONTRACTION_RATIO
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ─── MODO DE OPERACIÓN ───
    LIVE = os.getenv("LIVE", "false").lower() in ("true", "1", "yes")

    # ─── CREDENCIALES ───
    if LIVE:
        API_KEY = os.getenv("OKX_LIVE_API_KEY", "")
        SECRET = os.getenv("OKX_LIVE_SECRET", "")
        PASSPHRASE = os.getenv("OKX_LIVE_PASSPHRASE", "")
    else:
        API_KEY = os.getenv("OKX_DEMO_API_KEY", "")
        SECRET = os.getenv("OKX_DEMO_SECRET", "")
        PASSPHRASE = os.getenv("OKX_DEMO_PASSPHRASE", "")

    # PATCH E3: aliases exactos que usa OKXClient
    OKX_API_KEY = API_KEY
    OKX_API_SECRET = SECRET
    OKX_API_PASSPHRASE = PASSPHRASE
    OKX_DEMO = not LIVE
    REST_URL = "https://www.okx.com"

    DEMO = not LIVE
    BASE_URL = "https://www.okx.com"

    # ─── PARÁMETROS DE TRADING ───
    CAPITAL = float(os.getenv("CAPITAL", "10000"))
    MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "8"))
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
    MAX_EXPOSURE = float(os.getenv("MAX_EXPOSURE", "0.3"))
    KELLY_SAFE_FACTOR = float(os.getenv("KELLY_SAFE_FACTOR", "0.25"))

    # ─── FILTROS Y EDGE ───
    MTF_CONVERGENCE_THRESHOLD = 0.65
    DIVERGENCE_MAX_TOLERANCE = 0.35
    ENTROPY_MAX_ALLOWED = 0.70
    SL_ATR = 1.5

    # PATCH E5: constantes de salida usadas por exit_hybrid.py
    TP_ATR = float(os.getenv("TP_ATR", "2.0"))
    BE_ATR = float(os.getenv("BE_ATR", "1.0"))
    TRAIL_ATR = float(os.getenv("TRAIL_ATR", "1.0"))
    TIME_DECAY_MIN = float(os.getenv("TIME_DECAY_MIN", "120.0"))
    VOL_CONTRACTION_RATIO = float(os.getenv("VOL_CONTRACTION_RATIO", "0.5"))

    # PATCH E4: volumen mínimo para top100_selector
    MIN_VOL24H = float(os.getenv("MIN_VOL24H", "1000000"))

    # ─── PARÁMETROS DE CICLO ───
    CYCLE_DURATION_MINUTES = int(os.getenv("CYCLE_DURATION_MINUTES", "230"))
    EDGE_ALERT_THRESHOLD = float(os.getenv("EDGE_ALERT_THRESHOLD", "1.15"))
    DAPS_DECAY_LAMBDA = float(os.getenv("DAPS_DECAY_LAMBDA", "0.99"))

    # ─── ALERTAS ───
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # ─── PERSISTENCIA ───
    DB_PATH = os.getenv("DB_PATH", "leviathan.db")
