import asyncio
import logging
import time
import traceback
from config import Config
from leviathan_edge_core.execution.okx_api_connector import OKXClient
from leviathan_edge_core.execution.rotational_engine import RotationalEngine
from leviathan_edge_core.execution.exit_hybrid import HybridExit
from leviathan_edge_core.execution.order_router import OrderRouter
from leviathan_edge_core.execution.position_manager import PositionManager
from leviathan_edge_core.portfolio.top100_selector import fetch_top100_symbols
from leviathan_edge_core.portfolio.velocity_momentum_engine import VelocityMomentumEngine
from runtime.pnl_tracker import PnLTracker
from runtime.state_manager import StateManager
from okx.reconciler import Reconciler
from monitoring.alert import send_alert

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.client = OKXClient()
        self.state = StateManager()
        self.pnl_tracker = PnLTracker()
        self.position_manager = PositionManager()
        self.reconciler = Reconciler(self.client, self.state)
        self.order_router = OrderRouter(self.client)
        self.rotational_engine = RotationalEngine()
        self.velocity_engine = VelocityMomentumEngine()
        self.running = False

    async def run_forever(self):
        self.running = True
        logger.info("Leviathan 24/7 started")
        await self.state.initialize()
        await self.client.set_position_mode()

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.critical(f"Unhandled exception: {e}")
                traceback.print_exc()
                await send_alert(f"CRITICAL: {e}")
                await asyncio.sleep(10)
            await asyncio.sleep(60)

    async def run_cycle(self):
        symbols = fetch_top100_symbols(self.client)
        active = self.velocity_engine.filter(symbols, top_n=12)

        market_data = {}
        for sym in active:
            c5 = self.client.get_candles(sym, "5m", 100)
            c15 = self.client.get_candles(sym, "15m", 100)
            c1h = self.client.get_candles(sym, "1H", 100)
            market_data[sym] = {"5m": c5, "15m": c15, "1h": c1h}

        trade = self.rotational_engine.cycle(market_data, self.state.get_capital())
        if not trade:
            return

        if self.pnl_tracker.daily_loss_exceeded():
            logger.warning("Daily loss limit reached. Skipping trade.")
            return

        order_result = self.order_router.send(trade)
        if not order_result or order_result.get("code") != "0":
            logger.error(f"Order failed: {order_result}")
            return

        pos = order_result["data"][0]
        self.position_manager.add_position(pos)

        open_positions = self.position_manager.get_open_positions()
        for p in open_positions:
            price = self._get_current_price(p["instId"])
            if price is None:
                continue
            exit_signal, reason = HybridExit.evaluate(p, price)
            if exit_signal:
                side = "sell" if p["posSide"] == "long" else "buy"
                result = self.client.place_order(
                    p["instId"], side, float(p["pos"]), p["posSide"], reduceOnly=True
                )
                if result.get("code") == "0":
                    self.position_manager.remove_position(p["instId"], p["posSide"])
                    pnl = self._calculate_pnl(p, price)
                    self.pnl_tracker.record_trade(pnl)
                    logger.info(f"Exit: {p['instId']} {reason} PnL={pnl:.2f}")

    def _get_current_price(self, instId: str) -> float:
        candles = self.client.get_candles(instId, "5m", 1)
        return float(candles[0][4]) if candles else None

    def _calculate_pnl(self, pos: dict, exit_price: float) -> float:
        entry = float(pos.get("avgPx", 0))
        sz = float(pos.get("pos", 0))
        side = 1 if pos["posSide"] == "long" else -1
        return (exit_price - entry) * sz * side

    async def shutdown(self):
        self.running = False
        await self.state.save()
        logger.info("Orchestrator shut down")
