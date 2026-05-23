import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, timezone
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="🐋 Leviathan Control Center",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# ESTILOS VISUALES PROFESIONALES
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E4EA; }
    .main-header { font-size: 2rem; font-weight: 700; color: #58A6FF; margin-bottom: 0.5rem; }
    .status-card { background-color: #161B22; border-radius: 16px; padding: 1.5rem;
                   margin: 0.5rem 0; border: 1px solid #30363D; text-align: center; }
    .status-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
                    color: #8B949E; margin-bottom: 0.3rem; }
    .status-value { font-size: 1.6rem; font-weight: 700; }
    .alive-pulse { color: #00D2A1; animation: pulse-glow 1.5s infinite; }
    @keyframes pulse-glow { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .dead-text { color: #FF4D4D; }
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
    .alert-red { background-color: #2D1B1B; border-left: 4px solid #FF4D4D;
                 padding: 0.8rem; border-radius: 6px; margin: 0.5rem 0; }
    .alert-green { background-color: #1B2D1B; border-left: 4px solid #00D2A1;
                   padding: 0.8rem; border-radius: 6px; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# RUTAS ABSOLUTAS
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH   = os.path.join(BASE_DIR, "runtime", "state.json")
TRADES_PATH  = os.path.join(BASE_DIR, "runtime", "trades.csv")
LOG_PATH     = os.path.join(BASE_DIR, "runtime", "logs", "engine.log")
METRICS_PATH = os.path.join(BASE_DIR, "runtime", "metrics.json")
CONTROL_PATH = os.path.join(BASE_DIR, "runtime", "runtime_control.json")
CACHE_DIR    = os.path.join(BASE_DIR, "runtime", "cache")

# ---------------------------------------------------------------------------
# FUNCIONES DE CARGA SEGURA (con caché de corta duración)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=8)
def load_state():
    if not os.path.exists(STATE_PATH): return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

@st.cache_data(ttl=8)
def load_metrics():
    if not os.path.exists(METRICS_PATH): return {}
    try:
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

@st.cache_data(ttl=8)
def load_control():
    if not os.path.exists(CONTROL_PATH):
        return {"bot_enabled": True, "allow_new_entries": True, "shutdown_requested": False}
    try:
        with open(CONTROL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {"bot_enabled": True, "allow_new_entries": True, "shutdown_requested": False}

def save_control(control: dict):
    """Escritura atómica del archivo de control."""
    control["last_modified"] = datetime.now(timezone.utc).isoformat()
    control["modified_by"] = "dashboard"
    tmp = CONTROL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(control, f, indent=2)
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
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:] if lines else ["(log empty)"]
    except: return ["(error reading log)"]

# ---------------------------------------------------------------------------
# AUTO‑REFRESH SEGURO (cada 8 segundos)
# ---------------------------------------------------------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=8_000, key="dashboard-refresh")

# ---------------------------------------------------------------------------
# DATOS VIVOS
# ---------------------------------------------------------------------------
state   = load_state()
metrics = load_metrics()
control = load_control()
trades_df = load_trades()
logs    = load_logs_tail(35)

# ---------------------------------------------------------------------------
# CABECERA PRINCIPAL
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">🐋 LEVIATHAN CONTROL CENTER</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HEARTBEAT Y ESTADO GENERAL
# ---------------------------------------------------------------------------
col_hb, col_ctrl = st.columns([2.5, 1])

with col_hb:
    now_ts = datetime.now(timezone.utc)
    last_exec = state.get("last_execution")
    alive = False
    delta_sec = 9999
    if last_exec:
        try:
            last_dt = datetime.fromisoformat(last_exec)
            delta_sec = (now_ts - last_dt).total_seconds()
            alive = delta_sec < 120
        except: pass

    # Bloque visual de estado
    if alive:
        st.markdown(f"""
        <div class="status-card">
            <div class="status-label">SYSTEM STATUS</div>
            <div class="status-value alive-pulse">● ALIVE</div>
            <div style="margin-top:0.5rem; font-size:0.85rem; color:#8B949E;">
                Último ciclo: {delta_sec:.0f}s atrás
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-card">
            <div class="status-label">SYSTEM STATUS</div>
            <div class="status-value dead-text">● NO HEARTBEAT</div>
            <div style="margin-top:0.5rem; font-size:0.85rem; color:#8B949E;">
                Sin señal desde: {delta_sec:.0f}s
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Indicadores de componentes (badges)
    comps = {
        "API": last_exec is not None,
        "DAPS": state.get("daps_x") is not None,
        "CACHE": os.path.exists(CACHE_DIR),
        "PERSIST": os.path.exists(STATE_PATH),
        "METRICS": os.path.exists(METRICS_PATH),
        "BREAKER": not state.get("breaker", {}).get("cooldown_active", False),
        "STATGUARD": state.get("status") != "STAT_GUARD_BLOCK"
    }
    badges_html = '<div class="component-row">'
    for name, ok in comps.items():
        cls = "active" if ok else "error"
        badges_html += f'<span class="component-badge {cls}">{name}</span>'
    badges_html += '</div>'
    st.markdown(badges_html, unsafe_allow_html=True)

with col_ctrl:
    st.subheader("Control")
    if control.get("bot_enabled", True):
        if st.button("⏹️ STOP BOT", help="Detiene nuevas entradas. Las posiciones abiertas se mantienen."):
            control["bot_enabled"] = False
            save_control(control)
            st.rerun()
        st.success("BOT RUNNING")
    else:
        if st.button("▶️ START BOT", help="Reanuda la generación de nuevas entradas."):
            control["bot_enabled"] = True
            control["shutdown_requested"] = False
            save_control(control)
            st.rerun()
        st.error("BOT STOPPED")
    st.caption(f"Modo: {'LIVE' if not Config.TESTNET else 'TESTNET'}" 
               if 'Config' in dir() else "Modo: TESTNET")

# ---------------------------------------------------------------------------
# MÉTRICAS PRINCIPALES
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Balance</div><div class="metric-value">${state.get("balance", 0):,.2f}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Equity</div><div class="metric-value">${state.get("equity", 0):,.2f}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">DAPS x</div><div class="metric-value">{state.get("daps_x", 0):.4f}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Equilibrium</div><div class="metric-value">{state.get("equilibrium", 1):.4f}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SEGURIDAD (CIRCUIT BREAKER, STAT GUARD, SAFE MODE)
# ---------------------------------------------------------------------------
st.subheader("🛡 Safety")
col_s1, col_s2, col_s3 = st.columns(3)
breaker_active = state.get("breaker", {}).get("cooldown_active", False)
stat_block = state.get("status") == "STAT_GUARD_BLOCK"
safe_mode = metrics.get("safe_mode", False)
if breaker_active:
    col_s1.error("Circuit Breaker ACTIVO")
else:
    col_s1.success("Circuit Breaker OK")
if stat_block:
    col_s2.warning("Statistical Guard BLOQUEANDO")
else:
    col_s2.success("Statistical Guard OK")
if safe_mode:
    col_s3.info("Safe‑risk activo")
else:
    col_s3.success("Riesgo normal")

# ---------------------------------------------------------------------------
# MÉTRICAS DE RUNTIME
# ---------------------------------------------------------------------------
if metrics:
    st.subheader("📊 Runtime")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ciclos", metrics.get("cycles_completed", 0))
    c2.metric("Señales gen.", metrics.get("signals_generated", 0))
    c3.metric("Filtradas", metrics.get("signals_filtered", 0))
    c4.metric("Avg ciclo (ms)", f"{metrics.get('average_cycle_ms', 0):.0f}")

# ---------------------------------------------------------------------------
# LOGS EN VIVO
# ---------------------------------------------------------------------------
st.subheader("📜 Live Logs")
log_text = "".join(logs) if logs else "No logs yet."
st.text_area("Últimas líneas", log_text, height=220, disabled=True)

# ---------------------------------------------------------------------------
# POSICIONES ABIERTAS
# ---------------------------------------------------------------------------
st.subheader("📌 Posiciones Abiertas")
open_pos = state.get("open_positions", {})
if not open_pos:
    st.info("Sin posiciones abiertas.")
else:
    rows = [{"Symbol": sym, "Direction": p.get("direction"), "Entry": p.get("entry"),
             "Leverage": f"{p.get('leverage', 1):.1f}x", "Size": f"{p.get('size', 0):.4f}",
             "Meta Score": f"{p.get('meta_score', 0):.2f}"} for sym, p in open_pos.items()]
    st.table(pd.DataFrame(rows))

# ---------------------------------------------------------------------------
# HISTORIAL DE TRADES (colapsable)
# ---------------------------------------------------------------------------
with st.expander("📋 Historial de Trades"):
    if trades_df.empty:
        st.info("No hay trades registrados.")
    else:
        st.dataframe(trades_df.sort_values("timestamp", ascending=False).head(40),
                     use_container_width=True)

# ---------------------------------------------------------------------------
# CURVA DE EQUITY
# ---------------------------------------------------------------------------
if not trades_df.empty:
    st.subheader("📈 Equity")
    df_eq = trades_df.sort_values("timestamp")
    df_eq["cum_pnl"] = df_eq["pnl"].cumsum()
    init_balance = state.get("balance", 10000) - df_eq["cum_pnl"].iloc[-1] if len(df_eq) else 10000
    df_eq["equity"] = init_balance + df_eq["cum_pnl"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_eq["timestamp"], y=df_eq["equity"],
                             mode='lines', name='Equity',
                             line=dict(color='#58A6FF', width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0E1117",
                      plot_bgcolor="#0E1117", margin=dict(l=0,r=0,t=10,b=10),
                      height=300)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# PIE DE PÁGINA
# ---------------------------------------------------------------------------
st.caption("Leviathan Control Center v5.2 · Recovery‑First Design · Dashboard desacoplado")
