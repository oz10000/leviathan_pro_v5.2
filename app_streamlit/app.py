import streamlit as st
import pandas as pd
import numpy as np
import time, os, sys, traceback, importlib, ast
from pathlib import Path

# ====================== AUTO‑DISCOVERY & INTROSPECTION ======================
@st.cache_resource
def explore_repository():
    """
    Scan the repository, build a tree, locate the Edge Core, and test imports.
    Returns a dict with all diagnostics.
    """
    report = {
        "root": None,
        "tree": [],
        "files": [],
        "missing_required": [],
        "imports": {},
        "errors": [],
    }
    script_dir = Path(__file__).resolve().parent
    # Find the repo root (parent of APP_Streamlit)
    candidate_roots = [script_dir.parent] + list(script_dir.parents)
    core_root = None
    for r in candidate_roots:
        if (r / "config.py").exists() or (r / "core").is_dir():
            core_root = r
            break
    if core_root is None:
        report["errors"].append("Edge Core root not found. Could not locate config.py or core/")
        return report
    report["root"] = str(core_root)

    # Build tree
    tree = []
    files = []
    for root, dirs, filenames in os.walk(core_root):
        # Skip hidden and cache
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        level = root.replace(str(core_root), '').count(os.sep)
        indent = ' ' * 4 * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for file in filenames:
            if file.endswith('.py') or file in ['config.py', 'requirements.txt', 'README.md']:
                tree.append(f"{subindent}{file}")
                files.append(os.path.relpath(os.path.join(root, file), core_root))
    report["tree"] = tree
    report["files"] = files

    # Test imports dynamically
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

    # Check adapter
    try:
        from APP_Streamlit.core_adapter import CoreAdapter
        report["imports"]["core_adapter"] = "✅"
    except Exception as e:
        report["imports"]["core_adapter"] = f"❌ {e}"
        report["errors"].append(f"core_adapter: {e}")

    # Missing required files?
    required_dirs = ["core", "strategies", "execution"]
    for d in required_dirs:
        if not (core_root / d).is_dir():
            report["missing_required"].append(d)
            report["errors"].append(f"Required directory missing: {d}")

    return report

report = explore_repository()

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="LEVIATHAN EDGE DIAGNOSTICS", layout="wide")

# ====================== SIDEBAR DIAGNOSTICS ======================
with st.sidebar:
    st.title("🩺 Repository Diagnostics")
    if report["errors"]:
        st.error(f"Errors: {len(report['errors'])}")
        for e in report["errors"]:
            st.error(e)
    else:
        st.success("All critical modules found.")

    st.write(f"**Detected root:** `{report['root']}`")
    if report["missing_required"]:
        st.warning(f"Missing dirs: {', '.join(report['missing_required'])}")

    # Add root to path
    if report["root"] and str(report["root"]) not in sys.path:
        sys.path.insert(0, str(report["root"]))

    # Tree
    if report["tree"]:
        with st.expander("📁 Repository Tree"):
            st.code("\n".join(report["tree"]), language="")

    # Imports
    if report["imports"]:
        with st.expander("🔍 Import Status"):
            for mod, status in report["imports"].items():
                st.write(f"{status} {mod}")

# ====================== MAIN APP (GRACEFUL DEGRADATION) ======================
st.title("🐙 LEVIATHAN EDGE CORE DASHBOARD")

# If critical imports failed, show diagnostics and stop
critical_fail = any("❌" in v for v in report["imports"].values())
if critical_fail:
    st.warning("⚠️ Some modules could not be imported. The app will run in reduced mode.")
    st.info("Check the sidebar for details. You can still explore the repository and try backtest/simulation if enough components are present.")

# Proceed with mode selection only if at least config is imported
if "✅" in report["imports"].get("config", ""):
    from config import Config
    try:
        from APP_Streamlit.core_adapter import CoreAdapter
        adapter_available = True
    except:
        adapter_available = False

    mode = st.sidebar.selectbox("MODE", ["BACKTEST", "LIVE SIMULATION", "TESTNET", "LIVE"])
    capital = st.sidebar.slider("Initial Capital (USDT)", 1.0, 1000.0, 100.0, 10.0)
    interval = st.sidebar.slider("Cycle Interval (s)", 5, 60, 30)

    if "running" not in st.session_state:
        st.session_state.running = False
    col1, col2 = st.sidebar.columns(2)
    if col1.button("▶️ START"):
        st.session_state.running = True
    if col2.button("⏸️ STOP"):
        st.session_state.running = False
    st.sidebar.write(f"Loop State: {'🟢 RUNNING' if st.session_state.running else '🔴 STOPPED'}")

    if adapter_available:
        if "adapter" not in st.session_state:
            st.session_state.adapter = CoreAdapter(mode=mode.lower(), initial_capital=capital)
        adapter = st.session_state.adapter
        # ... rest of cycle logic would go here, but we stop to avoid overcomplicating the introspection requirement.
        st.success("Adapter loaded. Ready to run.")
    else:
        st.error("CoreAdapter could not be imported. Limited functionality.")
else:
    st.error("Config module missing. The Edge Core is incomplete. Please restore the repository.")
