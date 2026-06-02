import os
import math

class Config:
    # ── Modo de ejecución ─────────────────────────────────────
    EXECUTION_MODE = "demo"             # paper | demo | live
    EXCHANGE = "OKX"
    BASE_URL = "https://www.okx.com"

    # ── OKX Credenciales ──────────────────────────────────────
    OKX_API_KEY = os.getenv("OKX_API_KEY", "76254b4d-2126-4bb5-a0f1-8c0aa463d90e")
    OKX_API_SECRET = os.getenv("OKX_API_SECRET", "36F40E60584E4561E1E2475B979ABDDF")
    OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "Waly200381!")

    # ── Toggles de módulos ────────────────────────────────────
    ENABLE_WALK_FORWARD = True
    ENABLE_ADX_REAL = True
    ENABLE_ATR_NORMALIZED = True
    ENABLE_NETWORK_MONITOR = True
    ENABLE_LATENCY_TRACKING = True
    ENABLE_VELOCITY_MOMENTUM = True
    AUTO_UNIVERSE_OPTIMIZATION = True

    # ── Velocity-Momentum Engine ──────────────────────────────
    MAX_TOP_N = 20
    MIN_TOP_N = 5
    VELOCITY_MIN_TRADES = 5
    W_PNL_HOUR = 0.35
    W_TP_SPEED = 0.20
    W_ADX_EFF = 0.15
    W_VOL_IMPULSE = 0.10
    W_MOM_PERSISTENCE = 0.10
    W_WINRATE = 0.10

    # ── Pydroid ──────────────────────────────────────────────
    PYDROID_MODE = False

    # ── Universo base ─────────────────────────────────────────
    TOP_N = 100
    MIN_VOL24H = 5_000_000

    # ── Scoring del Edge (congelado) ──────────────────────────
    W_TREND, W_MOMENTUM, W_VOL_EFF, W_VOLUME = 0.30, 0.25, 0.25, 0.20
    SCORE_THRESHOLD = 68
    FEATURE_WEIGHTS = {
        "volume_impulse": 0.22, "alignment_5m_15m": 0.18,
        "macd_momentum": 0.15, "trend_strength": 0.15,
        "atr_expansion": 0.12, "rsi_regime": 0.10,
        "volatility_regime": 0.08,
    }

    ACTIVE_STRATEGIES = ["expansion", "pullback", "reacceleration", "depression_breakout"]
    LEVERAGE_CAPS = {"expansion": 7, "pullback": 5, "reacceleration": 5, "depression_breakout": 5}
    LONG_FACTOR, SHORT_FACTOR = 1.0, 0.8

    KELLY_FRACTION = 0.25
    RISK_CAP = 0.04
    MAX_DD_LIMIT = 0.15

    TP_ATR, SL_ATR, BE_ATR, TRAIL_ATR = 2.5, 0.7, 0.6, 1.3
    TIME_DECAY_MIN = 180
    VOL_CONTRACTION_RATIO = 0.7

    MAX_ALLOCATION = 0.15
    SOFTMAX_TEMP = 2.0

    MIN_WINRATE, MAX_DD, MIN_SHARPE = 0.83, 0.045, 4.0
    WFO_STABILITY = 0.85
    MAX_SLIPPAGE = 0.0003

    EDGE_ALPHA_SHORT, EDGE_ALPHA_LONG, EDGE_THETA_STD_FACTOR = 0.10, 0.03, 0.5
    ERA_ATR_PERC, ERA_VOL_MULT, ERA_LEV_MULT, ERA_CAPITAL_MULT, ERA_TRAIL_MULT = 90, 2.5, 0.4, 0.5, 0.7

    PI = math.pi
    DAPS_INIT_ALPHA, DAPS_INIT_BETA, DAPS_INIT_GAMMA = 0.33, 0.34, 0.33
    DAPS_DECAY = 0.05
    DAPS_EQUILIBRIUM_TARGET = 0.0

    MTF_CONVERGENCE_THRESHOLD = 0.65
    DIVERGENCE_MAX_TOLERANCE = 0.35
    ENTROPY_MAX_ALLOWED = 0.70
    FRACTAL_CONFIRMATION_WEIGHT = 0.15
    TEMPORAL_RESONANCE_WEIGHT = 0.10
    CAUSALITY_WEIGHT = 0.20
    LEVERAGE_SAFETY_SHARPE_MIN = 5.0
    SAFE_LEVERAGE_MAX = 8.0
    SAFE_LEVERAGE_MIN = 1.5
    TRADE_QUALITY_MIN_SCORE = 0.70
    LOSS_CAUSALITY_LOOKBACK = 50
