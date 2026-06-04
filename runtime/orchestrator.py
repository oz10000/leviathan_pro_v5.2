import asyncio
import logging
import time
import traceback
from config import Config
from execution.okx_api_connector import OKXClient
from execution.rotational_engine import RotationalEngine
from execution.exit_hybrid import HybridExit
from execution.order_router import OrderRouter
from execution.position_manager import PositionManager
from runtime.pnl_tracker import PnLTracker
from runtime.state_manager import StateManager
from portfolio.top100_selector import fetch_top100_symbols
from portfolio.velocity_momentum_engine import VelocityMomentumEngine
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
        """Bucle principal 24/7."""
        self.running = True
        logger.info("Leviathan DAPS-Ω 24/7 started")

        # Inicializar estado (cargar posiciones abiertas, etc.)
        await self.state.initialize()
        await self.client.set_position_mode()

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.critical(f"Unhandled exception in main loop: {e}")
                traceback.print_exc()
                await send_alert(f"CRITICAL: {e}")
                await asyncio.sleep(10)

            # Esperar hasta el siguiente minuto
            await asyncio.sleep(60)

    async def run_cycle(self):
        """Un ciclo completo de trading."""
        # 1. Actualizar universo
        symbols = fetch_top100_symbols(self.client)
        active_symbols = self.velocity_engine.filter(symbols, top_n=12)

        # 2. Obtener velas para el universo reducido
        market_data = {}
        for sym in active_symbols:
            candles_5m = self.client.get_candles(sym, "5m", limit=100)
            candles_15m = self.client.get_candles(sym, "15m", limit=100)
            candles_1h = self.client.get_candles(sym, "1H", limit=100)
            market_data[sym] = {
                "5m": candles_5m,
                "15m": candles_15m,
                "1h": candles_1h,
            }

        # 3. Ejecutar motor rotacional
        trade = self.rotational_engine.cycle(market_data, self.state.get_capital())
        if not trade:
            return

        # 4. Verificar circuit breaker
        if self.pnl_tracker.daily_loss_exceeded():
            logger.warning("Daily loss limit reached. Skipping trade.")
            return

        # 5. Enviar orden
        order_result = self.order_router.send(trade)
        if not order_result or order_result.get("code") != "0":
            logger.error(f"Order failed: {order_result}")
            return

        # 6. Registrar posición
        self.position_manager.add_position(order_result["data"][0])

        # 7. Verificar salidas (se ejecuta en cada ciclo)
        await self.manage_exits()

    async def manage_exits(self):
        """Gestiona salidas de todas las posiciones abiertas."""
        open_positions = self.position_manager.get_open_positions()
        for pos in open_positions:
            current_price = self._get_current_price(pos["instId"])
            if current_price is None:
                continue
            should_exit, reason = HybridExit.evaluate(pos, current_price)
            if should_exit:
                side = "sell" if pos["posSide"] == "long" else "buy"
                result = self.client.place_order(
                    pos["instId"], side, float(pos["pos"]), pos["posSide"], reduceOnly=True
                )
                if result.get("code") == "0":
                    self.position_manager.remove_position(pos["instId"], pos["posSide"])
                    pnl = self._calculate_pnl(pos, current_price)
                    self.pnl_tracker.record_trade(pnl)
                    logger.info(f"Exit: {pos['instId']} {reason} PnL={pnl:.2f}")

    def _get_current_price(self, instId: str) -> float:
        candles = self.client.get_candles(instId, "5m", limit=1)
        if candles:
            return float(candles[0][4])  # close
        return None

    def _calculate_pnl(self, pos: dict, exit_price: float) -> float:
        entry = float(pos["avgPx"])
        sz = float(pos["pos"])
        side = 1 if pos["posSide"] == "long" else -1
        return (exit_price - entry) * sz * side

    async def shutdown(self):
        self.running = False
        await self.state.save()
        logger.info("Orchestrator shut down")
