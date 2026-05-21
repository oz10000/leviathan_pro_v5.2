import json, time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
HEALTH_FILE = RUNTIME_DIR / "health.json"
HEARTBEAT_FILE = RUNTIME_DIR / "heartbeat.json"

class HealthEngine:
    def __init__(self):
        self.events = []
        self.cycles = 0

    def record_event(self, event):
        self.events.append({"event": event, "timestamp": time.time()})

    def record_cycle(self):
        self.cycles += 1
        with open(HEARTBEAT_FILE, 'w') as f:
            json.dump({"last_cycle": time.time(), "cycles": self.cycles}, f)

    def save(self):
        with open(HEALTH_FILE, 'w') as f:
            json.dump({"events": self.events[-20:], "cycles": self.cycles}, f)
