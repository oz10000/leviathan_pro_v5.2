import json, sys, time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
HEARTBEAT = RUNTIME_DIR / "heartbeat.json"

def main():
    if not HEARTBEAT.exists():
        print("No heartbeat found")
        sys.exit(1)
    with open(HEARTBEAT) as f:
        hb = json.load(f)
    if time.time() - hb["last_cycle"] > 600:
        print("Stale heartbeat")
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()
