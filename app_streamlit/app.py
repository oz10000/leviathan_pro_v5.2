import streamlit as st
import subprocess, os, time, json, sys, pandas as pd, numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

# ────────────── PATH SETUP ──────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
EDGE_CORE = REPO_ROOT / "leviathan_edge_core"
if str(EDGE_CORE) not in sys.path:
    sys.path.insert(0, str(EDGE_CORE))

from runtime_state import load_state, save_state

RUNTIME_DIR = SCRIPT_DIR / "runtime"
PID_FILE = RUNTIME_DIR / "engine.pid"

# ────────────── UTILIDADES ──────────────
def is_engine_running():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            pass
    return False

# ────────────── SIDEBAR ──────────────
st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.selectbox("Mode", ["SIMULATOR", "TESTNET", "LIVE"])
capital = st.sidebar.slider("Initial Capital (USDT)", 1.0, 1000.0, 100.0, 10.0)
auto_lev = st.sidebar.checkbox("Auto Leverage", True)
leverage = 5
if not auto_lev:
    leverage = st.sidebar.slider("Leverage", 1, 8, 5)

st.sidebar.subheader("Accelerated Backtest")
backtest_days = st.sidebar.selectbox("Period (days)", [1, 7, 30, 90, 180], index=2)
if st.sidebar.button("Run Accelerated Backtest"):
    from core_adapter import CoreAdapter
    from backtest_engine import BacktestEngine
    adapter = CoreAdapter(mode="backtest", initial_capital=100.0)
    engine = BacktestEngine(adapter, symbols=adapter.symbols[:20], days=backtest_days)
    with st.spinner(f"Backtesting {len(engine.symbols)} symbols over {backtest_days} days..."):
        engine.download_all()
        results = engine.run()
        st.session_state["backtest_results"] = results
        st.session_state["backtest_adapter"] = adapter
    st.success(f"Backtest completed. {results['trades']} trades simulated.")

# Motor persistente
running = is_engine_running()
if st.sidebar.button("▶️ START"):
    if not running:
        state = load_state()
        state["running"] = True
        state["mode"] = mode.lower()
        state["capital"] = capital
        state["auto_leverage"] = auto_lev
        state["leverage"] = leverage
        save_state(state)
        proc = subprocess.Popen(["python", "engine_runner.py"], cwd=str(SCRIPT_DIR))
        PID_FILE.write_text(str(proc.pid))
        running = True
        st.success("Engine started – will persist even if you close this page")
    else:
        st.warning("Engine already running")

if st.sidebar.button("⏸️ STOP"):
    if running:
        state = load_state()
        state["running"] = False
        save_state(state)
        time.sleep(2)
        if PID_FILE.exists():
            PID_FILE.unlink()
        running = False
        st.success("Engine stopped")
    else:
        st.info("Engine not running")

st.sidebar.write(f"Engine: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
if running and PID_FILE.exists():
    st.sidebar.write(f"PID: {PID_FILE.read_text().strip()}")

# ────────────── DASHBOARD ──────────────
st.title("🐙 LEVIATHAN EDGE DASHBOARD")
state = load_state()

if state:
    col1, col2, col3 = st.columns(3)
    col1.metric("Balance", f"${state.get('balance',0):.2f}")
    col2.metric("Equity", f"${state.get('equity',0):.2f}")
    col3.metric("PnL", f"{state.get('pnl',0):+.2f}")
    st.write(f"Loops: {state.get('loop_count',0)} | Last cycle: {state.get('last_execution','--')}")
    if state.get("position"):
        pos = state["position"]
        st.write(f"**Position:** {'LONG' if pos.get('dir')==1 else 'SHORT'} {pos.get('symbol','')} @ {pos.get('entry')} | SL: {pos.get('sl')} | TP: {pos.get('tp')}")
    if state.get("equity_history"):
        st.subheader("Equity Curve")
        st.line_chart(state["equity_history"])
    if state.get("oscillators"):
        st.subheader("Live Oscillators")
        cols = st.columns(len(state["oscillators"]))
        for i, (name, val) in enumerate(state["oscillators"].items()):
            cols[i].metric(name, f"{val:.2f}")
else:
    st.info("Press START to begin.")

# ────────────── BACKTEST RESULTS ──────────────
if "backtest_results" in st.session_state:
    res = st.session_state["backtest_results"]
    st.subheader("Backtest Results")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Sharpe", f"{res['sharpe']:.2f}")
    col2.metric("Max DD", f"{res['maxdd']:.2%}")
    col3.metric("Win Rate", f"{res['winrate']:.1%}")
    col4.metric("Profit Factor", f"{res['profit_factor']:.2f}")
    col5.metric("Trades", res['trades'])
    st.line_chart(res["equity_history"])

    # ────────────── COMPOUND GROWTH TABLE ──────────────
    st.subheader("Compound Growth Projection")
    adapter = st.session_state.get("backtest_adapter")
    if adapter:
        growth_df = adapter.compound_growth_table(
            start_capitals=[1,2,3,4,5,6,7,8,9,10],
            num_trades_list=[10, 20, 30, 60, 120],
            leverage=4.8
        )
        st.dataframe(growth_df)

        # Leverage comparison for 30 trades
        st.subheader("Leverage Impact (10 USDT, 30 trades)")
        leverage_options = [1,2,5,8,10,25,50]
        leverage_data = []
        for lev in leverage_options:
            final_opt = 10 * (1.40** (30*0.918)) * (0.50** (30*0.082)) * (lev/4.8)  # simplificación
            leverage_data.append({"Leverage": f"{lev}x", "Final (USDT)": f"{final_opt:.2f}"})
        st.table(pd.DataFrame(leverage_data))
