import asyncio
import logging
import time
import traceback
from typing import Dict, Any
import pandas as pd
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
from leviathan_edge_core.risk.circuit_breaker import CircuitBreaker
from edge_monitor import EdgeMonitor
from runtime.state_manager import StateManager
from runtime.pnl_tracker import PnLTracker
from okx.reconciler import Reconciler
from monitoring.alert import send_alert

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Orquestador principal del ciclo de trading.
    Versión asíncrona con inicialización de estado, idempotencia de órdenes
    y persistencia completa entre ciclos.
    """

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
        self._running = False

    async def run(self):
        """
        Bucle principal del ciclo de trading.
        Inicializa el estado, ejecuta el bucle de trading con verificación
        de idempotencia y persiste el estado al finalizar.
        """
        self._running = True
        logger.info(f"Cycle started. LIVE={Config.LIVE} Duration={Config.CYCLE_DURATION_MINUTES}min")

        # --- INICIALIZACIÓN DEL ESTADO (PATCHES 2, 3, 4) ---
        await self.state_mgr.initialize()
        await self.reconciler.restore_state()

        # Restaurar historial del EdgeMonitor si existe un snapshot previo
        try:
            self.edge_monitor.load_metrics("state/metrics.json")
        except Exception:
            logger.debug("No previous EdgeMonitor metrics found, starting fresh.")

        # Reconciliar posiciones con OKX antes de comenzar
        prev_positions = self.state_mgr.load_positions()
        reconciled = self.reconciler.reconcile_positions(prev_positions)
        self.state_mgr.save_positions(reconciled)

        # Restaurar estado del DAPS desde el último snapshot
        daps_snap = self.state_mgr.load_daps_state()
        if daps_snap:
            for sym, st in daps_snap.items():
                self.daps.set_state(sym, st)

        start_time = time.time()
        end_time = start_time + Config.CYCLE_DURATION_MINUTES * 60

        # --- BUCLE DE TRADING ---
        while time.time() < end_time:
            try:
                # 1. Actualizar universo de activos cada 5 minutos
                symbols = fetch_top100_symbols(self.client)
                active_symbols = self.velocity_engine.filter(symbols, top_n=12)

                # 2. Construir datos de mercado
                market_data = {}
                for sym in active_symbols:
                    candles_5m = self.client.get_candles(sym, "5m", limit=100)
                    if not candles_5m:
                        continue
                    features = self.feature_engine.compute(candles_5m)
                    market_data[sym] = {"candles_5m": candles_5m, "features": features}

                # 3. Generar señal con el motor rotacional
                trade = self.rotational_engine.cycle(market_data, self.state_mgr.get_capital())
                if trade is None:
                    time.sleep(60)
                    continue

                # 4. Modular Edge Score con DAPS
                edge_score = trade.get("edge_score", 0.5)
                symbol = trade["symbol"]
                closes = [c[4] for c in market_data[symbol]["candles_5m"]]
                daps_factor = self.daps.step(symbol, closes, edge_score)
                trade["edge_score"] = edge_score * daps_factor

                # 5. Evaluar riesgo
                approved, size = self.risk.evaluate(trade, self.daps)
                if not approved:
                    logger.info(f"Trade rejected by risk manager for {symbol}")
                    continue

                # 6. Circuit breaker
                if not self.circuit_breaker.check():
                    logger.warning("Circuit breaker triggered, halting trades")
                    break

                # 7. Ejecutar orden con IDEMPOTENCIA (PATCHES 5, 6)
                clOrdId = "lev_" + str(int(time.time() * 1000))
                if not await self.reconciler.was_order_sent(clOrdId):
                    result = self.order_router.send(trade, size)
                    if result.get("code") == "0":
                        logger.info(f"Order placed: {symbol} {trade['direction']}")
                        self.position_manager.add_position(trade)
                        await self.reconciler.mark_order_sent(
                            clOrdId, symbol, trade.get("direction", "buy"), size
                        )
                    else:
                        logger.error(f"Order failed: {result}")
                else:
                    logger.info(f"Order {clOrdId} already sent, skipping.")

                # 8. Gestionar salidas de posiciones abiertas
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

        # --- PERSISTENCIA FINAL ---
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

    async def shutdown(self):
        self._running = False
        await self.state_mgr.close()
        logger.info("Orchestrator shut down")
