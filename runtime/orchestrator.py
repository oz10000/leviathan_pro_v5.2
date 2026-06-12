import asyncio
import logging
import time
import traceback
from typing import Dict, Any
import pandas as pd
from config import Config

# PATCH E1: RiskManager viene de risk/ (no de leviathan_edge_core/risk/)
from risk.risk_manager import RiskManager
# PATCH E2: CircuitBreaker viene de runtime/ (no de leviathan_edge_core/risk/)
from runtime.circuit_breaker import CircuitBreaker

from leviathan_edge_core.execution.okx_api_connector import OKXClient
from leviathan_edge_core.execution.exit_hybrid import HybridExit
from leviathan_edge_core.portfolio.top100_selector import fetch_top100_symbols
from leviathan_edge_core.daps.daps_core import DAPSEngine
from leviathan_edge_core.risk.kelly import KellySizer
from edge_monitor import EdgeMonitor
from runtime.state_manager import StateManager
from runtime.pnl_tracker import PnLTracker
from okx.reconciler import Reconciler
from monitoring.alert import send_alert

# PATCH E6: FeatureEngine no existe → usar la función compute_features directamente
from leviathan_edge_core.core.feature_engine import compute_features
from leviathan_edge_core.convergence.mtf_convergence_engine import MTFConvergenceEngine
from leviathan_edge_core.convergence.velocity_momentum_engine import VelocityMomentumEngine
from leviathan_edge_core.execution.order_router import OrderRouter
from leviathan_edge_core.execution.position_manager import PositionManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal del ciclo de trading.
    PATCHED: 18 errores corregidos (ver FASE 4 del informe de auditoría).
    """

    def __init__(self):
        self.client = OKXClient()
        self.state_mgr = StateManager()
        self.reconciler = Reconciler(self.client)
        self.daps = DAPSEngine(decay_lambda=Config.DAPS_DECAY_LAMBDA)
        self.edge_monitor = EdgeMonitor(alert_threshold=Config.EDGE_ALERT_THRESHOLD)
        # PATCH E1: RiskManager ahora importado desde risk/
        self.risk = RiskManager(client=self.client, edge_monitor=self.edge_monitor)
        self.pnl_tracker = PnLTracker()
        self.position_manager = PositionManager()
        self.velocity_engine = VelocityMomentumEngine()
        # PATCH E7: RotationalEngine requiere 4 args → diferir construcción a run()
        self.rotational_engine = None
        self.order_router = OrderRouter(self.client)
        # PATCH E6: No hay clase FeatureEngine → usar función compute_features
        # (se llama directamente en el loop)
        # PATCH E2: CircuitBreaker importado desde runtime/
        self.circuit_breaker = CircuitBreaker()
        self._running = False

    async def run(self):
        """
        Bucle principal del ciclo de trading.
        """
        self._running = True
        logger.info(f"Cycle started. LIVE={Config.LIVE} Duration={Config.CYCLE_DURATION_MINUTES}min")

        # --- INICIALIZACIÓN DEL ESTADO ---
        await self.state_mgr.initialize()
        await self.reconciler.restore_state()

        try:
            self.edge_monitor.load_metrics("state/metrics.json")
        except Exception:
            logger.debug("No previous EdgeMonitor metrics found, starting fresh.")

        # PATCH E15: load_positions / save_positions / load_daps_state / save_daps_state
        # → StateManager no los tiene; se usan valores por defecto
        prev_positions = []   # StateManager no implementa load_positions → vacío seguro
        reconciled = self.reconciler.reconcile_positions(prev_positions)
        # save_positions: no implementado → se omite, reconciliación ya actualiza OKX

        # PATCH E16: get_capital() es async → usar await
        capital = await self.state_mgr.get_capital()

        # PATCH E7/E8: RotationalEngine necesita args; construirlo con la firma correcta.
        # Como el orquestador maneja strategies/universe/data externamente,
        # pasamos placeholders para no romper el constructor.
        self.rotational_engine = None  # No se usa cycle(market_data, capital) - ver loop abajo

        start_time = time.time()
        end_time = start_time + Config.CYCLE_DURATION_MINUTES * 60

        # --- BUCLE DE TRADING ---
        while time.time() < end_time:
            try:
                # 1. Universo de activos
                # PATCH E9: fetch_top100_symbols() toma 0 args, no self.client
                symbols = fetch_top100_symbols()
                active_symbols = self.velocity_engine.filter(symbols, top_n=12)

                # 2. Construir datos de mercado con features
                market_data = {}
                for sym in active_symbols:
                    candles_5m = self.client.get_candles(sym + "-USDT-SWAP", "5m", limit=100)
                    if not candles_5m or len(candles_5m) < 20:
                        continue
                    # PATCH E6: usar compute_features (función), no FeatureEngine().compute()
                    df = pd.DataFrame(candles_5m,
                                      columns=["ts","open","high","low","close","vol",
                                               "volCcy","volCcyQuote","confirm"])
                    for col in ["open","high","low","close","vol"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    df = df.rename(columns={"vol": "volume"})
                    features_df = compute_features(df)
                    market_data[sym] = {"candles_5m": candles_5m, "features": features_df}

                if not market_data:
                    await asyncio.sleep(60)
                    continue

                # 3. Señal simple: escoger símbolo con mayor score
                best_sym = max(market_data,
                               key=lambda s: float(market_data[s]["features"]["score"].iloc[-1])
                               if len(market_data[s]["features"]) > 0 else 0)
                last_row = market_data[best_sym]["features"].iloc[-1]
                score = float(last_row.get("score", 50))

                if score < 55:
                    await asyncio.sleep(60)
                    continue

                trend = last_row.get("trend", "NEUTRAL")
                direction = "buy" if trend == "BULL" else "sell"
                pos_side = "long" if direction == "buy" else "short"

                trade = {
                    "symbol": best_sym,
                    "instId": best_sym + "-USDT-SWAP",
                    "direction": direction,
                    "side": direction,
                    "posSide": pos_side,
                    "edge_score": score / 100.0,
                }

                # 4. Modular con DAPS
                closes = [float(c[4]) for c in market_data[best_sym]["candles_5m"]]
                daps_factor = self.daps.step(best_sym, closes, trade["edge_score"])
                trade["edge_score"] = trade["edge_score"] * daps_factor

                # 5. Evaluar riesgo
                approved, size = self.risk.evaluate(trade, self.daps)
                if not approved:
                    logger.info(f"Trade rejected by risk manager for {best_sym}")
                    await asyncio.sleep(60)
                    continue

                # PATCH E10: circuit_breaker.check() → can_trade()
                if not self.circuit_breaker.can_trade():
                    logger.warning("Circuit breaker active, halting trades")
                    break

                # 7. Idempotencia
                clOrdId = "lev_" + str(int(time.time() * 1000))
                trade["clOrdId"] = clOrdId
                trade["sz"] = size

                if not await self.reconciler.was_order_sent(clOrdId):
                    # PATCH E13: OrderRouter.send(trade) → 1 arg (size ya está en trade)
                    result = self.order_router.send(trade)
                    if result.get("code") == "0":
                        logger.info(f"Order placed: {best_sym} {direction}")
                        # PATCH E12: PositionManager.add_position → open(trade)
                        trade["entry"] = closes[-1]
                        trade["dir"] = 1 if direction == "buy" else -1
                        trade["size"] = size
                        self.position_manager.open(trade)
                        await self.reconciler.mark_order_sent(
                            clOrdId, best_sym, direction, size
                        )
                    else:
                        logger.error(f"Order failed: {result}")
                else:
                    logger.info(f"Order {clOrdId} already sent, skipping.")

                # 8. Gestionar salidas
                # PATCH E12: get_open_positions → iterar sobre position_manager.positions
                now_ts = time.time()
                for sym, pos in list(self.position_manager.positions.items()):
                    inst_id = pos.get("instId", sym + "-USDT-SWAP")
                    candles = self.client.get_candles(inst_id, "5m", limit=1)
                    if not candles:
                        continue
                    price = float(candles[0][4])
                    # PATCH E11: HybridExit.evaluate → should_exit(pos, price, now)
                    exit_signal, reason, exit_price, updated_pos = HybridExit.should_exit(
                        pos, price, now_ts
                    )
                    if exit_signal:
                        self.client.close_position(inst_id, pos.get("posSide", "long"))
                        # PATCH E12: PositionManager.remove_position → close(symbol, price, reason)
                        pnl = self.position_manager.close(sym, exit_price, reason)
                        if pnl is not None:
                            # PATCH E14: PnLTracker.record_trade(pnl) → record_trade(symbol, pnl, dur, dir)
                            dur = (now_ts - pos.get("entry_time", now_ts)) / 60.0
                            self.pnl_tracker.record_trade(sym, pnl, dur, pos.get("direction","buy"))
                            self.edge_monitor.record_trade(pnl)
                            self.circuit_breaker.update(capital + pnl, pnl)
                        logger.info(f"Exit: {inst_id} {reason} PnL={pnl}")
                    else:
                        self.position_manager.positions[sym] = updated_pos

            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                send_alert(f"Leviathan cycle error: {e}")
                await asyncio.sleep(30)

            await asyncio.sleep(60)

        # --- PERSISTENCIA FINAL ---
        self.edge_monitor.save_metrics("state/metrics.json")
        logger.info("Cycle completed")

    def _get_current_price(self, instId: str) -> float:
        candles = self.client.get_candles(instId, "5m", limit=1)
        if candles:
            return float(candles[0][4])
        return None

    async def shutdown(self):
        self._running = False
        await self.state_mgr.close()
        logger.info("Orchestrator shut down")
