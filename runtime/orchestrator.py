#!/usr/bin/env python3
"""
LEVIATHAN ORCHESTRATOR — AUTONOMOUS QUANTITATIVE RUNTIME
Pipeline completo: escaneo → scoring → ejecución → gestión → persistencia → dashboard.
"""
import sys, os, time, json, signal, logging, hashlib, random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDGE_CORE = REPO_ROOT / "leviathan_edge_core"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EDGE_CORE))

from config import Config
from core.feature_engine import compute_features
from strategies.expansion_strategy import ExpansionStrategy
from strategies.pullback_strategy import PullbackStrategy
from strategies.reacceleration_strategy import ReaccelerationStrategy
from strategies.depression_breakout import DepressionBreakoutStrategy
from execution.rotational_engine import RotationalEngine
from execution.order_router import OrderRouter
from execution.position_manager import PositionManager
from execution.exit_hybrid import HybridExit
from portfolio.top100_selector import fetch_top100_symbols
from portfolio.testnet_assets import fetch_testnet_symbols

from runtime.persistence_engine import PersistenceEngine
from runtime.reconciliation_engine import ExchangeReconciliationEngine
from runtime.position_guardian import PersistentPositionGuardian
from runtime.hybrid_exit_engine import HybridExitManager
from runtime.bootstrap import bootstrap_runtime
from runtime.journal_engine import JournalEngine
from runtime.health_engine import HealthEngine
from runtime.market_data import MarketDataFetcher
from runtime.runtime_lock import RuntimeLock

RUNTIME_DIR = REPO_ROOT / "runtime"
LOG_FILE = RUNTIME_DIR / "logs" / "orchestrator.log"
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

EMERGENCY_STOP = RUNTIME_DIR / "emergency_stop.txt"
STATE_FILE = RUNTIME_DIR / "state.json"


