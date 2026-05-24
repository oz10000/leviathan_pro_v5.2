import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, timezone
import plotly.graph_objects as go

st.set_page_config(page_title="🐋 Leviathan Control Center", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E4EA; }
    .main-header { font-size: 2rem; font-weight: 700; color: #58A6FF; margin-bottom: 0.5rem; }
    .status-card { background-color: #161B22; border-radius: 16px; padding: 1.5rem;
                   margin: 0.5rem 0; border: 1px solid #30363D; text-align: center; }
    .status-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
                    color: #8B949E; margin-bottom: 0.3rem; }
    .status-value { font-size: 1.6rem; font-weight: 700; }
    .running { color: #00D2A1; animation: pulse-glow 1.5s infinite; }
    @keyframes pulse-glow { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .waiting { color: #D29922; }
    .sleeping { color: #E67E22; }
    .dead { color: #FF4D4D; }
    .shutdown { color: #8B949E; }
    .metric-card { background-color: #161B22; border-radius: 12px; padding: 1rem;
                   margin: 0.3rem 0; border: 1px solid #30363D; }
    .metric-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;
                    color: #8B949E; }
    .metric-value { font-size: 1.3rem; font-weight: 600; color: #58A6FF; }
    .component-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0; }
    .component-badge { background-color: #1C2129; border-radius: 20px; padding: 0.3rem 0.8rem;
                       font-size: 0.75rem; color: #C9D1D9; border: 1px solid #30363D; }
    .component-badge.active { border-color: #00D2A1; color: #00D2A1; }
    .component-badge.error { border-color: #FF4D4D; color: #FF4D4D; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH   = os.path.join(BASE_DIR, "runtime", "state.json")
TRADES_PATH  = os.path.join(BASE_DIR, "runtime", "trades.csv")
LOG_PATH     = os.path.join(BASE_DIR, "runtime", "logs", "engine.log")
METRICS_PATH = os.path.join(BASE_DIR, "runtime", "metrics.json")
CONTROL_PATH = os.path.join(BASE_DIR, "runtime", "runtime_control.json")
CACHE_DIR    = os.path.join(BASE_DIR, "runtime", "cache")

@st.cache_data(ttl=8)
def load_state():
    if not os.path.exists(STATE_PATH): return {}
    try:
        with open(STATE_PATH, "r") as f: return json.load(f)
    except: return {}

@st.cache_data(ttl=8)
def load_metrics():
    if not os.path.exists(METRICS_PATH): return {}
    try:
        with open(METRICS_PATH, "r") as f: return json.load(f)
    except: return {}

@st.cache_data(ttl=8)
def load_control():
    if not os.path.exists(CONTROL_PATH): return {"bot_enabled": True, "allow_new_entries": True, "shutdown_requested": False}
    try:
        with open(CONTROL_PATH, "r") as f: return json.load(f)
    except: return {"bot_enabled": True, "allow_new_entries": True, "shutdown_requested": False}

def save_control(control: dict):
    control["last_modified"] = datetime.now(timezone.utc).isoformat()
    control["modified_by"] = "dashboard"
    tmp = CONTROL_PATH + ".tmp"
    with open(tmp, "w") as f: json.dump(control, f, indent=2)
    os.replace(tmp, CONTROL_PATH)

@st.cache_data(ttl=30)
def load_trades():
    if not os.path.exists(TRADES_PATH): return pd.DataFrame()
    try:
        df = pd.read_csv(TRADES_PATH)
        for col in ["entry","exit","pnl","meta_score"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
        if "timestamp" in df.columns: df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=6)
def load_logs_tail(n=35):
    if not os.path.exists(LOG_PATH): return ["(log not found)"]
    try:
        with open(LOG_PATH, "r") as f: lines = f.readlines()
        return lines[-n:] if lines else ["(log empty)"]
    except: return ["(error reading log)"]

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=8_000, key="dashboard-refresh")

state   = load_state()
metrics = load_metrics()
control = load_control()
trades_df = load_trades()
logs    = load_logs_tail(35)

st.markdown('<div class="main-header">🐋 LEVIATHAN CONTROL CENTER</div>', unsafe_allow_html=True)

# Heartbeat + estado
now_ts = datetime.now(timezone.utc)
last_exec = state.get("last_execution")
delta_sec = 9999
estado = "UNKNOWN"
estado_color = "#8B949E"
if last_exec:
    try:
        last_dt = datetime.fromisoformat(last_exec)
        delta_sec = (now_ts - last_dt).total_seconds()
        if delta_sec < 60:
            estado = "RUNNING"
            estado_color = "#00D2A1"
        elif delta_sec < 300:
            estado = "WAITING"
            estado_color = "#D29922"
        elif delta_sec < 600:
            estado = "SLEEPING"
            estado_color = "#E67E22"
        else:
            estado = "NO HEARTBEAT"
            estado_color = "#FF4D4D"
    except:
        estado = "NO HEARTBEAT"
        estado_color = "#FF4D4D"

if not control.get("bot_enabled", True):
    estado = "SHUTDOWN"
    estado_color = "#8B949E"

st.markdown(f"""
<div class="status-card">
    <div class="status-label">SYSTEM STATUS</div>
    <div class="status-value" style="color:{estado_color};">● {estado}</div>
    <div style="margin-top:0.5rem; font-size:0.85rem; color:#8B949E;">
        Último ciclo: {delta_sec:.0f}s atrás · Próximo en ~{max(0,300-int(delta_sec))}s
    </div>
</div>
""", unsafe_allow_html=True)

# Indicadores de componentes
comps = {
    "API": last_exec is not None,
    "DAPS": state.get("daps_x") is not None,
    "CACHE": os.path.exists(CACHE_DIR),
    "PERSIST": os.path.exists(STATE_PATH),
    "METRICS": os.path.exists(METRICS_PATH),
    "BREAKER": not state.get("breaker", {}).get("cooldown_active", False),
    "STATGUARD": state.get("status") != "STAT_GUARD_BLOCK"
}
badges = '<div class="component-row">'
for name, ok in comps.items():
    cls = "active" if ok else "error"
    badges += f'<span class="component-badge {cls}">{name}</span>'
badges += '</div>'
st.markdown(badges, unsafe_allow_html=True)

# Botón STOP/START
col1, col2 = st.columns(2)
with col1:
    if control.get("bot_enabled", True):
        if st.button("⏹️ STOP BOT"):
            control["bot_enabled"] = False
            save_control(control)
            st.rerun()
    else:
        if st.button("▶️ START BOT"):
            control["bot_enabled"] = True
            save_control(control)
            st.rerun()
with col2:
    st.caption(f"Modo: {'DEMO TESTNET' if True else 'LIVE'}")

# Métricas principales
col1, col2, col3, col4 = st.columns(4)
col1.markdown(f'<div class="metric-card"><div class="metric-label">Balance</div><div class="metric-value">${state.get("balance",0):,.2f}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="metric-card"><div class="metric-label">Equity</div><div class="metric-value">${state.get("equity",0):,.2f}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="metric-card"><div class="metric-label">DAPS x</div><div class="metric-value">{state.get("daps_x",0):.4f}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="metric-card"><div class="metric-label">Equilibrium</div><div class="metric-value">{state.get("equilibrium",1):.4f}</div></div>', unsafe_allow_html=True)

# Seguridad
st.subheader("🛡 Safety")
cs1, cs2, cs3 = st.columns(3)
breaker_active = state.get("breaker", {}).get("cooldown_active", False)
stat_block = state.get("status") == "STAT_GUARD_BLOCK"
safe_mode = metrics.get("safe_mode", False)
cs1.success("Circuit Breaker OK") if not breaker_active else cs1.error("Circuit Breaker ACTIVO")
cs2.success("Statistical Guard OK") if not stat_block else cs2.warning("Statistical Guard BLOQUEANDO")
cs3.info("Safe‑risk activo") if safe_mode else cs3.success("Riesgo normal")

# Métricas runtime
if metrics:
    st.subheader("📊 Runtime")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ciclos", metrics.get("cycles_completed",0))
    c2.metric("Señales gen.", metrics.get("signals_generated",0))
    c3.metric("Filtradas", metrics.get("signals_filtered",0))
    c4.metric("Avg ciclo (ms)", f"{metrics.get('average_cycle_ms',0):.0f}")

# Logs en vivo
st.subheader("📜 Live Logs")
log_text = "".join(logs) if logs else "No logs yet."
st.text_area("Últimas líneas", log_text, height=220, disabled=True)

# Posiciones abiertas
st.subheader("📌 Posiciones Abiertas")
open_pos = state.get("open_positions", {})
if not open_pos:
    st.info("Sin posiciones abiertas.")
else:
    rows = [{"Symbol": sym, "Direction": p.get("direction"), "Entry": p.get("entry"),
             "Leverage": f"{p.get('leverage',1):.1f}x", "Size": f"{p.get('size',0):.4f}",
             "Meta Score": f"{p.get('meta_score',0):.2f}"} for sym, p in open_pos.items()]
    st.table(pd.DataFrame(rows))

# Historial de trades
with st.expander("📋 Historial de Trades"):
    if trades_df.empty:
        st.info("No hay trades registrados.")
    else:
        st.dataframe(trades_df.sort_values("timestamp", ascending=False).head(40), use_container_width=True)

# Curva de equity
if not trades_df.empty:
    st.subheader("📈 Equity")
    df_eq = trades_df.sort_values("timestamp")
    df_eq["cum_pnl"] = df_eq["pnl"].cumsum()
    init_balance = state.get("balance", 10000) - df_eq["cum_pnl"].iloc[-1] if len(df_eq) else 10000
    df_eq["equity"] = init_balance + df_eq["cum_pnl"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_eq["timestamp"], y=df_eq["equity"], mode='lines', name='Equity', line=dict(color='#58A6FF', width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", margin=dict(l=0,r=0,t=10,b=10), height=300)
    st.plotly_chart(fig, use_container_width=True)

st.caption("Leviathan Control Center v5.2 · Recovery‑First Design")
