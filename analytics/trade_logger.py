import csv
import os

class TradeLogger:
    def __init__(self, filename="trades.csv"):
        self.filename = filename
        if not os.path.exists(filename):
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp","symbol","side","entry","exit","pnl","exit_reason"])

    def log(self, trade):
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trade.get("timestamp"),
                trade.get("symbol"),
                trade.get("side"),
                trade.get("entry_price"),
                trade.get("exit_price"),
                trade.get("pnl"),
                trade.get("exit_reason")
            ])
