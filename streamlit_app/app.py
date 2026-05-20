import streamlit as st
import json, os, requests, time, pandas as pd
from pathlib import Path

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
TRADES_FILE = RUNTIME_DIR / "trades.csv"
METRICS_FILE = RUNTIME_DIR / "metrics.json"
LOGS_FILE = RUNTIME_DIR / "logs" / "engine.log"

GH_TOKEN = os.getenv("GH_TOKEN", "")
REPO = "oz10000/leviathan_pro_v5.2"
WORKFLOW_ID = "leviathan_runtime.yml"

def load_json(file):
    if file.exists():
        with open(file) as f: return json.load(f)
    return {}

def trigger_workflow():
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    res = requests.post(url, json={"ref":"main"}, headers=headers)
    return res.status_code == 204

def cancel_workflow():
    runs_url = f"https://api.github.com/repos/{REPO}/actions/runs?status=in_progress"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    r = requests.get(runs_url, headers=headers)
    if r.status_code == 200 and r.json().get("workflow_runs"):
        run_id = r.json()["workflow_runs"][0]["id"]
        cancel_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/cancel"
        requests.post(cancel_url, headers=headers)
        return True
    return False

# ── Panel de control ──
st.sidebar.title("⚙️ Engine Control")
if st.sidebar.button("▶️ START WORKFLOW"):
    if trigger_workflow():
        st.sidebar.success("Workflow triggered")
    else:
        st.sidebar.error("Failed to start workflow")
if st.sidebar.button("⏹️ STOP WORKFLOW"):
    if cancel_workflow():
        st.sidebar.success("Workflow cancelled")
    else:
        st.sidebar.warning("No active workflow found")

# ── Dashboard ──
st.title("🐙 LEVIATHAN EDGE DASHBOARD")
state = load_json(STATE_FILE)
metrics = load_json(METRICS_FILE)

if state:
    col1, col2, col3 = st.columns(3)
    col1.metric("Balance", f"${state.get('balance',0):.2f}")
    col2.metric("Equity", f"${state.get('equity',0):.2f}")
    col3.metric("PnL", f"{state.get('pnl',0):+.2f}")
    st.write(f"**Mode:** {state.get('mode','')} | **Loops:** {state.get('loop_count',0)}")

    if state.get("position"):
        pos = state["position"]
        st.write(f"**Open Position:** {pos.get('strategy','')} {pos.get('symbol','')} @ {pos.get('entry')}")

    # Métricas
    if metrics:
        status = " (⚠️ preliminary)" if metrics.get("status")=="preliminary" else " (✅ validated)"
        st.subheader(f"Real‑time Metrics{status}")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Win Rate", f"{metrics.get('winrate',0):.1%}")
        c2.metric("Profit Factor", f"{metrics.get('profit_factor',0):.2f}")
        c3.metric("Sharpe", f"{metrics.get('sharpe',0):.2f}")
        c4.metric("Max DD", f"{metrics.get('maxdd',0):.2%}")

    # Trades
    if TRADES_FILE.exists():
        try:
            trades_df = pd.read_csv(TRADES_FILE)
            if not trades_df.empty:
                st.subheader("Recent Trades")
                st.dataframe(trades_df.tail(10))
        except: pass

    # Logs recientes
    if LOGS_FILE.exists():
        with open(LOGS_FILE) as f:
            lines = f.readlines()[-20:]
        if lines:
            st.subheader("Recent Engine Logs")
            st.text("".join(lines))

    # Equity
    if state.get("equity_history"):
        st.subheader("Equity Curve")
        st.line_chart(state["equity_history"])

    st.info("🔍 Backtest Sharpe 6.95 is theoretical; live metrics will converge with sufficient trades.")
else:
    st.info("Engine not running. Press START WORKFLOW to begin.")
