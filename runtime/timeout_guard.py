import time

class TimeoutGuard:
    def __init__(self, max_minutes: int = 330):
        self.start = time.time()
        self.max_seconds = max_minutes * 60

    def triggered(self) -> bool:
        elapsed = time.time() - self.start
        return elapsed >= self.max_seconds

    def remaining_seconds(self) -> float:
        return max(0, self.max_seconds - (time.time() - self.start))
