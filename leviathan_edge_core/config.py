import os, math

class Config:
    TESTNET = True  # not used in edge core, but kept for compatibility
    INITIAL_CAPITAL = 100.0
    MAX_ALLOCATION = 0.15
    RISK_CAP = 0.04
    KELLY_FRACTION = 0.25
    LEVERAGE_CAPS = {"expansion": 7, "pullback": 5, "reacceleration": 5, "depression_breakout": 5}
    LONG_FACTOR, SHORT_FACTOR = 1.0, 0.8

    W_TREND, W_MOMENTUM, W_VOL_EFF, W_VOLUME = 0.30, 0.25, 0.25, 0.20
    SCORE_THRESHOLD = 68
    FEATURE_WEIGHTS = {
        "volume_impulse": 0.22, "alignment_5m_15m": 0.18,
        "macd_momentum": 0.15, "trend_strength": 0.15,
        "atr_expansion": 0.12, "rsi_regime": 0.10,
        "volatility_regime": 0.08,
    }

    ACTIVE_STRATEGIES = ["expansion", "pullback", "reacceleration", "depression_breakout"]

    TP_ATR, SL_ATR, BE_ATR, TRAIL_ATR = 2.5, 0.7, 0.6, 1.3
    TIME_DECAY_MIN = 180
    VOL_CONTRACTION_RATIO = 0.7
    MAX_SLIPPAGE = 0.0003

    PI = math.pi
    DAPS_INIT_ALPHA, DAPS_INIT_BETA, DAPS_INIT_GAMMA = 0.33, 0.34, 0.33
    DAPS_DECAY = 0.05
    DAPS_EQUILIBRIUM_TARGET = 0.0

    MTF_CONVERGENCE_THRESHOLD = 0.65
    DIVERGENCE_MAX_TOLERANCE = 0.35
    ENTROPY_MAX_ALLOWED = 0.7
    FRACTAL_CONFIRMATION_WEIGHT = 0.15
    TEMPORAL_RESONANCE_WEIGHT = 0.10
    CAUSALITY_WEIGHT = 0.20
    LEVERAGE_SAFETY_SHARPE_MIN = 5.0
    SAFE_LEVERAGE_MAX = 8.0
    SAFE_LEVERAGE_MIN = 1.5
    TRADE_QUALITY_MIN_SCORE = 0.70
    LOSS_CAUSALITY_LOOKBACK = 50

    MIN_TRADES_PRUNE = 20
    SHARPE_PRUNE_THRESHOLD = 3.0
    WINRATE_PRUNE_THRESHOLD = 0.60
    FAKE_BREAKOUT_PRUNE_THRESHOLD = 0.15
    ENTROPY_PRUNE_LIMIT = 0.7
    PRUNE_CHECK_HOUR = 0

    HOUR_MIN_TRADES = 5
    HOUR_NEGATIVE_THRESHOLD = -0.5
    HOUR_WINRATE_THRESHOLD = 0.40

    CORR_BASKET_LIMIT = 0.7

    EDGE_ALPHA_SHORT, EDGE_ALPHA_LONG, EDGE_THETA_STD_FACTOR = 0.10, 0.03, 0.5
    ERA_ATR_PERC, ERA_VOL_MULT, ERA_LEV_MULT, ERA_CAPITAL_MULT, ERA_TRAIL_MULT = 90, 2.5, 0.4, 0.5, 0.7
