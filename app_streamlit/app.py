import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import time, os, sys, traceback, importlib, requests
from pathlib import Path

# ====================== AUTO‑DISCOVERY & INTROSPECTION ======================
@st.cache_resource
def explore_repository():
    report = {
        "root": None,
        "tree": [],
        "files": [],
        "missing_required": [],
        "imports": {},
        "errors": [],
    }
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    core_root = None
    for candidate in [repo_root / "leviathan_edge_core", repo_root]:
        if (candidate / "config.py").exists() and (candidate / "core").is_dir():
            core_root = candidate
            break
    if core_root is None:
        for r in [script_dir] + list(script_dir.parents):
            if (r / "config.py").exists() and (r / "core").is_dir():
                core_root = r
                break
    if core_root is None:
        report["errors"].append(
            "Edge Core root not found. Expected a folder with config.py and core/ "
            "parallel to streamlit_app/ (e.g. leviathan_edge_core/)."
        )
        return report

    report["root"] = str(core_root)

    tree = []
    files = []
    base = core_root
    for root, dirs, filenames in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        level = root.replace(str(base), '').count(os.sep)
        indent = ' ' * 4 * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for file in filenames:
            if file.endswith('.py') or file == 'config.py':
                tree.append(f"{subindent}{file}")
                files.append(os.path.relpath(os.path.join(root, file), base))
    report["tree"] = tree
    report["files"] = files

    if str(core_root) not in sys.path:
        sys.path.insert(0, str(core_root))

    import_status = {}
    critical_pairs = [
        ("config", "Config"),
        ("core.feature_engine", "compute_features"),
        ("strategies.expansion_strategy", "ExpansionStrategy"),
        ("strategies.pullback_strategy", "PullbackStrategy"),
        ("strategies.reacceleration_strategy", "ReaccelerationStrategy"),
        ("strategies.depression_breakout", "DepressionBreakoutStrategy"),
        ("execution.exit_hybrid", "HybridExit"),
    ]
    for mod_name, attr in critical_pairs:
        try:
            mod = importlib.import_module(mod_name)
            getattr(mod, attr)
            import_status[mod_name] = "✅"
        except Exception as e:
            import_status[mod_name] = f"❌ {e}"
            report["errors"].append(f"Import {mod_name}: {e}")
    report["imports"] = import_status

    try:
        import core_adapter
        import_status["core_adapter"] = "✅"
    except Exception as e:
        import_status["core_adapter"] = f"❌ {e}"
        report["errors"].append(f"core_adapter: {e}")

    try:
        import okx_client
        import_status["okx_client"] = "✅"
    except Exception as e:
        import_status["okx_client"] = f"❌ {e}"
        report["errors"].append(f"okx_client: {e}")

    required_dirs = ["core", "strategies", "execution"]
    for d in required_dirs:
        if not (core_root / d).is_dir():
            report["missing_required"].append(d)
            report["errors"].append(f"Required directory missing: {d}")

    return report


report = explore_repository()

st.set_page_config(page_title="LEVIATHAN EDGE", layout="wide")

# ====================== SIDEBAR DIAGNOSTICS ======================
with st.sidebar:
    st.title("🩺 System Diagnostics")
    if report["errors"]:
        st.error(f"Issues: {len(report['errors'])}")
        for e in report["errors"]:
            st.error(e)
    else:
        st.success("All critical modules found.")

    st.write(f"**Edge Core root:** `{report['root']}`")
    if report["missing_required"]:
        st.warning(f"Missing dirs: {', '.join(report['missing_required'])}")

    if report["tree"]:
        with st.expander("📁 Edge Core Tree"):
            st.code("\n".join(report["tree"]), language="")

    if report["imports"]:
        with st.expander("🔍 Import Status"):
            for mod, status in report["imports"].items():
                st.write(f"{status} {mod}")

critical_fail = any("❌" in v for v in report["imports"].values())
if critical_fail:
    st.warning("⚠️ Some modules could not be imported. Limited functionality.")

st.title("🐙 LEVIATHAN EDGE CORE DASHBOARD")

