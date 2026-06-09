import asyncio
import logging
import time
import traceback
from typing import Dict, Any
from config import Config
from leviathan_edge_core.execution.okx_api_connector import OKXClient
from leviathan_edge_core.execution.rotational_engine import RotationalEngine
from leviathan_edge_core.execution.exit_hybrid import HybridExit
from leviathan_edge_core.execution.order_router import OrderRouter
from leviathan_edge_core.execution.position_manager import PositionManager
from leviathan_edge_core.portfolio.top100_selector import fetch_top100_symbols
from leviathan_edge_core.convergence.velocity_momentum_engine import VelocityMomentumEngine
from leviathan_edge_core.core.feature_engine import FeatureEngine
from leviathan_edge_core.daps.daps_core import DAPSEngine
from leviathan_edge_core.risk.risk_manager import RiskManager
from leviathan_edge_core.risk.kelly import KellySizer
from leviathan_edge_core.risk.circuit_breaker import CircuitBreaker
from edge_monitor import EdgeMonitor
from runtime.state_manager import StateManager
from runtime.pnl_tracker import PnLTracker
from monitoring.alert import send_alert

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.client = OKXClient()
        self.state_mgr = StateManager()
        self.reconciler = Reconciler(self.client)
        self.daps = DAPSEngine(decay_lambda=Config.DAPS_DECAY_LAMBDA)
        self.edge_monitor = EdgeMonitor(alert_threshold=Config.EDGE_ALERT_THRESHOLD)
        self.risk = RiskManager(client=self.client, edge_monitor=self.edge_monitor)
        self.pnl_tracker = PnLTracker()
        self.position_manager = PositionManager()
        self.velocity_engine = VelocityMomentumEngine()
        self.rotational_engine = RotationalEngine()
        self.order_router = OrderRouter(self.client)
        self.feature_engine = FeatureEngine()
        self.circuit_breaker = CircuitBreaker()

    def run(self):
        start_time = time.time()
        end_time = start_time + Config.CYCLE_DURATION_MINUTES * 60
        logger.info(f"Cycle started. LIVE={Config.LIVE} Duration={Config.CYCLE_DURATION_MINUTES}min")

        # 1. Restaurar estado previo
        self.reconciler.restore_state()
        prev_positions = self.state_mgr.load_positions()
        reconciled = self.reconciler.reconcile_positions(prev_positions)
        self.state_mgr.save_positions(reconciled)

        daps_snap = self.state_mgr.load_daps_state()
        if daps_snap:
            for sym, st in daps_snap.items():
                self.daps.set_state(sym, st)

        # 2. Bucle de trading
        while time.time() < end_time:
            try:
                symbols = fetch_top100_symbols(self.client)
                active_symbols = self.velocity_engine.filter(symbols, top_n=12)

                market_data = {}
                for sym in active_symbols:
                    candles_5m = self.client.get_candles(sym, "5m", limit=100)
                    if not candles_5m:
                        continue
                    features = self.feature_engine.compute(candles_5m)
                    market_data[sym] = {"candles_5m": candles_5m, "features": features}

                trade = self.rotational_engine.cycle(market_data, self.state_mgr.get_capital())
                if trade is None:
                    time.sleep(60)
                    continue

                edge_score = trade.get("edge_score", 0.5)
                symbol = trade["symbol"]
                closes = [c[4] for c in market_data[symbol]["candles_5m"]]
                daps_factor = self.daps.step(symbol, closes, edge_score)
                trade["edge_score"] = edge_score * daps_factor

                approved, size = self.risk.evaluate(trade, self.daps)
                if not approved:
                    logger.info(f"Trade rejected by risk manager for {symbol}")
                    continue

                if not self.circuit_breaker.check():
                    logger.warning("Circuit breaker triggered, halting trades")
                    break

                result = self.order_router.send(trade, size)
                if result.get("code") != "0":
                    logger.error(f"Order failed: {result}")
                    continue

                self.pnl_tracker.record_trade(0.0)
                self.edge_monitor.record_trade(0.0)

                # Gestionar salidas
                for pos in self.position_manager.get_open_positions():
                    price = self._get_current_price(pos["instId"])
                    if price is None:
                        continue
                    exit_signal, reason = HybridExit.evaluate(pos, price)
                    if exit_signal:
                        self.client.close_position(pos["instId"], pos["posSide"])
                        pnl = self._calculate_pnl(pos, price)
                        self.pnl_tracker.record_trade(pnl)
                        self.edge_monitor.record_trade(pnl)
                        self.position_manager.remove_position(pos["instId"], pos["posSide"])
                        logger.info(f"Exit: {pos['instId']} {reason} PnL={pnl:.2f}")

            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                send_alert(f"Leviathan cycle error: {e}")
                time.sleep(30)

            time.sleep(60)

        # 3. Guardar estado final
        self.state_mgr.save_daps_state({sym: self.daps.get_state(sym) for sym in self.daps.symbol_stats})
        self.edge_monitor.save_metrics("state/metrics.json")
        final_positions = self.position_manager.get_open_positions()
        self.state_mgr.save_positions(final_positions)
        logger.info("Cycle completed")

    def _get_current_price(self, instId: str) -> float:
        candles = self.client.get_candles(instId, "5m", limit=1)
        if candles:
            return float(candles[0][4])
        return None

    def _calculate_pnl(self, pos: Dict[str, Any], exit_price: float) -> float:
        entry = float(pos.get("avgPx", 0))
        sz = float(pos.get("pos", 0))
        side = 1 if pos["posSide"] == "long" else -1
        return (exit_price - entry) * sz * side
