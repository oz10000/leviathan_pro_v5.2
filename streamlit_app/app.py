import streamlit as st
import json, os, time, glob
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="LEVIATHAN LIVE", page_icon="🟩", layout="wide")

# Estilo terminal hacker
st.markdown("""
<style>
body { background-color: #000000; color: #00ff66; font-family: 'Courier New', monospace; }
.stApp { background-color: #000000; }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div { color: #00ff66 !important; }
.st-bq, .st-cb, .st-at, .st-af, .st-ah, .st-ai, .st-aj, .st-ak { color: #00ff66 !important; }
.streamlit-expanderHeader { color: #00ff66 !important; }
.live-dot { display: inline-block; width: 12px; height: 12px; background-color: #00ff66; border-radius: 0; margin-right: 8px; animation: blink 1s infinite; }
.live-dot.dead { background-color: #555; animation: none; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }
</style>
""", unsafe_allow_html=True)

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
ERRORS_FILE = RUNTIME_DIR / "errors.json"
LOGS_DIR = RUNTIME_DIR / "logs"
CURRENT_LOG = LOGS_DIR / "engine.log"

# Auto-refresh cada 5 segundos
st_autorefresh(interval=5000, key="dashboard_refresh")

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

# ────────────── HEADER VIVO ──────────────
state = load_json(STATE_FILE)
running = state.get("running", False)
mode = state.get("mode", "testnet").upper()
loop_count = state.get("loop_count", 0)
last_exec = state.get("last_execution", "--")
current_action = state.get("current_action", "idle")

col1, col2 = st.columns([1, 4])
with col1:
    if running:
        st.markdown('<div class="live-dot"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="live-dot dead"></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f"**MODE:** {mode} | **STATUS:** {'SCANNING' if running else 'STOPPED'} | **CYCLE:** {loop_count} | **LAST HB:** {last_exec}")

# ────────────── ACCIÓN ACTUAL ──────────────
st.markdown(f"**CURRENT ACTION:** → {current_action}")

# ────────────── TOP SIGNAL ──────────────
top = state.get("top_scan_results", [])
if top:
    best = top[0]
    st.markdown(f"**BEST SIGNAL:** {best.get('symbol','--')} {best.get('trend','--')} Score: {best.get('score',0):.2f}")
else:
    st.markdown("**BEST SIGNAL:** --")

# ────────────── POSICIONES ABIERTAS ──────────────
pos = state.get("position")
if pos:
    pnl = state.get("pnl", 0)
    st.markdown(f"**POSITIONS:** {pos.get('symbol','')} {'LONG' if pos.get('dir')==1 else 'SHORT'} PnL: {pnl:+.2f}")
else:
    st.markdown("**POSITIONS:** --")

# ────────────── ÚLTIMO ERROR ──────────────
errors = load_json(ERRORS_FILE)
if errors:
    st.markdown(f"**LAST ERROR:** {errors.get('message','')} (recovered)")
else:
    st.markdown("**LAST ERROR:** NO ERRORS")

# ────────────── LOGS VIVOS ──────────────
st.markdown("---")
st.markdown("### LIVE LOGS")
if CURRENT_LOG.exists():
    with open(CURRENT_LOG, "r") as f:
        lines = f.readlines()
    # últimos 30 líneas
    st.code("".join(lines[-30:]), language="")
else:
    st.info("No log file yet.")

# ────────────── HISTORIAL POR HORA ──────────────
st.markdown("### LOG HISTORY")
log_files = sorted(glob.glob(str(LOGS_DIR / "engine*.log*")), reverse=True)
log_options = ["current"] + [os.path.basename(f) for f in log_files if os.path.basename(f) != "engine.log"]
selected_log = st.selectbox("Select hour", log_options, index=0)
if selected_log != "current":
    log_path = LOGS_DIR / selected_log
    if log_path.exists():
        with open(log_path) as f:
            lines = f.readlines()
        st.code("".join(lines[-50:]), language="")
