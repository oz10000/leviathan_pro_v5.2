import streamlit as st
import subprocess, os, time, json, sys
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

# ────────────── PATH SETUP ──────────────
SCRIPT_DIR = Path(__file__).resolve().parent
EDGE_CORE = SCRIPT_DIR.parent / "leviathan_edge_core"
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
