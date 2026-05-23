import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Leviathan Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #E0E4EA;
    }
    .metric-card {
        background-color: #161B22;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border: 1px solid #30363D;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8B949E;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #58A6FF;
    }
    .warning-banner {
        background-color: #1F2329;
        border-left: 4px solid #D29922;
        padding: 0.8rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH   = os.path.join(BASE_DIR, "runtime", "state.json")
TRADES_PATH  = os.path.join(BASE_DIR, "runtime", "trades.csv")
LOG_PATH     = os.path.join(BASE_DIR, "runtime", "logs", "engine.log")
METRICS_PATH = os.path.join(BASE_DIR, "runtime", "metrics.json")

# ---------------------------------------------------------------------------
# FUNCIONES DE CARGA SEGURA
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

@st.cache_data(ttl=30)
def load_trades():
    if not os.path.exists(TRADES_PATH):
        return pd.DataFrame(columns=["timestamp", "symbol", "side", "entry", "exit", "pnl", "meta_score", "strategy"])
    try:
        df = pd.read_csv(TRADES_PATH)
        for col in ["entry", "exit", "pnl", "meta_score"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=["timestamp", "symbol", "side", "entry", "exit", "pnl", "meta_score", "strategy"])

@st.cache_data(ttl=30)
def load_logs_tail(n=100):
    if not os.path.exists(LOG_PATH):
        return ["(log file not found)"]
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:] if lines else ["(log empty)"]
    except Exception:
        return ["(error reading log)"]

@st.cache_data(ttl=30)
def load_metrics():
    if not os.path.exists(METRICS_PATH):
        return {}
    try:
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

# ---------------------------------------------------------------------------
# AUTO‑REFRESH
# ---------------------------------------------------------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30_000, key="dashboard-refresh")

# ---------------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------------
state   = load_state()
trades_df = load_trades()
logs    = load_logs_tail(100)
metrics = load_metrics()

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.title("🐋 Leviathan Dashboard")

if not state:
    st.markdown('<div class="warning-banner">⚠️ No se encontró <code>runtime/state.json</code>. El motor aún no ha generado estado persistente.</div>', unsafe_allow_html=True)
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Balance</div>
            <div class="metric-value">${state.get('balance', 0):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Equity</div>
            <div class="metric-value">${state.get('equity', 0):,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">DAPS x</div>
            <div class="metric-value">{state.get('daps_x', 0):.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Equilibrium</div>
            <div class="metric-value">{state.get('equilibrium', 1):.4f}</div>
        </div>
        """, unsafe_allow_html=True)

    col5, col6 = st.columns(2)
    with col5:
        st.markdown(f"**Status**: {state.get('status', 'UNKNOWN')}  ")
        st.markdown(f"**Loop count**: {state.get('loop_count', 0)}  ")
        st.markdown(f"**Last execution**: {state.get('last_execution', 'N/A')}  ")
    with col6:
        meta = state.get("meta", {})
        st.markdown(f"**Winrate**: {meta.get('winrate', 0)*100:.1f}%  ")
        st.markdown(f"**Profit Factor**: {meta.get('profit_factor', 0):.2f}  ")
        st.markdown(f"**Max Drawdown**: {meta.get('drawdown', 0)*100:.2f}%  ")

# ---------------------------------------------------------------------------
# SEGURIDAD (CIRCUIT BREAKER / STAT GUARD / SAFE MODE)
# ---------------------------------------------------------------------------
st.header("🛡 Runtime Safety")
col_s1, col_s2, col_s3 = st.columns(3)
if metrics.get("circuit_breaker_active"):
    col_s1.error("Circuit breaker activo")
else:
    col_s1.success("Circuit breaker OK")
if metrics.get("stat_guard_block"):
    col_s2.warning("Statistical Guard bloqueando")
else:
    col_s2.success("Statistical Guard OK")
if metrics.get("safe_mode"):
    col_s3.info("Safe‑risk activo (Sharpe < 1.5)")
else:
    col_s3.success("Riesgo normal")

# ---------------------------------------------------------------------------
# MÉTRICAS DE RUNTIME
# ---------------------------------------------------------------------------
if metrics:
    st.header("📊 Runtime Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclos completados", metrics.get("cycles_completed", 0))
    c2.metric("Señales generadas", metrics.get("signals_generated", 0))
    c3.metric("Posiciones abiertas", metrics.get("open_positions", 0))
    st.caption(f"Avg cycle: {metrics.get('average_cycle_ms', 0):.0f} ms | Uptime: {metrics.get('uptime_seconds', 0)} s")

# ---------------------------------------------------------------------------
# POSICIONES ABIERTAS
# ---------------------------------------------------------------------------
st.header("📌 Posiciones Abiertas")
open_pos = state.get("open_positions", {})
if not open_pos:
    st.info("No hay posiciones abiertas en este momento.")
else:
    rows = []
    for sym, p in open_pos.items():
        rows.append({
            "Symbol": sym,
            "Direction": p.get("direction", "?"),
            "Entry": p.get("entry", 0),
            "Leverage": f"{p.get('leverage', 1):.1f}x",
            "Size": f"{p.get('size', 0):.4f}",
            "Meta Score": f"{p.get('meta_score', 0):.2f}"
        })
    st.table(pd.DataFrame(rows))

# ---------------------------------------------------------------------------
# HISTORIAL DE TRADES
# ---------------------------------------------------------------------------
st.header("📋 Historial de Trades")
if trades_df.empty:
    st.info("No hay trades registrados aún.")
else:
    total_trades = len(trades_df)
    wins = (trades_df["pnl"] > 0).sum()
    losses = (trades_df["pnl"] <= 0).sum()
    winrate = wins / total_trades * 100 if total_trades else 0
    total_pnl = trades_df["pnl"].sum()
    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades_df[trades_df["pnl"] <= 0]["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total trades", total_trades)
    m2.metric("Winrate", f"{winrate:.1f}%")
    m3.metric("P&L Total", f"${total_pnl:,.2f}")
    m4.metric("Profit Factor", f"{profit_factor:.2f}")

    st.dataframe(trades_df.sort_values("timestamp", ascending=False), use_container_width=True)

# ---------------------------------------------------------------------------
# CURVA DE EQUITY
# ---------------------------------------------------------------------------
st.header("📈 Curva de Equity")
if trades_df.empty:
    st.info("Sin datos para mostrar la curva de equity.")
else:
    df_equity = trades_df.sort_values("timestamp")
    df_equity["cumulative_pnl"] = df_equity["pnl"].cumsum()
    initial_balance = state.get("balance", 10000) - df_equity["cumulative_pnl"].iloc[-1] if len(df_equity) else 10000
    df_equity["equity"] = initial_balance + df_equity["cumulative_pnl"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_equity["timestamp"],
        y=df_equity["equity"],
        mode='lines',
        name='Equity',
        line=dict(color='#58A6FF', width=2)
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        margin=dict(l=0, r=0, t=10, b=10),
        xaxis_title="",
        yaxis_title="Equity ($)",
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# LOGS
# ---------------------------------------------------------------------------
st.header("📜 Últimos logs")
with st.expander("Mostrar logs"):
    st.code("".join(logs), language="log")

st.caption("Leviathan Dashboard v5.2 – Solo lectura. El motor se ejecuta de forma independiente.")
