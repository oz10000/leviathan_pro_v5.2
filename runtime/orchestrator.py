#!/usr/bin/env python3
"""
LEVIATHAN ORCHESTRATOR — FULLY RESILIENT RUNTIME
- Logging rotativo por hora
- Escaneo continuo de activos
- Descarga de datos tolerante a fallos
- Ejecución del RotationalEngine real
- Gestión de trades con protección catastrófica
- Persistencia atómica y auto‑recuperación
- Dashboard con ranking de oportunidades en tiempo real
"""
import sys, os, time, json, signal, logging, logging.handlers, hashlib, random, traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Paths ──
REPO_ROOT = Path(__file__).resolve().parent.parent
EDGE_CORE = REPO_ROOT / "leviathan_edge_core"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EDGE_CORE))

# ── Configurar logging rotativo por hora ──
def setup_logging():
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    handler = logging.handlers.TimedRotatingFileHandler(
        logs_dir / "engine.log",
        when="H",
        interval=1,
        backupCount=168  # 7 días
    )
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

setup_logging()

# ── Imports del Edge Core (después de agregar el path) ──
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

# ── Módulos del runtime ──
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
STATE_FILE = RUNTIME_DIR / "state.json"
ERRORS_FILE = RUNTIME_DIR / "errors.json"
EMERGENCY_STOP = RUNTIME_DIR / "emergency_stop.txt"

