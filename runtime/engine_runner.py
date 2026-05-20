#!/usr/bin/env python3
"""
LEVIATHAN ENGINE RUNNER – FINAL UNIFIED RUNTIME
Con lock file, persistencia de posiciones, rate limit y recuperación.
"""
import sys, os, time, json, signal, logging, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np

# Añadir raíz del repo y Edge Core al path
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

# Directorios y archivos
RUNTIME_DIR = REPO_ROOT / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)
LOG_FILE = RUNTIME_DIR / "logs" / "engine.log"
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

STATE_FILE = RUNTIME_DIR / "state.json"
TRADES_FILE = RUNTIME_DIR / "trades.csv"
METRICS_FILE = RUNTIME_DIR / "metrics.json"
POSITIONS_FILE = RUNTIME_DIR / "open_positions.json"
LOCK_FILE = RUNTIME_DIR / "engine.lock"

OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
MODE = os.getenv("LEVIATHAN_MODE", "testnet")
MAX_CYCLES = int(os.getenv("MAX_CYCLES", "8"))

# ── Evitar ejecución simultánea ──
if LOCK_FILE.exists():
    print("Engine already running (lock file exists). Exiting.")
    sys.exit(0)
LOCK_FILE.write_text(str(time.time()))

def get_optimal_workers(num_symbols):
    if num_symbols <= 10: return 2
    elif num_symbols <= 30: return 4
    else: return min(8, os.cpu_count() or 4)

class OKXDataFeed:
    def __init__(self, testnet=True):
        from app_streamlit.okx_client import OKXClient
        self.client = OKXClient(OKX_API_KEY, OKX_SECRET, OKX_PASSPHRASE, testnet=testnet)
        self.error_count = 0
        self.circuit_open = False

    def get_candles_with_retry(self, symbol, bar="5m", limit=100, retries=3):
        if self.circuit_open:
            return pd.DataFrame()
        for attempt in range(retries):
            try:
                # Rate limit: sleep aleatorio entre 0.1 y 0.5 segundos
                time.sleep(random.uniform(0.1, 0.5))
                df = self.client.get_candles(symbol, bar, limit)
                if not df.empty:
                    if "volume" not in df.columns and "vol" in df.columns:
                        df.rename(columns={"vol": "volume"}, inplace=True)
                    df = compute_features(df)
                    self.error_count = 0
                    return df
            except Exception as e:
                logging.warning(f"Fetch {symbol} fail (attempt {attempt+1}): {e}")
                time.sleep(2)
        self.error_count += 1
        if self.error_count > 5:
            self.circuit_open = True
            logging.error("Circuit breaker OPEN for OKX API")
        return pd.DataFrame()

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f: return json.load(f)
    return None

def save_state(engine, pos_mgr):
    snap = engine.get_snapshot() if hasattr(engine, 'get_snapshot') else {
        "balance": engine.capital, "equity": engine.capital,
        "pnl": engine.capital - Config.INITIAL_CAPITAL,
        "position": engine.position, "signal": None,
        "loop_count": getattr(engine, 'loop_count', 0), "last_execution": ""
    }
    state = {
        "running": True, "mode": MODE,
        "balance": snap.get("balance", engine.capital),
        "equity": snap.get("equity", engine.capital),
        "pnl": snap.get("pnl", 0.0),
        "position": engine.position,
        "signal": engine.current_state.get("current_signal") if hasattr(engine, 'current_state') else None,
        "loop_count": snap.get("loop_count", 0),
        "last_execution": snap.get("last_execution", ""),
        "oscillators": snap.get("oscillators", {}),
        "analysis_log": getattr(engine, 'current_state', {}),
        "active_symbols": engine.universe if hasattr(engine, 'universe') else [],
        "equity_history": snap.get("equity_history", []),
        "trades_count": len(pos_mgr.trade_history)
    }
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)
    # Persistir posición abierta por separado
    if engine.position:
        with open(POSITIONS_FILE, 'w') as f: json.dump(engine.position, f)
    elif POSITIONS_FILE.exists():
        POSITIONS_FILE.unlink()

def save_metrics(metrics):
    with open(METRICS_FILE, 'w') as f: json.dump(metrics, f, indent=2)

def append_trades(trades, since_index):
    write_header = not TRADES_FILE.exists()
    with open(TRADES_FILE, 'a', newline='') as f:
        import csv
        w = csv.writer(f)
        if write_header:
            w.writerow(["time","symbol","strategy","direction","entry","exit","pnl","reason"])
        for t in trades[since_index:]:
            w.writerow([t.get("time",""), t.get("symbol",""), t.get("strategy",""),
                        t.get("direction",""), t.get("entry",0), t.get("exit_price",0),
                        t.get("pnl",0), t.get("reason","")])