# ====================== MAIN APP (if possible) ======================
if "❌" not in report["imports"].get("config", "❌") and "❌" not in report["imports"].get("core_adapter", "❌"):
    from config import Config
    from core_adapter import CoreAdapter
    if "❌" not in report["imports"].get("okx_client", "❌"):
        from okx_client import OKXClient
    else:
        OKXClient = None

    mode = st.sidebar.selectbox("MODE", ["BACKTEST", "LIVE SIMULATION", "TESTNET", "LIVE"])
    capital = st.sidebar.slider("Initial Capital (USDT)", 1.0, 1000.0, 100.0, 10.0)
    leverage_mode = st.sidebar.radio("Leverage", ["Auto (Edge Safe)", "Manual"], index=0)
    manual_leverage = 5
    if leverage_mode == "Manual":
        manual_leverage = st.sidebar.slider("Leverage", 1, 8, 5)

    client = None
    if mode in ("TESTNET", "LIVE") and OKXClient:
        try:
            api_key = st.secrets.get("OKX_API_KEY", "")
            secret_key = st.secrets.get("OKX_SECRET_KEY", "")
            passphrase = st.secrets.get("OKX_PASSPHRASE", "")
            if api_key and secret_key:
                client = OKXClient(api_key, secret_key, passphrase, testnet=(mode == "TESTNET"))
            else:
                st.sidebar.warning("Missing API credentials in secrets.toml")
        except Exception as e:
            st.sidebar.error(f"Secrets error: {e}")

    interval = st.sidebar.slider("Cycle Interval (s)", 5, 60, 30)
    if "running" not in st.session_state:
        st.session_state.running = False
    col1, col2 = st.sidebar.columns(2)
    if col1.button("▶️ START"):
        st.session_state.running = True
    if col2.button("⏸️ STOP"):
        st.session_state.running = False
    st.sidebar.write(f"Loop State: {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")
    if st.session_state.running:
        st_autorefresh(interval=interval * 1000, key="loop")

    if "adapter" not in st.session_state or st.session_state.get("last_mode") != mode:
        st.session_state.adapter = CoreAdapter(mode=mode.lower(), initial_capital=capital)
        st.session_state.last_mode = mode
    adapter = st.session_state.adapter

    # ====================== ROBUST DATA FETCH ======================
    @st.cache_data(ttl=120, show_spinner="Fetching market data...")
    def download_public_candles(symbol, bar, limit):
        """Safe public candle download with fallback."""
        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT-SWAP&bar={bar}&limit={limit}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != "0":
                raise ValueError(f"OKX API error: {payload.get('msg','')}")
            raw = payload["data"]
            if not raw or not isinstance(raw, list):
                return pd.DataFrame()
            # OKX returns reverse chronological; reverse to chronological
            raw = raw[::-1]
            df = pd.DataFrame(raw, columns=["ts","open","high","low","close","vol","volCcy"])
            for col in ["open","high","low","close","vol"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
            df = df.dropna().reset_index(drop=True)
            return df
        except Exception as e:
            st.error(f"Data download error for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_data(symbol="BTC", bar="5m", limit=100):
        if mode in ("TESTNET", "LIVE") and client:
            try:
                df = client.get_candles(symbol, bar=bar, limit=limit)
                return df if not df.empty else pd.DataFrame()
            except Exception as e:
                st.warning(f"Candle fetch error: {e}")
                return pd.DataFrame()
        elif mode == "LIVE SIMULATION":
            df = download_public_candles(symbol, bar, limit)
            if df.empty and symbol == "BTC":
                # fallback to ETH
                st.info("BTC data unavailable, trying ETH...")
                df = download_public_candles("ETH", bar, limit)
            return df
        elif mode == "BACKTEST":
            # Use a larger limit for backtest and cache it
            if "hist_data" not in st.session_state:
                with st.spinner("Downloading historical data (this may take a moment)..."):
                    df = download_public_candles(symbol, bar, 300)
                    if not df.empty:
                        st.session_state.hist_data = df
                        st.success(f"Loaded {len(df)} candles.")
                        # Run backtest automatically
                        adapter.run_backtest(df, leverage=manual_leverage if leverage_mode=="Manual" else None)
                    else:
                        st.error("Failed to load historical data. Check your connection or try a different symbol.")
            return st.session_state.get("hist_data", pd.DataFrame()).copy()
        else:
            # Fallback simulator
            dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
            df = pd.DataFrame({
                'ts': dates,
                'open': 50000 + np.cumsum(np.random.randn(100)*20),
                'high': 0, 'low': 0, 'close': 0, 'volume': 1000
            })
            df['high'] = df['open'] + np.abs(np.random.randn(100)*10)
            df['low'] = df['open'] - np.abs(np.random.randn(100)*10)
            df['close'] = df['open'] + np.random.randn(100)*2
            return df

    # Run cycle
    df = pd.DataFrame()
    if st.session_state.running or mode == "BACKTEST":
        df = fetch_data()

    snapshot = None
    if not df.empty:
        try:
            snapshot = adapter.run_cycle(df, leverage=manual_leverage if leverage_mode=="Manual" else None)
        except Exception as e:
            st.error(f"❌ Cycle error:\n```\n{traceback.format_exc()}\n```")
    else:
        snapshot = adapter.get_snapshot()

    # Dashboard (identical to previous)
    if snapshot:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Balance", f"${snapshot['balance']:.2f}")
        col2.metric("Equity", f"${snapshot['equity']:.2f}")
        col3.metric("PnL", f"{snapshot['pnl']:+.2f}")
        col4.metric("Loops", snapshot['loop_count'])

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

        if adapter.state.get("equity_history"):
            st.subheader("Equity Curve")
            st.line_chart(adapter.state["equity_history"])

        if adapter.state.get("oscillators"):
            st.subheader("Live Oscillators")
            osc = adapter.state["oscillators"]
            cols = st.columns(len(osc))
            for i, (name, val) in enumerate(osc.items()):
                cols[i].metric(name, f"{val:.2f}")

        if mode == "BACKTEST" and adapter.state.get("backtest_metrics"):
            st.subheader("Backtest Results")
            bm = adapter.state["backtest_metrics"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Sharpe", f"{bm.get('sharpe', 0):.2f}")
            col2.metric("Max DD", f"{bm.get('maxdd', 0):.2%}")
            col3.metric("Win Rate", f"{bm.get('winrate', 0):.1%}")
            col4.metric("Profit Factor", f"{bm.get('profit_factor', 0):.2f}")

        if adapter.state.get("backtest_metrics") and adapter.state.get("live_metrics"):
            st.subheader("Live vs Backtest")
            live_m = adapter.state["live_metrics"]
            back_m = adapter.state["backtest_metrics"]
            comp_df = pd.DataFrame({
                "Metric": ["Sharpe","Win Rate","Max DD","Profit Factor"],
                "Backtest": [back_m.get('sharpe',0), back_m.get('winrate',0), back_m.get('maxdd',0), back_m.get('profit_factor',0)],
                "Live": [live_m.get('sharpe',0), live_m.get('winrate',0), live_m.get('maxdd',0), live_m.get('profit_factor',0)]
            })
            st.dataframe(comp_df)
    else:
        if not st.session_state.running and mode != "BACKTEST":
            st.info("Press **START** to begin.")
        elif df.empty:
            st.warning("No market data. Check connection or symbols.")
else:
    st.warning("Essential modules missing. Trading engine cannot start.")
