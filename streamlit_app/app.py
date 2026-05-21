import streamlit as st
import json, os, requests, time, pandas as pd
from pathlib import Path

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

st.title("🐙 LEVIATHAN EDGE DASHBOARD")

# ── Panel de control ──
st.sidebar.title("⚙️ Control")
if st.sidebar.button("🔄 Refresh Now"):
    st.experimental_rerun()

# ── Estado general ──
state = load_state()
if state:
    col1, col2, col3 = st.columns(3)
    col1.metric("Balance", f"${state.get('balance',0):.2f}")
    col2.metric("Equity", f"${state.get('equity',0):.2f}")
    col3.metric("PnL", f"{state.get('pnl',0):+.2f}")
    st.write(f"**Mode:** {state.get('mode','')} | **Loops:** {state.get('loop_count',0)}")
    st.write(f"**Last execution:** {state.get('last_execution','')}")

    # ── Escaneo de mercado ──
    if state.get("top_scan_results"):
        st.subheader("📡 Latest Market Scan")
        st.write(f"Scan time: {state.get('scan_time','')} | Symbols: {len(state.get('active_symbols',[]))}")
        scan_df = pd.DataFrame(state["top_scan_results"])
        st.dataframe(scan_df, use_container_width=True)

    # ── Posición abierta ──
    if state.get("position"):
        pos = state["position"]
        st.subheader("📌 Open Position")
        st.write(f"**{pos.get('strategy','')} {pos.get('symbol','')}** "
                 f"{'LONG' if pos.get('dir')==1 else 'SHORT'} "
                 f"Entry: {pos.get('entry'):.2f} | SL: {pos.get('sl','?'):.2f} | TP: {pos.get('tp','?'):.2f}")

    # ── Trades recientes ──
    if state.get("recent_trades"):
        st.subheader("📋 Recent Trades")
        trades_df = pd.DataFrame(state["recent_trades"])
        st.dataframe(trades_df, use_container_width=True)

    # ── Métricas ──
    if state.get("equity_history"):
        st.subheader("📈 Equity Curve")
        st.line_chart(state["equity_history"])

    # ── Runtime health ──
    st.subheader("🩺 Runtime Health")
    st.write(f"Heartbeat cycles: {state.get('heartbeat',0)}")
    st.write(f"Uptime: {state.get('uptime',0):.0f} s")
    if state.get("error"):
        st.error(f"Last error: {state['error']}")
else:
    st.info("Engine not running. Start the workflow from GitHub Actions.")