def compute_realtime_metrics(engine, pos_mgr):
    trades = pos_mgr.trade_history
    if len(trades) < 5: return {"status":"preliminary","trades":len(trades)}
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p>0]; losses = [p for p in pnls if p<=0]
    winrate = len(wins)/len(pnls)
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = sum(wins)/abs(sum(losses)) if sum(losses)!=0 else float('inf')
    expectancy = winrate*avg_win - (1-winrate)*abs(avg_loss)
    eq = np.array(engine.equity_curve if hasattr(engine,'equity_curve') else [Config.INITIAL_CAPITAL])
    rets = np.diff(eq)/eq[:-1]
    sharpe = np.mean(rets)/np.std(rets)*np.sqrt(365*24) if len(rets)>1 else 0
    maxdd = (np.maximum.accumulate(eq)-eq).max()/np.maximum.accumulate(eq).max()
    return {"status":"valid","trades":len(pnls),"winrate":winrate,
            "profit_factor":profit_factor,"expectancy":expectancy,
            "sharpe":sharpe,"maxdd":maxdd,"avg_win":avg_win,"avg_loss":avg_loss}

def main():
    # Determinar símbolos
    if MODE == "live":
        symbols = fetch_top100_symbols(); testnet = False
    else:
        symbols = fetch_testnet_symbols(); testnet = True

    strategies = [ExpansionStrategy(), PullbackStrategy(),
                  ReaccelerationStrategy(), DepressionBreakoutStrategy()]
    data_feed = OKXDataFeed(testnet=testnet)
    initial_capital = Config.INITIAL_CAPITAL

    # Recuperar estado anterior
    state = load_state()
    if state:
        initial_capital = state.get("balance", initial_capital)

    engine = RotationalEngine(strategies, symbols, initial_capital, {})
    router = OrderRouter(live=(MODE != "simulator"))
    pos_mgr = PositionManager()

    if state:
        engine.capital = state.get("balance", initial_capital)
        engine.peak_capital = max(engine.peak_capital, engine.capital)
        engine.equity_curve = state.get("equity_history", [engine.capital])
        engine._loop_count = state.get("loop_count", 0)

    # Recuperar posición abierta si existía
    if POSITIONS_FILE.exists():
        with open(POSITIONS_FILE) as f:
            saved_pos = json.load(f)
        engine.position = saved_pos
        logging.info("Recovered open position from disk")

    logging.info(f"Engine started in {MODE} mode with {len(symbols)} symbols")

    def graceful_shutdown(sig, frame):
        save_state(engine, pos_mgr)
        save_metrics(compute_realtime_metrics(engine, pos_mgr))
        LOCK_FILE.unlink(missing_ok=True)
        logging.info("Shutdown signal received"); sys.exit(0)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)

    n_workers = get_optimal_workers(len(symbols))
    executor = ThreadPoolExecutor(max_workers=n_workers)
    cycle = 0
    trades_index = len(pos_mgr.trade_history)

    while cycle < MAX_CYCLES:
        try:
            # Descargar datos de mercado (solo los primeros 10 símbolos por ciclo, rotando)
            symbols_slice = symbols[cycle % len(symbols): (cycle % len(symbols)) + 10]
            futures = [executor.submit(data_feed.get_candles_with_retry, sym) for sym in symbols_slice]
            market_data = {}
            for sym, future in zip(symbols_slice, futures):
                df = future.result()
                if not df.empty: market_data[sym] = df

            # Completar con datos en caché para el resto
            for sym in symbols:
                if sym not in market_data:
                    cached = data_feed.get_candles_with_retry(sym, limit=50)  # menos velas
                    if not cached.empty: market_data[sym] = cached

            engine.data = {sym: {"5m": df} for sym, df in market_data.items()}

            # Ejecutar ciclo del motor original
            trade = engine.cycle()
            if trade:
                order = router.send(trade["symbol"], "LONG" if trade["dir"]==1 else "SHORT",
                                    trade["size"], trade["atr"], trade["leverage"])
                if order.get("status") == "filled":
                    pos_mgr.open(trade)
                    logging.info(f"Trade opened: {trade['symbol']} {trade['strategy']}")

            # Gestionar posiciones abiertas
            for sym in pos_mgr.get_active_symbols():
                df = market_data.get(sym)
                if df is not None and len(df) > 0:
                    price = df["close"].iloc[-1]
                    exit_sig, reason, px, _ = HybridExit.should_exit(
                        pos_mgr.positions[sym], price, time.time())
                    if exit_sig:
                        pnl = pos_mgr.close(sym, px, reason)
                        if pnl is not None:
                            logging.info(f"Trade closed: {sym} {reason} PnL={pnl:.2f}")

            # Persistencia
            save_state(engine, pos_mgr)
            new_trades = pos_mgr.trade_history
            if len(new_trades) > trades_index:
                append_trades(new_trades, trades_index)
                trades_index = len(new_trades)
            save_metrics(compute_realtime_metrics(engine, pos_mgr))

            cycle += 1
            logging.info(f"Cycle {cycle} completed. Balance: {engine.capital:.2f}")

        except Exception as e:
            logging.error(f"Cycle error: {e}")
            time.sleep(10)

        time.sleep(30)

    save_state(engine, pos_mgr)
    save_metrics(compute_realtime_metrics(engine, pos_mgr))
    LOCK_FILE.unlink(missing_ok=True)
    executor.shutdown(wait=True)

if __name__ == "__main__":
    try:
        main()
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink(missing_ok=True)
