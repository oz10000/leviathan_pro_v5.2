import json
import os
import time
from datetime import datetime, timezone

METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics.json")


def load_metrics():
    if not os.path.exists(METRICS_PATH):
        return {
            "uptime_seconds": 0,
            "average_cycle_ms": 0,
            "api_errors": 0,
            "rate_limit_hits": 0,
            "cycles_completed": 0,
            "signals_generated": 0,
            "signals_filtered": 0,
            "open_positions": 0,
            "last_heartbeat": "",
            "circuit_breaker_active": False,
            "stat_guard_block": False,
            "safe_mode": False
        }
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


def save_metrics(metrics: dict):
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)


class RuntimeMetrics:
    """
    Colecta y persiste métricas operativas del runtime.
    """

    def __init__(self):
        self.metrics = load_metrics()
        self.start_time = time.time()
        self.last_cycle_start = None

    def start_cycle(self):
        self.last_cycle_start = time.time()

    def end_cycle(self,
                  signals_generated=0,
                  signals_filtered=0,
                  open_positions=0,
                  api_errors=0,
                  rate_limit_hits=0,
                  circuit_breaker_active=False,
                  stat_guard_block=False,
                  safe_mode=False):
        now = time.time()
        if self.last_cycle_start:
            cycle_ms = (now - self.last_cycle_start) * 1000
            prev_avg = self.metrics["average_cycle_ms"]
            prev_cycles = self.metrics["cycles_completed"]
            if prev_cycles > 0:
                self.metrics["average_cycle_ms"] = (
                    prev_avg * prev_cycles + cycle_ms
                ) / (prev_cycles + 1)
            else:
                self.metrics["average_cycle_ms"] = cycle_ms

        self.metrics["cycles_completed"] += 1
        self.metrics["signals_generated"] += signals_generated
        self.metrics["signals_filtered"] += signals_filtered
        self.metrics["open_positions"] = open_positions
        self.metrics["api_errors"] += api_errors
        self.metrics["rate_limit_hits"] += rate_limit_hits
        self.metrics["uptime_seconds"] = int(now - self.start_time)
        self.metrics["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        self.metrics["circuit_breaker_active"] = circuit_breaker_active
        self.metrics["stat_guard_block"] = stat_guard_block
        self.metrics["safe_mode"] = safe_mode

        save_metrics(self.metrics)
