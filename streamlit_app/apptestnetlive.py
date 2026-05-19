import streamlit as st
import json, os, pandas as pd, time
from pathlib import Path

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
TRADES_FILE = RUNTIME_DIR / "trades.csv"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

st.title("🐙 LEVIATHAN EDGE DASHBOARD")

# Mostrar estado si existe
state = load_state()
if state:
    col1, col2, col3 = st.columns(3)
    col1.metric("Balance", f"${state.get('balance',0):.2f}")
    col2.metric("Equity", f"${state.get('equity',0):.2f}")
    col3.metric("PnL", f"{state.get('pnl',0):+.2f}")
    st.write(f"Loops: {state.get('loop_count',0)} | Last: {state.get('last_execution','')}")
    
    # Equity curve
    if state.get("equity_history"):
        st.line_chart(state["equity_history"])
    
    # Backtest metrics (si vienen del motor)
    if state.get("backtest_metrics"):
        bm = state["backtest_metrics"]
        st.subheader("Backtest Metrics")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Sharpe", f"{bm.get('sharpe',0):.2f}")
        c2.metric("Max DD", f"{bm.get('maxdd',0):.2%}")
        c3.metric("Win Rate", f"{bm.get('winrate',0):.1%}")
        c4.metric("Profit Factor", f"{bm.get('profit_factor',0):.2f}")

    # Trades recientes
    if TRADES_FILE.exists():
        try:
            trades_df = pd.read_csv(TRADES_FILE)
            if not trades_df.empty:
                st.subheader("Recent Trades")
                st.dataframe(trades_df.tail(20))
        except:
            pass
else:
    st.info("Engine not running. Start workflow or local engine_runner.py")
