import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'leviathan_edge_core'))
from core_adapter import CoreAdapter
from okx_client import OKXClient

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

# ---------- CONFIGURACIÓN DE MODO ----------
st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.selectbox("MODE", ["SIMULATOR", "TESTNET", "LIVE"])

# Cargar credenciales si no es simulador
if mode != "SIMULATOR":
    api_key = st.secrets.get("OKX_API_KEY", "")
    secret_key = st.secrets.get("OKX_SECRET_KEY", "")
    passphrase = st.secrets.get("OKX_PASSPHRASE", "")
    testnet = mode == "TESTNET"
    client = OKXClient(api_key, secret_key, passphrase, testnet=testnet)
else:
    client = None

# ---------- INICIALIZAR ADAPTER ----------
if "adapter" not in st.session_state:
    st.session_state.adapter = CoreAdapter(mode=mode.lower())

adapter = st.session_state.adapter

# Cambiar modo si el usuario lo modifica
if adapter.state["mode"] != mode.lower():
    adapter.state["mode"] = mode.lower()

# ---------- CONTROLES ----------
interval = st.sidebar.slider("Execution Interval (s)", 5, 60, 30)

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"):
    st.session_state.running = True
if col2.button("⏸️ STOP"):
    st.session_state.running = False

if "running" not in st.session_state:
    st.session_state.running = False

st.sidebar.write(f"Loop State: {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")

# ---------- AUTO REFRESH ----------
if st.session_state.running:
    st_autorefresh(interval=interval * 1000, key="loop")

# ---------- OBTENER DATOS ----------
if mode == "SIMULATOR":
    # Generar datos sintéticos o usar datos públicos de OKX sin autenticación
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
    df = pd.DataFrame({
        'ts': dates,
        'open': 50000 + np.cumsum(np.random.randn(100)*20),
        'high': 0, 'low': 0, 'close': 0, 'volume': 1000
    })
    df['high'] = df['open'] + np.abs(np.random.randn(100)*10)
    df['low'] = df['open'] - np.abs(np.random.randn(100)*10)
    df['close'] = df['open'] + np.random.randn(100)*2
else:
    # Obtener datos reales de OKX
    if client:
        df = client.get_candles("BTC", bar="5m", limit=100)
    else:
        df = pd.DataFrame()

# ---------- EJECUTAR CICLO ----------
if st.session_state.running and not df.empty:
    snapshot = adapter.run_cycle(df)
else:
    snapshot = adapter.get_snapshot()

# ---------- DASHBOARD ----------
st.title("🐙 LEVIATHAN EDGE CORE DASHBOARD")
st.markdown(f"**MODE:** {mode} | **STATUS:** {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")

col1, col2, col3 = st.columns(3)
col1.metric("Balance", f"${snapshot['balance']:.2f} USDT")
col2.metric("Equity", f"${snapshot['equity']:.2f} USDT")
col3.metric("PnL", f"{snapshot['pnl']:+.2f} USDT")

st.markdown("---")
col_sig, col_pos = st.columns(2)
with col_sig:
    st.write(f"**Signal:** {snapshot['signal'] or 'NONE'}")
with col_pos:
    if snapshot['position']:
        pos = snapshot['position']
        st.write(f"**Open Position:** {pos.get('dir','?')==1 and 'LONG' or 'SHORT'} "
                 f"Entry: {pos['entry']:.2f} | SL: {pos['sl']:.2f} | TP: {pos['tp']:.2f}")
    else:
        st.write("**Open Position:** NONE")

st.markdown("---")
st.write(f"Loops executed: {snapshot['loop_count']} | Last: {snapshot['last_execution']}")
