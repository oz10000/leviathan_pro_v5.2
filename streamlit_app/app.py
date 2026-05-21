import streamlit as st
import streamlit.components.v1 as components
import json, os
from pathlib import Path

st.set_page_config(page_title="LEVIATHAN · DARDO", page_icon="⚡", layout="wide")

# Ocultar decoración de Streamlit para inmersión total
hide_streamlit_style = """
<style>
#MainMenu, footer, header, .stDeployButton { visibility: hidden; }
.stApp { background: #050508; margin: 0; padding: 0; }
.stApp > div { padding: 0; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Cargar datos reales del motor
RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
state = {}
if STATE_FILE.exists():
    with open(STATE_FILE) as f:
        state = json.load(f)

# Inyectar estado como JSON dentro del HTML (será leído por el JS)
state_json = json.dumps(state, ensure_ascii=False)

# HTML del sistema vivo (incrustado para evitar CORS)
with open(Path(__file__).parent / "dardo.html", "r", encoding="utf-8") as f:
    html = f.read()

# Insertar los datos reales antes de cerrar </body>
html = html.replace("</body>", f"<script>window.__LEVIATHAN_STATE__ = {state_json};</script></body>")

components.html(html, height=1000, scrolling=False)
