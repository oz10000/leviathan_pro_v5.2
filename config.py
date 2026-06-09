import os
from dotenv import load_dotenv

# ─── Carga de variables de entorno (.env) ───
load_dotenv()

class Config:
    # ─── MODO DE OPERACIÓN ───
    # Cambia a "live" cuando uses dinero real.
    LIVE = os.getenv("LIVE", "false").lower() in ("true", "1", "yes")

    # ─── CREDENCIALES ───
    # Opción 1 (RECOMENDADA): variables de entorno / .env
    if LIVE:
        API_KEY = os.getenv("OKX_LIVE_API_KEY", "")
        SECRET = os.getenv("OKX_LIVE_SECRET", "")
        PASSPHRASE = os.getenv("OKX_LIVE_PASSPHRASE", "")
    else:
        API_KEY = os.getenv("OKX_DEMO_API_KEY", "")
        SECRET = os.getenv("OKX_DEMO_SECRET", "")
        PASSPHRASE = os.getenv("OKX_DEMO_PASSPHRASE", "")

    # Opción 2 (INSEGURA): hardcodear las claves aquí.
    # Descomenta las líneas de abajo y comenta el bloque de arriba.
    # if LIVE:
    #     API_KEY = "tu-api-key-live"
    #     SECRET = "tu-secret-live"
    #     PASSPHRASE = "tu-passphrase-live"
    # else:
    #     API_KEY = "tu-api-key-demo"
    #     SECRET = "tu-secret-demo"
    #     PASSPHRASE = "tu-passphrase-demo"

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
    MTF_THRESHOLD = 0.65
    ENTROPY_THRESHOLD = 0.70
    DIVERGENCE_THRESHOLD = 0.35

    # ─── PARÁMETROS DE CICLO ───
    CYCLE_DURATION_MINUTES = int(os.getenv("CYCLE_DURATION_MINUTES", "230"))   # 3h50m
    EDGE_ALERT_THRESHOLD = float(os.getenv("EDGE_ALERT_THRESHOLD", "1.15"))
    DAPS_DECAY_LAMBDA = float(os.getenv("DAPS_DECAY_LAMBDA", "0.99"))

    # ─── ALERTAS ───
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
