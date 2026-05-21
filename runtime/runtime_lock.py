import os, time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
LOCK_FILE = RUNTIME_DIR / "runtime.lock"

class RuntimeLock:
    def acquire(self):
        if LOCK_FILE.exists():
            pid = LOCK_FILE.read_text().strip()
            # Check if process is alive (only works on same OS)
            try:
                os.kill(int(pid), 0)
                return False  # still running
            except (OSError, ValueError):
                # stale lock
                LOCK_FILE.unlink(missing_ok=True)
        LOCK_FILE.write_text(str(os.getpid()))
        return True

    def release(self):
        if LOCK_FILE.exists():
            LOCK_FILE.unlink(missing_ok=True)
