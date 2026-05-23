import copy
import json
import os
import csv
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# LOGGING ROTATIVO (evita duplicados)
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("leviathan_runtime")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "engine.log"),
        maxBytes=1_000_000,
        backupCount=3
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

# ---------------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------------
STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")
TRADES_PATH = os.path.join(os.path.dirname(__file__), "trades.csv")

# ---------------------------------------------------------------------------
# ESTADO POR DEFECTO (deep copy para seguridad)
# ---------------------------------------------------------------------------
DEFAULT_STATE = {
    "balance": 10000.0,
    "equity": 10000.0,
    "position": None,
    "loop_count": 0,
    "last_execution": None,
    "daps_x": 0.0,
    "equilibrium": 1.0,
    "daps_balance": 1.0,
    "status": "BOOT",
    "open_positions": {},
    "last_signal": None,
    "meta": {
        "winrate": 0.0,
        "profit_factor": 0.0,
        "drawdown": 0.0
    },
    "breaker": {
        "loss_streak": 0,
        "peak_equity": None,
        "cooldown_until": 0.0,
        "cooldown_active": False
    }
}

# ---------------------------------------------------------------------------
# FUNCIONES DE PERSISTENCIA
# ---------------------------------------------------------------------------

def load_state():
    """Carga el estado desde state.json. Si el archivo no existe o está
    corrupto, devuelve una copia segura del estado por defecto."""
    if not os.path.exists(STATE_PATH):
        logger.info("state.json no encontrado. Creando estado por defecto.")
        return copy.deepcopy(DEFAULT_STATE)

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            logger.warning("state.json corrupto (no es dict). Usando default.")
            return copy.deepcopy(DEFAULT_STATE)

        # Rellenar campos faltantes sin modificar el default
        for key, value in DEFAULT_STATE.items():
            if key not in state:
                state[key] = copy.deepcopy(value) if isinstance(value, dict) else value
        return state
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Error al leer state.json: %s. Usando default.", e)
        return copy.deepcopy(DEFAULT_STATE)


def save_state(engine, pos_mgr, current_prices=None, breaker=None):
    """
    Guarda el estado actual del motor de forma atómica.

    Parámetros
    ----------
    engine      : RotationalEngine
    pos_mgr     : PositionManager
    current_prices : dict {symbol: price} para calcular unrealized PnL (opcional)
    breaker     : CircuitBreaker (opcional)
    """
    # Equity real = balance + PnL no realizado
    try:
        unreal_pnl = pos_mgr.total_unrealized_pnl(current_prices) if current_prices else 0.0
    except Exception:
        unreal_pnl = 0.0
    equity = engine.capital + unreal_pnl

    state = {
        "balance": float(engine.capital),
        "equity": float(equity),
        "position": engine.position,
        "loop_count": getattr(engine, "_loop_count", 0),
        "last_execution": datetime.now(timezone.utc).isoformat(),
        "daps_x": float(engine.daps.x),
        "equilibrium": float(engine.daps_equilibrium.equilibrium_score),
        "daps_balance": float(getattr(engine.daps_balance, "balance", 1.0)),
        "open_positions": {
            sym: {
                "entry": p.get("entry"),
                "direction": "LONG" if p.get("dir") == 1 else "SHORT",
                "size": p.get("size"),
                "leverage": p.get("leverage"),
                "atr": p.get("atr"),
                "meta_score": p.get("meta_score")
            }
            for sym, p in pos_mgr.positions.items()
        },
        "status": getattr(engine, "status", "RUNNING") if hasattr(engine, "status") else "RUNNING",
        "last_signal": getattr(engine, "last_signal", None),
        "meta": {
            "winrate": float(getattr(engine, "winrate", 0.0)),
            "profit_factor": float(getattr(engine, "profit_factor", 0.0)),
            "drawdown": float(getattr(engine, "max_drawdown", 0.0))
        },
        "breaker": breaker.status() if breaker else DEFAULT_STATE["breaker"]
    }

    tmp_path = STATE_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        os.replace(tmp_path, STATE_PATH)          # atómico
        logger.debug("Estado guardado (atómico).")
    except Exception as e:
        logger.error("Error al guardar state.json: %s", e)


def append_trade(trade_data: dict):
    """Agrega una línea al archivo trades.csv. Crea el archivo si no existe."""
    file_exists = os.path.exists(TRADES_PATH)
    try:
        with open(TRADES_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "symbol", "side", "entry", "exit",
                "pnl", "meta_score", "strategy"
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": trade_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "symbol": trade_data.get("symbol", ""),
                "side": trade_data.get("side", ""),
                "entry": trade_data.get("entry", 0.0),
                "exit": trade_data.get("exit", 0.0),
                "pnl": trade_data.get("pnl", 0.0),
                "meta_score": trade_data.get("meta_score", 0.0),
                "strategy": trade_data.get("strategy", "unknown")
            })
        logger.info("Trade registrado: %s %s PnL=%.2f",
                     trade_data.get("symbol"), trade_data.get("side"),
                     trade_data.get("pnl", 0.0))
    except Exception as e:
        logger.error("Error al guardar trade: %s", e)
