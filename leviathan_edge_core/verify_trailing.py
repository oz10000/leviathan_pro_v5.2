from execution.exit_hybrid import HybridExit

def test_trailing():
    pos = {
        "dir": 1, "entry": 100, "atr": 2, "leverage": 5,
        "be_active": False, "trail_active": False,
        "sl": 98.6, "trail_sl": 98.6, "entry_time": 0
    }
    exit, reason, price, updated = HybridExit.should_exit(pos, 105, 1000)
    if updated:
        pos = updated
    # After moving above BE threshold, BE should activate
    exit2, reason2, price2, updated2 = HybridExit.should_exit(pos, 106, 1000)
    print("Trailing test passed, exit:", exit2, reason2)

if __name__ == "__main__":
    test_trailing()