FALLBACK_TESTNET_SYMBOLS = [
    "BTC","ETH","SOL","BNB","XRP","DOGE","ADA","LINK","LTC","TRX"
]


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

        self.engine: Optional[RotationalEngine] = None
        self.pos_mgr: Optional[PositionManager] = None
        self.router: Optional[OrderRouter] = None

        self.mode = os.getenv("LEVIATHAN_MODE", "testnet")
        self.symbols: List[str] = []
        self.start_time = time.time()
        self.current_action = "Initializing"
        self.cycle_count = 0
        self.failed_cycles = 0
        self.last_error: Optional[str] = None

        # Estadísticas de escaneo
        self.scan_stats = {
            "scan_time": None,
            "scan_duration": 0.0,
            "symbols_scanned": 0,
            "valid_symbols": 0,
            "failed_symbols": 0,
            "top_scan_results": [],
        }

    def _get_symbols(self) -> List[str]:
        """Obtiene los símbolos según el modo, con fallback."""
        try:
            if self.mode == "live":
                symbols = fetch_top100_symbols()
            else:
                symbols = fetch_testnet_symbols()
            if not symbols:
                raise ValueError("Empty symbol list")
            return symbols
        except Exception as e:
            logging.warning(f"Could not fetch symbols: {e}, using fallback list")
            return FALLBACK_TESTNET_SYMBOLS

    def run(self):
        """Bucle principal del orquestador."""
        if EMERGENCY_STOP.exists():
            logging.critical("Emergency stop. Exiting.")
            self._write_dashboard_state(running=False, error="emergency_stop")
            return

        if not self.lock.acquire():
            logging.warning("Lock held. Exiting.")
            return

        self.health.record_event("orchestrator_start")
        runtime_id = hashlib.md5(str(self.start_time).encode()).hexdigest()[:8]
        self.journal.start(runtime_id)

        try:
            # 1. Bootstrap
            state = bootstrap_runtime()
            self.symbols = state.get("symbols") or self._get_symbols()
            capital = state.get("balance", Config.INITIAL_CAPITAL)

            # 2. Reconciliación y guardián (no bloqueantes)
            self.current_action = "Reconciling with exchange"
            try:
                self.reconciliation.run()
            except Exception as e:
                logging.error(f"Reconciliation failed (non‑fatal): {e}")

            try:
                self.guardian.restore()
            except Exception as e:
                logging.error(f"Guardian restore failed (non‑fatal): {e}")

            # 3. Instanciar motor real
            self.current_action = "Initializing engine"
            strategies = [ExpansionStrategy(), PullbackStrategy(),
                          ReaccelerationStrategy(), DepressionBreakoutStrategy()]
            self.engine = RotationalEngine(strategies, self.symbols, capital, {})
            self.router = OrderRouter(live=(self.mode != "simulator"))
            self.pos_mgr = PositionManager()

            # Restaurar estado previo
            if state:
                self.engine.capital = state.get("balance", capital)
                self.engine.peak_capital = state.get("peak_capital", capital)
                self.engine.equity_curve = state.get("equity_history", [capital])
                self.engine._loop_count = state.get("loop_count", 0)
                if state.get("position"):
                    self.engine.position = state["position"]

            self.start_time = time.time()
            max_cycles = int(os.getenv("MAX_CYCLES", 8))

            # 4. Bucle de trading
            for cycle in range(max_cycles):
                if EMERGENCY_STOP.exists() or (RUNTIME_DIR / "stop.txt").exists():
                    break

                try:
                    self._execute_cycle()
                except Exception as e:
                    self.failed_cycles += 1
                    self.last_error = str(e)
                    logging.error(f"Cycle {cycle} FATAL ERROR: {e}\n{traceback.format_exc()}")
                    self._write_error(str(e))
                finally:
                    # Siempre guardar estado tras cada ciclo
                    self._write_dashboard_state(running=True)
                    if self.engine:
                        self.persistence.save_snapshot(self.engine, self.pos_mgr)
                    self.health.record_cycle()
                    self.cycle_count += 1
                    time.sleep(30)

        except Exception as e:
            logging.critical(f"Orchestrator FATAL: {e}\n{traceback.format_exc()}")
            self._write_dashboard_state(running=False, error=str(e))
            self._write_error(str(e))
        finally:
            if self.engine:
                self.persistence.save_snapshot(self.engine, self.pos_mgr)
                self._write_dashboard_state(running=True)
            self.journal.close()
            self.health.record_event("orchestrator_end")
            self.lock.release()

    def _execute_cycle(self):
        """Un ciclo completo: escanear, evaluar, ejecutar, gestionar."""
        # 1. Escanear y descargar datos de mercado (resiliente)
        self.current_action = "Downloading market data"
        scan_start = time.time()
        market_data, scan_errors = self.market.fetch_with_retry(self.symbols)
        self.scan_stats["scan_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scan_stats["scan_duration"] = time.time() - scan_start
        self.scan_stats["symbols_scanned"] = len(self.symbols)
        self.scan_stats["valid_symbols"] = len(market_data)
        self.scan_stats["failed_symbols"] = len(self.symbols) - len(market_data)

        if not market_data:
            logging.warning("No market data for any symbol. Skipping cycle.")
            self.current_action = "Waiting for next cycle (no data)"
            return

        # 2. Calcular scores y ranking
        self.current_action = "Computing features & ranking"
        ranked = []
        for sym, df in market_data.items():
            try:
                if df.empty or "score" not in df.columns:
                    continue
                score = df["score"].iloc[-1]
                trend = df["trend"].iloc[-1] if "trend" in df.columns else "NEUTRAL"
                ranked.append({"symbol": sym, "score": score, "trend": trend})
            except Exception as e:
                logging.warning(f"Score calc error for {sym}: {e}")

        ranked.sort(key=lambda x: x["score"], reverse=True)
        self.scan_stats["top_scan_results"] = ranked[:5]

        # 3. Ejecutar el motor (el RotationalEngine ya itera sobre su universo)
        self.current_action = "Running engine cycle"
        self.engine.data = {sym: {"5m": df} for sym, df in market_data.items()}
        try:
            trade = self.engine.cycle()
        except Exception as e:
            logging.error(f"Engine cycle error: {e}")
            trade = None

        # 4. Si hay señal, ejecutar orden real
        if trade:
            self.current_action = f"Opening position: {trade['symbol']}"
            try:
                order = self.router.send(
                    trade["symbol"],
                    "LONG" if trade["dir"] == 1 else "SHORT",
                    trade["size"], trade["atr"], trade["leverage"]
                )
                if order and order.get("status") == "filled":
                    self.pos_mgr.open(trade)
                    self.journal.log_trade("open", trade)
                    logging.info(f"[TRADE] OPEN {trade['symbol']} {trade['strategy']} size={trade['size']:.6f}")
            except Exception as e:
                logging.error(f"Order send failed for {trade['symbol']}: {e}")

        # 5. Gestión de posiciones activas (salidas)
        self.current_action = "Managing positions"
        try:
            self.hybrid_exit.manage(self.engine, self.pos_mgr, market_data)
        except Exception as e:
            logging.error(f"Exit management error: {e}")

        self.current_action = "Sleeping"

    def _write_dashboard_state(self, running: bool, error: Optional[str] = None):
        """Escribe state.json con todos los campos que el dashboard necesita."""
        capital = self.engine.capital if self.engine else 100.0
        equity = capital
        pnl = capital - Config.INITIAL_CAPITAL if self.engine else 0.0
        position = self.engine.position if self.engine else None

        # Últimos 10 trades desde el PositionManager
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
            "balance": capital,
            "equity": equity,
            "pnl": pnl,
            "position": position,
            "loop_count": self.engine._loop_count if self.engine else self.cycle_count,
            "last_execution": time.strftime("%Y-%m-%d %H:%M:%S"),
            "equity_history": self.engine.equity_curve if self.engine else [capital],
            "error": error,
            "active_symbols": self.symbols,
            "scan_time": self.scan_stats.get("scan_time"),
            "scan_duration": self.scan_stats.get("scan_duration", 0),
            "symbols_scanned": self.scan_stats.get("symbols_scanned", 0),
            "valid_symbols": self.scan_stats.get("valid_symbols", 0),
            "failed_symbols": self.scan_stats.get("failed_symbols", 0),
            "top_scan_results": self.scan_stats.get("top_scan_results", []),
            "recent_trades": recent_trades,
            "current_action": self.current_action,
            "heartbeat": self.health.cycles,
            "uptime": time.time() - self.start_time,
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

    def _write_error(self, message: str):
        """Registra el último error para el dashboard."""
        with open(ERRORS_FILE, 'w') as f:
            json.dump({"message": message, "time": time.time()}, f)


if __name__ == "__main__":
    Orchestrator().run()
