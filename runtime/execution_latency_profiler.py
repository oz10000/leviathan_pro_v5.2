import time
import statistics
from collections import deque

class ExecutionLatencyProfiler:
    def __init__(self, window_size=20):
        self.latencies = deque(maxlen=window_size)
        self.slippages = deque(maxlen=window_size)
        self.fill_rates = deque(maxlen=window_size)

    def record_order(self, send_time, fill_time, requested_price, fill_price):
        latency = (fill_time - send_time) * 1000  # ms
        slippage = abs(fill_price - requested_price) / requested_price * 100  # %
        self.latencies.append(latency)
        self.slippages.append(slippage)
        self.fill_rates.append(1.0)  # asumimos llenado total

    def stats(self):
        if not self.latencies:
            return {'latency_ms': 0, 'slippage_pct': 0, 'jitter_ms': 0}
        return {
            'latency_ms': round(statistics.mean(self.latencies), 1),
            'slippage_pct': round(statistics.mean(self.slippages), 4),
            'jitter_ms': round(statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0.0, 1)
        }
