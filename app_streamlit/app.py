import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import time

# Configuración de página (debe ser la primera llamada a st)
st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

# ====================== MODO ======================
st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.selectbox("MODE", ["SIMULATOR", "TESTNET", "LIVE"])

# ====================== CARGA DE CREDENCIALES ======================
client = None
if mode != "SIMULATOR":
    try:
        api_key = st.secrets.get("OKX_API_KEY", "")
        secret_key = st.secrets.get("OKX_SECRET_KEY", "")
        passphrase = st.secrets.get("OKX_PASSPHRASE", "")
        if api_key and secret_key:
            from .okx_client import OKXClient
            client = OKXClient(api_key, secret_key, passphrase, testnet=(mode == "TESTNET"))
        else:
            st.sidebar.warning("Missing API credentials in secrets.toml")
    except Exception as e:
        st.sidebar.error(f"Error loading secrets: {e}")

# ====================== CONTROLES ======================
interval = st.sidebar.slider("Execution Interval (s)", 5, 60, 30)

if "running" not in st.session_state:
    st.session_state.running = False

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"):
    st.session_state.running = True
if col2.button("⏸️ STOP"):
    st.session_state.running = False

st.sidebar.write(f"Loop State: {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")

# ====================== AUTO REFRESH ======================
if st.session_state.running:
    st_autorefresh(interval=interval * 1000, key="loop")

# ====================== INICIALIZAR ENGINE BAJO DEMANDA ======================
adapter = None
engine_error = None

if st.session_state.running:
    try:
        from .core_adapter import CoreAdapter
        if "adapter" not in st.session_state:
            st.session_state.adapter = CoreAdapter(mode=mode.lower())
        adapter = st.session_state.adapter
    except ImportError as e:
        engine_error = (
            f"❌ Failed to import Edge Core.\n"
            f"Check that `leviathan_edge_core/` is complete.\n"
            f"Technical: {e}"
        )
        st.error(engine_error)
        st.session_state.running = False
    except Exception as e:
        engine_error = f"❌ Unexpected error: {e}"
        st.error(engine_error)
        st.session_state.running = False

# ====================== OBTENER DATOS ======================
df = pd.DataFrame()
if adapter is not None and engine_error is None:
    if mode == "SIMULATOR":
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
        if client:
            now = time.time()
            if "candles_cache" not in st.session_state:
                st.session_state.candles_cache = {}
            cache = st.session_state.candles_cache
            symbol = "BTC"
            if symbol not in cache or (now - cache[symbol].get("ts", 0)) > 60:
                try:
                    df = client.get_candles(symbol, bar="5m", limit=100)
                    if not df.empty:
                        cache[symbol] = {"df": df, "ts": now}
                except Exception as e:
                    st.warning(f"Failed to fetch candles: {e}")
            else:
                df = cache[symbol]["df"]
        else:
            st.warning("OKX client not initialized. Check credentials.")

# ====================== EJECUTAR CICLO ======================
snapshot = None
if adapter is not None and not df.empty:
    try:
        snapshot = adapter.run_cycle(df)
    except Exception as e:
        st.error(f"Edge Core cycle error: {e}")
elif adapter is not None:
    snapshot = adapter.get_snapshot()

# ====================== DASHBOARD ======================
st.title("🐙 LEVIATHAN EDGE CORE DASHBOARD")
st.markdown(f"**MODE:** {mode} | **STATUS:** {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")

if snapshot:
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
            st.write(f"**Open Position:** {'LONG' if pos.get('dir')==1 else 'SHORT'} "
                     f"Entry: {pos['entry']:.2f} | SL: {pos['sl']:.2f} | TP: {pos['tp']:.2f}")
        else:
            st.write("**Open Position:** NONE")
    st.markdown("---")
    st.write(f"Loops executed: {snapshot['loop_count']} | Last: {snapshot['last_execution']}")
else:
    if not st.session_state.running:
        st.info("Engine not started. Press **PLAY** to initialize the Edge Core.")
    elif engine_error:
        pass
    elif df.empty:
        st.warning("No market data available. Check connection or symbols.")
    else:
        st.info("Waiting for first cycle...")
