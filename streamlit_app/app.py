import streamlit as st
import json, os, pandas as pd, time, requests
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

def trigger_workflow():
    """Dispara el workflow leviathan_runtime.yml"""
    gh_token = st.secrets.get("GH_TOKEN")
    if not gh_token:
        st.error("❌ GH_TOKEN no configurado en Streamlit Secrets")
        return False
    
    try:
        url = "https://api.github.com/repos/oz10000/leviathan_pro_v5.2/actions/workflows/leviathan_runtime.yml/dispatches"
        headers = {
            "Authorization": f"token {gh_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {"ref": "main"}
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 204:
            st.success("✅ Workflow disparado exitosamente")
            return True
        else:
            st.error(f"❌ Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Error al disparar workflow: {str(e)}")
        return False

def cancel_workflow():
    """Cancela los workflows activos"""
    gh_token = st.secrets.get("GH_TOKEN")
    if not gh_token:
        st.error("❌ GH_TOKEN no configurado en Streamlit Secrets")
        return False
    
    try:
        # Obtener runs activos
        url = "https://api.github.com/repos/oz10000/leviathan_pro_v5.2/actions/runs?status=in_progress"
        headers = {
            "Authorization": f"token {gh_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            cancelled_count = 0
            
            for run in runs:
                cancel_url = f"https://api.github.com/repos/oz10000/leviathan_pro_v5.2/actions/runs/{run['id']}/cancel"
                cancel_response = requests.post(cancel_url, headers=headers, timeout=10)
                
                if cancel_response.status_code == 202:
                    cancelled_count += 1
            
            if cancelled_count > 0:
                st.success(f"✅ {cancelled_count} workflow(s) cancelado(s)")
                # Crear stop.txt para shutdown limpio
                STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
                STOP_FILE.write_text("stop")
                return True
            else:
                st.info("ℹ️ No hay workflows activos para cancelar")
                return False
        else:
            st.error(f"❌ Error: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"❌ Error al cancelar workflow: {str(e)}")
        return False

# Sidebar controls
st.sidebar.title("⚙️ Engine Control")

col1, col2, col3 = st.sidebar.columns(3)

with col1:
    if st.button("▶️ START", use_container_width=True):
        trigger_workflow()

with col2:
    if st.button("⏹️ STOP", use_container_width=True):
        cancel_workflow()

with col3:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Verificar si GH_TOKEN está configurado
if not st.secrets.get("GH_TOKEN"):
    st.sidebar.warning("⚠️ GH_TOKEN no configurado. Agrega en Streamlit Cloud → Settings → Secrets")

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
