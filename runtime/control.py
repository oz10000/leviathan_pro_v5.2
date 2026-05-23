import json
import os
from datetime import datetime, timezone

CONTROL_PATH = os.path.join(os.path.dirname(__file__), "runtime_control.json")

DEFAULT_CONTROL = {
    "bot_enabled": True,
    "allow_new_entries": True,
    "shutdown_requested": False,
    "last_modified": "",
    "modified_by": "system"
}

def load_control():
    """Carga el estado de control. Si no existe, crea uno por defecto."""
    if not os.path.exists(CONTROL_PATH):
        return dict(DEFAULT_CONTROL)
    try:
        with open(CONTROL_PATH, "r") as f:
            control = json.load(f)
        # Rellenar campos faltantes
        for k, v in DEFAULT_CONTROL.items():
            if k not in control:
                control[k] = v
        return control
    except (json.JSONDecodeError, IOError):
        return dict(DEFAULT_CONTROL)

def save_control(control: dict):
    """Guarda el estado de control de forma atómica."""
    control["last_modified"] = datetime.now(timezone.utc).isoformat()
    tmp = CONTROL_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(control, f, indent=2)
    os.replace(tmp, CONTROL_PATH)
