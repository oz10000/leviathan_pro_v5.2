import json, os

STATE_FILE = "runtime/runtime_state.json"

class StateManager:
    @staticmethod
    def load():
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {"positions": {}, "open_orders": [], "last_signal": None, "cycle_count": 0}

    @staticmethod
    def save(state):
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    @staticmethod
    def reconcile_with_exchange(connector, state):
        positions = connector.get_positions()
        state["positions"] = {p.get("symbol", ""): p for p in positions}
        return state
