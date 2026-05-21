#!/usr/bin/env python3
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

    def run(self):
        if EMERGENCY_STOP.exists():
            logging.critical("Emergency stop. Exiting.")
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

                market_data = self.market.fetch(self.symbols)
                self.engine.data = {sym: {"5m": df} for sym, df in market_data.items()}

                trade = self.engine.cycle()
                if trade:
                    order = self.router.send(
                        trade["symbol"], "LONG" if trade["dir"]==1 else "SHORT",
                        trade["size"], trade["atr"], trade["leverage"]
                    )
                    if order and order.get("status") == "filled":
                        self.pos_mgr.open(trade)
                        self.journal.log_trade("open", trade)

                self.hybrid_exit.manage(self.engine, self.pos_mgr, market_data)
                self.persistence.save_snapshot(self.engine, self.pos_mgr)
                self.journal.log_cycle(cycle, self.engine.capital)
                self.health.record_cycle()
                time.sleep(30)

        except Exception as e:
            logging.error(f"Fatal orchestrator error: {e}", exc_info=True)
            self.health.record_event("orchestrator_error")
        finally:
            self.persistence.save_snapshot(self.engine, self.pos_mgr)
            self.journal.close()
            self.health.record_event("orchestrator_end")
            self.lock.release()

    def _get_symbols(self):
        if self.mode == "live":
            return fetch_top100_symbols()
        return fetch_testnet_symbols()

if __name__ == "__main__":
    Orchestrator().run()
