#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leviathan V5.2 DAPS CAUSAL – Runtime Orchestrator
"""

import sys
import os
import time
import numpy as np
from datetime import datetime, timezone

# ------------------------------------------------------------
# Ajuste de PYTHONPATH
# ------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "leviathan_edge_core"))

# ------------------------------------------------------------
# Importaciones
# ------------------------------------------------------------
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

MAX_CYCLES = int(os.getenv("MAX_CYCLES", 8))

# Ejecución real solo si el modo es demo o live
LIVE_EXECUTION = Config.EXECUTION_MODE in ("demo", "live")


def main():
    # ── Cargar estado previo ──────────────────────────────────
    state = load_state()
    logger.info("Estado cargado: loop=%d, balance=%.2f",
                state["loop_count"], state["balance"])

    # ── Universo y datos (usa caché incremental) ───────────────
    universe = fetch_top100_symbols()
    conn = OKXConnector()
    data = {}

    def _fetch_okx(symbol, timeframe, limit=200):
        return conn.fetch_candles(symbol, timeframe, limit)

    for sym in universe:
        try:
            df5 = load_or_fetch(sym, "5m", _fetch_okx, limit=200)
            if df5 is None or df5.empty:
                continue
            df5 = compute_features(df5)
            df15 = load_or_fetch(sym, "15m", _fetch_okx, limit=200)
            df1h = load_or_fetch(sym, "1H", _fetch_okx, limit=200)
            if not df15.empty:
                df15 = compute_features(df15)
            if not df1h.empty:
                df1h = compute_features(df1h)
            data[sym] = {"5m": df5, "15m": df15, "1h": df1h}
            time.sleep(0.1)
        except Exception as e:
            logger.warning("No se pudieron obtener datos para %s: %s", sym, e)

    strategies = [ExpansionStrategy(), PullbackStrategy(),
                  ReaccelerationStrategy(), DepressionBreakoutStrategy()]

    # ── Motor con capital restaurado ──────────────────────────
    engine = RotationalEngine(strategies, universe, state["balance"], data)
    if state.get("position") is not None:
        engine.position = state["position"]
        logger.info("Posición restaurada desde estado previo.")
    engine.daps.x = state["daps_x"]
    engine.daps_equilibrium.equilibrium_score = state["equilibrium"]
    engine.daps_balance.balance = state.get("daps_balance", 1.0)
    engine._loop_count = state["loop_count"]
    if hasattr(engine, "status"):
        engine.status = state.get("status", "RUNNING")

    # ── Order Router con el modo correcto ─────────────────────
    router = OrderRouter(live=LIVE_EXECUTION)
    pos_mgr = PositionManager()

    # Restaurar posiciones abiertas
    for sym, pdata in state.get("open_positions", {}).items():
        pos_mgr.positions[sym] = {
            "symbol": sym,
            "dir": 1 if pdata.get("direction") == "LONG" else -1,
            "entry": float(pdata.get("entry", 0.0)),
            "size": float(pdata.get("size", 0.0)),
            "leverage": float(pdata.get("leverage", 1.0)),
            "atr": float(pdata.get("atr", 0.0)),
            "meta_score": float(pdata.get("meta_score", 0.0)),
            "entry_time": datetime.now(timezone.utc).timestamp()
        }
    logger.info("Posiciones restauradas: %s", list(pos_mgr.positions.keys()))

    # ── Circuit Breaker ───────────────────────────────────────
    breaker = CircuitBreaker(
        max_consecutive_losses=5,
        max_drawdown_pct=0.12,
        cooldown_minutes=60
    )
    if "breaker" in state:
        b = state["breaker"]
        breaker.loss_streak = b.get("loss_streak", 0)
        breaker.peak_equity = b.get("peak_equity")
        breaker.cooldown_until = b.get("cooldown_until", 0.0)

    # ── Métricas de observabilidad ────────────────────────────
    metrics = RuntimeMetrics()

    # ==================================================================
    # BUCLE DE TRADING
    # ==================================================================
    for cycle in range(MAX_CYCLES):
        logger.info("Inicio ciclo %d/%d", cycle + 1, MAX_CYCLES)
        metrics.start_cycle()

        # Leer control operacional
        control = load_control()
        if control.get("shutdown_requested", False):
            logger.info("Shutdown solicitado. Finalizando bucle.")
            break

        trade = None
        try:
            # Si el bot está deshabilitado, no abrir nuevas posiciones
            if not control.get("bot_enabled", True):
                logger.info("Bot deshabilitado por control. Solo gestión de posiciones existentes.")
            else:
                # Verificar circuit breaker
                if not breaker.can_trade():
                    logger.warning("Circuit breaker activo. Trading pausado.")
                    time.sleep(30)
                    continue

                trade = engine.cycle()
                engine._loop_count += 1

                if trade:
                    order = router.send_with_feedback(
                        trade["symbol"],
                        "LONG" if trade["dir"] == 1 else "SHORT",
                        trade["size"], trade["atr"], trade["leverage"]
                    )
                    if order.get("status") == "filled":
                        pos_mgr.open(trade)
                        logger.info("Trade abierto: %s %s",
                                    trade["symbol"], trade["strategy"])

                    if hasattr(engine, "exec_qual"):
                        engine.exec_qual.feed_execution(
                            latency_ms=order.get("latency_ms", 0),
                            slippage_pct=order.get("slippage_pct", 0),
                            filled=(order.get("status") == "filled"),
                            rejected=(order.get("status") == "rejected")
                        )
                else:
                    if hasattr(engine, "perf_tracker"):
                        engine.perf_tracker.add_equity_snapshot(engine.capital)

            # Gestión de salidas (siempre activa, incluso con bot detenido)
            for sym in list(pos_mgr.get_active_symbols()):
                df5 = data.get(sym, {}).get("5m")
                if df5 is None or df5.empty:
                    continue
                price = float(df5["close"].iloc[-1])
                pos_data = pos_mgr.positions[sym].copy()
                exit_sig, reason, px, updated = HybridExit.should_exit(
                    pos_data, price, time.time()
                )
                if exit_sig:
                    pnl = pos_mgr.close(sym, float(px), reason)
                    if pnl is not None:
                        trade_info = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "symbol": sym,
                            "side": "LONG" if pos_data["dir"] == 1 else "SHORT",
                            "entry": float(pos_data["entry"]),
                            "exit": float(px),
                            "pnl": float(pnl),
                            "meta_score": float(pos_data.get("meta_score", 0)),
                            "strategy": pos_data.get("strategy", "unknown")
                        }
                        append_trade(trade_info)
                        breaker.update(engine.capital, pnl)
                        logger.info("Trade cerrado: %s PnL=%.2f", sym, pnl)

        except Exception as e:
            logger.error("Error en ciclo: %s", e)

        finally:
            # Precios actuales para unrealized PnL
            current_prices = {}
            for sym in pos_mgr.get_active_symbols():
                df5 = data.get(sym, {}).get("5m")
                if df5 is not None and not df5.empty:
                    current_prices[sym] = float(df5["close"].iloc[-1])
            save_state(engine, pos_mgr, current_prices, breaker)

            # Métricas del ciclo
            signals_gen = 1 if trade else 0
            signals_filt = getattr(engine, "_signals_filtered", 0)
            engine_status = getattr(engine, "status", "RUNNING")
            try:
                current_sharpe = engine.perf_tracker.realtime_sharpe() if hasattr(engine, "perf_tracker") else 0.0
            except:
                current_sharpe = 0.0
            safe_mode = current_sharpe < 1.5

            metrics.end_cycle(
                signals_generated=signals_gen,
                signals_filtered=signals_filt,
                open_positions=pos_mgr.active_count(),
                circuit_breaker_active=not breaker.can_trade(),
                stat_guard_block=(engine_status == "STAT_GUARD_BLOCK"),
                safe_mode=safe_mode
            )

        time.sleep(30)

    # Guardar control limpio al salir
    control = load_control()
    control["shutdown_requested"] = False
    save_control(control)
    logger.info("Ejecución completada.")


if __name__ == "__main__":
    main()
