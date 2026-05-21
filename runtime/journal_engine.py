import json, time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
JOURNAL_DIR = RUNTIME_DIR / "journals"
JOURNAL_DIR.mkdir(exist_ok=True)

class JournalEngine:
    def __init__(self):
        self.file = None

    def start(self, runtime_id):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.file = JOURNAL_DIR / f"journal_{timestamp}_{runtime_id}.jsonl"

    def log_trade(self, event, trade):
        if self.file:
            entry = {"event": event, "time": time.time(), "trade": trade}
            with open(self.file, 'a') as f:
                f.write(json.dumps(entry) + "\n")

    def log_cycle(self, cycle, capital):
        if self.file:
            entry = {"event": "cycle", "cycle": cycle, "capital": capital, "time": time.time()}
            with open(self.file, 'a') as f:
                f.write(json.dumps(entry) + "\n")

    def close(self):
        pass