class Orchestrator:
    def __init__(self):
        self.persistence = PersistenceEngine()
        self.reconciliation = ExchangeReconciliationEngine()
        self.guardian = PersistentPositionGuardian()
        self.hybrid_exit = HybridExitManager()
        self.journal = JournalEngine()
        self.health = HealthEngine()
        self.market = MarketDataFetcher()
        self.lock = RuntimeLock()
        self.engine = None
        self.pos_mgr = None
        self.router = None
        self.mode = os.getenv("LEVIATHAN_MODE", "testnet")
        self.symbols = []
        self.last_scan_time = None
        self.scan_results = []  # para el dashboard

    def run(self):
        if EMERGENCY_STOP.exists():
            logging.critical("Emergency stop. Exiting.")
            self._write_dashboard_state(balance=100.0, running=False)
            return
        if not self.lock.acquire():
            logging.warning("Lock held. Exiting.")
            return

        self.health.record_event("orchestrator_start")
        runtime_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.journal.start(runtime_id)

        try:
            state = bootstrap_runtime()
            self.symbols = state.get("symbols") or self._get_symbols()
            capital = state.get("balance", Config.INITIAL_CAPITAL)

            self.reconciliation.run()
            self.guardian.restore()

            strategies = [ExpansionStrategy(), PullbackStrategy(),
                          ReaccelerationStrategy(), DepressionBreakoutStrategy()]
            self.engine = RotationalEngine(strategies, self.symbols, capital, {})
            self.router = OrderRouter(live=(self.mode != "simulator"))
            self.pos_mgr = PositionManager()

            if state:
                self.engine.capital = state.get("balance", capital)
                self.engine.peak_capital = state.get("peak_capital", capital)
                self.engine.equity_curve = state.get("equity_history", [capital])
                self.engine._loop_count = state.get("loop_count", 0)
                if state.get("position"):
                    self.engine.position = state["position"]

            max_cycles = int(os.getenv("MAX_CYCLES", 8))
            for cycle in range(max_cycles):
                if EMERGENCY_STOP.exists() or (RUNTIME_DIR / "stop.txt").exists():
                    break

                # 1. Escanear y descargar datos de mercado
                market_data = self.market.fetch(self.symbols)
                self.engine.data = {sym: {"5m": df} for sym, df in market_data.items()}

                # 2. Guardar resumen del escaneo para el dashboard
                self.last_scan_time = time.strftime("%Y-%m-%d %H:%M:%S")
                self.scan_results = [
                    {"symbol": sym, "score": row["score"].iloc[-1] if "score" in row else 0,
                     "trend": row.get("trend", "NEUTRAL")}
                    for sym, df in market_data.items()
                    if not df.empty and (row := df.iloc[-1]) is not None
                ]
                self.scan_results.sort(key=lambda x: x["score"], reverse=True)

                # 3. Ejecutar ciclo del motor (scoring, selección, ejecución)
                trade = self.engine.cycle()
                if trade:
                    order = self.router.send(
                        trade["symbol"], "LONG" if trade["dir"] == 1 else "SHORT",
                        trade["size"], trade["atr"], trade["leverage"]
                    )
                    if order and order.get("status") == "filled":
                        self.pos_mgr.open(trade)
                        self.journal.log_trade("open", trade)

                # 4. Gestión de posiciones activas
                self.hybrid_exit.manage(self.engine, self.pos_mgr, market_data)

                # 5. Persistencia y snapshot
                self.persistence.save_snapshot(self.engine, self.pos_mgr)

                # 6. Escribir estado completo para el dashboard
                self._write_dashboard_state(
                    balance=self.engine.capital,
                    equity=self.engine.capital,
                    pnl=self.engine.capital - Config.INITIAL_CAPITAL,
                    position=self.engine.position,
                    loop_count=getattr(self.engine, '_loop_count', 0),
                    equity_history=self.engine.equity_curve,
                    running=True
                )

                self.journal.log_cycle(cycle, self.engine.capital)
                self.health.record_cycle()
                time.sleep(30)

        except Exception as e:
            logging.error(f"Fatal orchestrator error: {e}", exc_info=True)
            self.health.record_event("orchestrator_error")
            self._write_dashboard_state(balance=100.0, running=False, error=str(e))
        finally:
            if self.engine:
                self.persistence.save_snapshot(self.engine, self.pos_mgr)
                self._write_dashboard_state(
                    balance=self.engine.capital,
                    equity=self.engine.capital,
                    pnl=self.engine.capital - Config.INITIAL_CAPITAL,
                    position=self.engine.position,
                    loop_count=getattr(self.engine, '_loop_count', 0),
                    equity_history=self.engine.equity_curve,
                    running=True
                )
            self.journal.close()
            self.health.record_event("orchestrator_end")
            self.lock.release()

    def _write_dashboard_state(self, balance, equity=0, pnl=0, position=None,
                               loop_count=0, equity_history=None, running=False, error=None):
        """Escribe state.json con toda la actividad visible para el dashboard."""
        # Obtener trades recientes del PositionManager (últimos 10)
        recent_trades = []
        if self.pos_mgr:
            for t in self.pos_mgr.trade_history[-10:]:
                recent_trades.append({
                    "symbol": t.get("symbol", ""),
                    "strategy": t.get("strategy", ""),
                    "direction": t.get("direction", ""),
                    "entry": t.get("entry", 0),
                    "exit": t.get("exit_price", 0),
                    "pnl": t.get("pnl", 0),
                    "reason": t.get("reason", "")
                })

        state = {
            "running": running,
            "mode": self.mode,
            "balance": balance,
            "equity": equity or balance,
            "pnl": pnl,
            "position": position,
            "loop_count": loop_count,
            "last_execution": time.strftime("%Y-%m-%d %H:%M:%S"),
            "equity_history": equity_history or [balance],
            "error": error,
            "active_symbols": self.symbols,
            "scan_time": self.last_scan_time,
            "top_scan_results": self.scan_results[:5],
            "recent_trades": recent_trades,
            "heartbeat": self.health.cycles,
            "uptime": time.time() - getattr(self, 'start_time', time.time()),
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

    def _get_symbols(self):
        if self.mode == "live":
            return fetch_top100_symbols()
        return fetch_testnet_symbols()


if __name__ == "__main__":
    Orchestrator().run()
