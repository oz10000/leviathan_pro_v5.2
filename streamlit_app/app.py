import streamlit as st
import json, os, pandas as pd, time
from pathlib import Path

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
TRADES_FILE = RUNTIME_DIR / "trades.csv"
STOP_FILE = RUNTIME_DIR / "stop.txt"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

# Sidebar controls
st.sidebar.title("⚙️ Engine Control")
if st.sidebar.button("⏹️ STOP"):
    STOP_FILE.write_text("stop")
    st.sidebar.success("Stop signal sent. Engine will shut down gracefully.")
if st.sidebar.button("🔄 Refresh"):
    st.experimental_rerun()

st.title("🐙 LEVIATHAN EDGE DASHBOARD")
state = load_state()

if state:
    col1, col2, col3 = st.columns(3)
    col1.metric("Balance", f"${state.get('balance',0):.2f}")
    col2.metric("Equity", f"${state.get('equity',0):.2f}")
    col3.metric("PnL", f"{state.get('pnl',0):+.2f}")

    st.write(f"**Loop count:** {state.get('loop_count',0)} | **Last cycle:** {state.get('last_execution','')}")
    if state.get("signal"):
        st.write(f"**Current Signal:** {state['signal']}")

    # Trades table
    if TRADES_FILE.exists():
        try:
            trades = pd.read_csv(TRADES_FILE)
            if not trades.empty:
                st.subheader("Recent Trades")
                st.dataframe(trades.tail(20))
        except Exception:
            pass

    # Metrics
    if state.get("backtest_metrics"):
        bm = state["backtest_metrics"]
        st.subheader("Key Metrics")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Sharpe", f"{bm.get('sharpe',0):.2f}")
        c2.metric("Max DD", f"{bm.get('maxdd',0):.2%}")
        c3.metric("Win Rate", f"{bm.get('winrate',0):.1%}")
        c4.metric("Profit Factor", f"{bm.get('profit_factor',0):.2f}")
else:
    st.info("Engine not running. Start the workflow or local runner.")
