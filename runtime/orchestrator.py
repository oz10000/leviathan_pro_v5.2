import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Any
import numpy as np
import pandas as pd
from config import Config
from leviathan_edge_core.execution.okx_api_connector import OKXClient
from leviathan_edge_core.execution.rotational_engine import RotationalEngine
from leviathan_edge_core.execution.order_router import OrderRouter
from leviathan_edge_core.execution.position_manager import PositionManager
from leviathan_edge_core.portfolio.top100_selector import fetch_top100_symbols
from leviathan_edge_core.convergence.velocity_momentum_engine import VelocityMomentumEngine
from leviathan_edge_core.core.feature_engine import FeatureEngine
from leviathan_edge_core.strategies.expansion_strategy import ExpansionStrategy
from leviathan_edge_core.strategies.pullback_strategy import PullbackStrategy
from leviathan_edge_core.strategies.reacceleration_strategy import ReaccelerationStrategy
from leviathan_edge_core.strategies.depression_breakout import DepressionBreakoutStrategy
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
        self.edge_monitor = EdgeMonitor(alert_threshold=Config.EDGE_ALERT_THRESHOLD)
        self.circuit_breaker = CircuitBreaker()
        self.pnl_tracker = PnLTracker()
        self.position_manager = PositionManager()
        self.velocity_engine = VelocityMomentumEngine()
        self.order_router = OrderRouter(self.client)
        self.feature_engine = FeatureEngine()
        self.strategies = [
            ExpansionStrategy(),
            PullbackStrategy(),
            ReaccelerationStrategy(),
            DepressionBreakoutStrategy()
        ]
        self.rotational = None
        self.symbols = []
        self.capital = Config.CAPITAL
        self._running = False

    async def run_forever(self):
        self._running = True
        logger.info(f"Leviathan 24/7 started. LIVE={Config.LIVE}")
        await self.state_mgr.initialize()
        await self.client.set_position_mode()

        # Inicializar universo
        self.symbols = self._update_universe()
        data_feeds = self._build_data_feeds()
        self.rotational = RotationalEngine(
            strategies=self.strategies,
            universe=self.symbols,
            capital=self.capital,
            data_feeds=data_feeds
        )

        while self._running:
            try:
                await self._cycle()
            except Exception as e:
                logger.error(f"Unhandled exception: {e}", exc_info=True)
                await send_alert(f"Leviathan cycle error: {e}")
                await asyncio.sleep(10)
            await asyncio.sleep(60)

    def _update_universe(self):
        symbols = fetch_top100_symbols(self.client)
        active = self.velocity_engine.filter(symbols, top_n=12)
        return active

    def _build_data_feeds(self):
        data_feeds = {}
        for sym in self.symbols:
            data_feeds[sym] = {}
            for tf in ["5m", "15m", "1h"]:
                candles = self.client.get_candles(sym, tf, limit=100)
                if candles:
                    df = pd.DataFrame(candles, columns=["ts", "open", "high", "low", "close", "vol", "volCcy"])
                    df = df.iloc[::-1]  # orden cronológico
                    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
                    df.set_index("ts", inplace=True)
                    for col in ["open", "high", "low", "close", "vol"]:
                        df[col] = df[col].astype(float)
                    # Features
                    df = self.feature_engine.compute(df)
                    data_feeds[sym][tf] = df
        return data_feeds

    async def _cycle(self):
        # Actualizar universo cada 5 minutos
        if int(time.time()) % 300 < 60:
            self.symbols = self._update_universe()

        # Actualizar datos de mercado
        for sym in self.symbols:
            for tf in ["5m", "15m", "1h"]:
                new_candles = self.client.get_candles(sym, tf, limit=5)
                if new_candles:
                    df = pd.DataFrame(new_candles, columns=["ts", "open", "high", "low", "close", "vol", "volCcy"])
                    df = df.iloc[::-1]
                    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
                    df.set_index("ts", inplace=True)
                    for col in ["open", "high", "low", "close", "vol"]:
                        df[col] = df[col].astype(float)
                    df = self.feature_engine.compute(df)
                    if tf in self.rotational.data.get(sym, {}):
                        self.rotational.data[sym][tf] = pd.concat([self.rotational.data[sym][tf], df]).tail(100)

        # Circuit breaker
        if not self.circuit_breaker.check():
            logger.warning("Circuit breaker triggered, halting trades")
            return

        # Ciclo del motor rotacional
        position = self.rotational.cycle()
        if position:
            # Enviar orden a OKX
            trade = {
                "symbol": position["symbol"],
                "direction": "buy" if position["dir"] == 1 else "sell",
                "leverage": position["leverage"],
                "entry": position["entry"],
                "atr": position["atr"],
                "size": position["size"]
            }
            result = self.order_router.send(trade)
            if result.get("code") == "0":
                logger.info(f"Order placed: {position['symbol']} {trade['direction']}")
                self.position_manager.add_position(position)
            else:
                logger.error(f"Order failed: {result}")

        # Actualizar posiciones abiertas (gestión de salidas)
        current_prices = {}
        for pos in self.position_manager.get_open_positions():
            sym = pos["symbol"]
            if sym not in current_prices:
                candles = self.client.get_candles(sym, "5m", limit=1)
                current_prices[sym] = float(candles[0][4]) if candles else None
            price = current_prices.get(sym)
            if price is None:
                continue
            self.rotational.update_position(price)
            # Si el motor cerró la posición, se refleja en rotational.position = None
            if self.rotational.position is None:
                # Buscar la última operación en el historial de PnL
                if self.rotational.pnl_history:
                    pnl = self.rotational.pnl_history[-1]
                    self.pnl_tracker.record_trade(pnl)
                    self.edge_monitor.record_trade(pnl)
                    self.position_manager.remove_position(sym, "long" if pos["dir"] == 1 else "short")
                    logger.info(f"Position closed: {sym} PnL={pnl:.2f}")

        # Reconciliación y persistencia al final del ciclo
        if time.time() % 300 < 60:
            self.reconciler.reconcile_positions(self.state_mgr.load_positions())
            self.state_mgr.save_daps_state(self.rotational.daps.x)
            self.edge_monitor.save_metrics("state/metrics.json")
            self.state_mgr.save_positions(self.position_manager.get_open_positions())

    async def shutdown(self):
        self._running = False
        await self.state_mgr.close()
        logger.info("Orchestrator shut down")
