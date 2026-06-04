import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Credenciales OKX (nunca en el código)
    OKX_API_KEY = os.getenv("OKX_API_KEY")
    OKX_API_SECRET = os.getenv("OKX_API_SECRET")
    OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

    # Modo demo/live
    OKX_DEMO = os.getenv("OKX_DEMO", "True").lower() in ("true", "1", "yes")

    # URLs de OKX (no requieren cambio)
    REST_URL = "https://www.okx.com"
    WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
    WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"

    # Trading
    CAPITAL = float(os.getenv("CAPITAL", "10000"))
    MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "8"))
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
    MAX_EXPOSURE = float(os.getenv("MAX_EXPOSURE", "0.3"))
    RISK_CAP = float(os.getenv("RISK_CAP", "0.04"))

    # Edge / Filtros
    MTF_THRESHOLD = 0.65
    ENTROPY_THRESHOLD = 0.70
    DIVERGENCE_THRESHOLD = 0.35
    KELLY_SAFE_FACTOR = 0.25

    # WebSocket
    WS_ENABLED = os.getenv("WS_ENABLED", "True").lower() in ("true", "1", "yes")
    WS_PING_INTERVAL = 20

    # Base de datos
    DB_PATH = os.getenv("DB_PATH", "leviathan.db")

    # Alertas Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
