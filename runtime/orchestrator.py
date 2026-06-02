#!/usr/bin/env python3
"""
Leviathan V5.2B – Orchestrator 24/7 con loop continuo y timeout guard.
Incluye state manager, reconciliación, logging estructurado y confirmación real de órdenes.
"""

import sys, os, time, json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "leviathan_edge_core"))

from config import Config
from core.feature_engine import compute_features
from strategies.expansion_strategy import ExpansionStrategy
from strategies.pullback_strategy import PullbackStrategy
from strategies.reacceleration_strategy import ReaccelerationStrategy
from strategies.depression_breakout import DepressionBreakoutStrategy
from execution.okx_api_connector import OKXConnector
from execution.order_router import OrderRouter
from execution.position_manager import PositionManager
from execution.rotational_engine import RotationalEngine
from execution.exit_hybrid import HybridExit
from portfolio.top100_selector import fetch_top100_symbols
from runtime.persistence_engine import load_state, save_state, append_trade, logger
from runtime.circuit_breaker import CircuitBreaker
from runtime.observability import RuntimeMetrics
from runtime.market_data_cache import load_or_fetch
from runtime.control import load_control, save_control
from runtime.velocity_momentum_engine import VelocityMomentumEngine
from runtime.pnl_tracker import PnLTracker
from runtime.reconciliation import reconcile_positions
from runtime.state_manager import StateManager
from runtime.timeout_guard import TimeoutGuard

LIVE_EXECUTION = Config.EXECUTION_MODE in ("demo", "live")

def structured_log(event_type, **fields):
    log_line = f"[{event_type}] | exec_id={os.getenv('GITHUB_RUN_ID', 'local')}"
    for k, v in fields.items():
        log_line += f" | {k}={v}"
    print(log_line, flush=True)

def validate_credentials(connector):
    try:
        connector.exchange.fetch_balance()
        structured_log("AUTH_OK")
    except Exception as e:
        structured_log("FATAL_AUTH_ERROR", error=repr(e))
        sys.exit(1)

def main():
    state = StateManager.load()
    structured_log("BOOT", cycle_count=state.get("cycle_count", 0))

    conn = OKXConnector()
    validate_credentials(conn)

    state = StateManager.reconcile_with_exchange(conn, state)
    structured_log("RECONCILE", positions=len(state.get("positions", {})))

    universe = fetch_top100_symbols()
    if Config.ENABLE_VELOCITY_MOMENTUM:
        vme = VelocityMomentumEngine()
        if Config.AUTO_UNIVERSE_OPTIMIZATION:
            universe = vme.optimal_universe(universe, Config.MIN_TOP_N, Config.MAX_TOP_N)
        else:
            scores = vme.rank_assets(universe)
            if scores:
                sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                universe = [s for s, _ in sorted_scores[:Config.MAX_TOP_N]]
            else:
                universe = universe[:Config.MAX_TOP_N]
    structured_log("SCANNER", universe_size=len(universe))

    data = {}
    for sym in universe:
        try:
            df5 = load_or_fetch(sym, "5m", conn.fetch_candles, limit=200)
            if df5 is None or df5.empty:
                continue
            df5 = compute_features(df5)
            df15 = load_or_fetch(sym, "15m", conn.fetch_candles, limit=200)
            df1h = load_or_fetch(sym, "1h", conn.fetch_candles, limit=200)
            data[sym] = {"5m": df5, "15m": df15, "1h": df1h}
            mtf_ok = all(not df.empty for df in [df5, df15, df1h] if df is not None)
            structured_log("AUDIT_MTF", symbol=sym, status="PASS" if mtf_ok else "FAIL")
        except Exception as e:
            structured_log("FETCH_ERROR", symbol=sym, error=str(e))

    strategies = [ExpansionStrategy(), PullbackStrategy(),
                  ReaccelerationStrategy(), DepressionBreakoutStrategy()]
    engine = RotationalEngine(strategies, universe, state.get("balance", 10000), data)

    router = OrderRouter(connector=conn, live=LIVE_EXECUTION)
    pos_mgr = PositionManager()

    breaker = CircuitBreaker()
    guard = TimeoutGuard(max_minutes=330)
    cycle = 0
    total_trades = 0

    while not guard.triggered():
        cycle += 1
        trade = engine.cycle()
        engine._loop_count += 1

        if trade:
            order = router.send_with_feedback(
                trade["symbol"],
                "LONG" if trade["dir"] == 1 else "SHORT",
                trade["size"], trade["atr"], trade["leverage"]
            )
            structured_log("ORDER", status=order.get("status"), order_id=order.get("order_id"))
            if order.get("status") == "filled":
                pos_mgr.open(trade)
                total_trades += 1
                structured_log("FILL_CONFIRMED", symbol=trade["symbol"], size=trade["size"])

        for sym in list(pos_mgr.get_active_symbols()):
            df5 = data.get(sym, {}).get("5m")
            if df5 is None or df5.empty:
                continue
            price = float(df5["close"].iloc[-1])
            pos = pos_mgr.positions[sym]
            exit_sig, reason, px, updated = HybridExit.should_exit(pos, price, time.time())
            if exit_sig:
                pnl = pos_mgr.close(sym, float(px), reason)
                if pnl is not None:
                    trade_info = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "symbol": sym,
                        "side": "LONG" if pos["dir"] == 1 else "SHORT",
                        "entry": float(pos["entry"]),
                        "exit": float(px),
                        "pnl": float(pnl),
                        "meta_score": float(pos.get("meta_score", 0)),
                        "strategy": pos.get("strategy", "unknown")
                    }
                    append_trade(trade_info)
                    structured_log("POSITION_CLOSED", symbol=sym, pnl=pnl, reason=reason)

        if cycle % 10 == 0:
            StateManager.save({"cycle_count": cycle, "last_signal": trade, "positions": pos_mgr.positions})
            structured_log("CHECKPOINT", cycle=cycle)

        time.sleep(30)

    StateManager.save({"cycle_count": cycle, "positions": pos_mgr.positions})
    structured_log("SHUTDOWN_CLEAN", total_cycles=cycle, total_trades=total_trades)

if __name__ == "__main__":
    main()
