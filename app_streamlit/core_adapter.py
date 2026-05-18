import sys, os, time
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque

from config import Config
from core.feature_engine import compute_features
from strategies.expansion_strategy import ExpansionStrategy
from strategies.pullback_strategy import PullbackStrategy
from strategies.reacceleration_strategy import ReaccelerationStrategy
from strategies.depression_breakout import DepressionBreakoutStrategy
from execution.exit_hybrid import HybridExit

class CoreAdapter:
    def __init__(self, mode="simulator", initial_capital=None):
        self.mode = mode
        self.strategies = [
            ExpansionStrategy(),
            PullbackStrategy(),
            ReaccelerationStrategy(),
            DepressionBreakoutStrategy()
        ]
        capital = initial_capital if initial_capital is not None else Config.INITIAL_CAPITAL
        self.state = {
            "balance": capital,
            "equity": capital,
            "pnl": 0.0,
            "position": None,
            "signal": None,
            "loop_count": 0,
            "last_execution": None,
            "mode": mode,
            "equity_history": [capital],
            "oscillators": {},
            "backtest_metrics": None,
            "live_metrics": None,
            "trades": []
        }
        self._prev_balance = capital

    def run_cycle(self, df_5m, df_15m=None, df_1h=None, leverage=None):
        if df_5m is None or len(df_5m) < 50:
            self.state["signal"] = None
            return self.get_snapshot()

        df_5m = compute_features(df_5m)
        if df_15m is not None and len(df_15m) >= 20:
            df_15m = compute_features(df_15m)
        else:
            df_15m = df_5m.copy()

        row_5m = df_5m.iloc[-1]
        row_15m = df_15m.iloc[-1]

        direction = "LONG" if row_5m["ema20"] > row_5m["ema50"] else "SHORT"

        best_score = 0
        best_strategy = None
        for strat in self.strategies:
            score = strat.compute_score(df_5m, df_15m, row_5m, row_15m, direction)
            if score > best_score:
                best_score = score
                best_strategy = strat.name

        if best_score >= Config.SCORE_THRESHOLD and self.state["position"] is None:
            self.state["signal"] = direction
            atr = row_5m["atr"]
            entry = row_5m["close"]
            lev = leverage if leverage else Config.SAFE_LEVERAGE_MIN
            sl = entry - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr
            tp = entry + (1 if direction == "LONG" else -1) * Config.TP_ATR * atr
            self.state["position"] = {
                "symbol": "BTC-USDT-SWAP",
                "dir": 1 if direction == "LONG" else -1,
                "entry": entry,
                "atr": atr,
                "size": 0.01,
                "leverage": lev,
                "strategy": best_strategy,
                "entry_time": time.time(),
                "be_active": False,
                "trail_active": False,
                "sl": sl,
                "trail_sl": sl,
                "tp": tp
            }
        else:
            self.state["signal"] = None

        if self.state["position"] is not None:
            pos = self.state["position"]
            price = row_5m["close"]
            exit_sig, reason, exit_price, updated = HybridExit.should_exit(pos, price, time.time())
            if updated:
                self.state["position"] = updated
            if exit_sig:
                d = pos["dir"]
                pnl = (exit_price - pos["entry"]) * d * pos["size"] * pos["leverage"] / pos["entry"]
                self.state["balance"] += pnl
                self.state["pnl"] += pnl
                self.state["equity"] = self.state["balance"]
                self.state["trades"].append({"pnl": pnl, "time": datetime.now(), "reason": reason})
                self.state["position"] = None

        self.state["equity_history"].append(self.state["balance"])
        self.state["loop_count"] += 1
        self.state["last_execution"] = datetime.now().strftime("%H:%M:%S")

        # Oscillators (simple: equity volatility)
        if len(self.state["equity_history"]) > 10:
            rets = np.diff(self.state["equity_history"][-20:]) / self.state["equity_history"][-20:-1]
            self.state["oscillators"]["Volatility"] = np.std(rets) * 100 if len(rets)>0 else 0

        return self.get_snapshot()

    def run_backtest(self, df_5m, leverage=None):
        self.state["balance"] = Config.INITIAL_CAPITAL
        self.state["equity"] = Config.INITIAL_CAPITAL
        self.state["pnl"] = 0.0
        self.state["position"] = None
        self.state["equity_history"] = [Config.INITIAL_CAPITAL]
        self.state["trades"] = []

        for i in range(50, len(df_5m)):
            window = df_5m.iloc[:i+1]
            self.run_cycle(window, leverage=leverage)

        eq = np.array(self.state["equity_history"])
        rets = np.diff(eq) / eq[:-1]
        sharpe = np.mean(rets) / np.std(rets) * np.sqrt(365*24) if len(rets) > 1 else 0
        maxdd = (np.maximum.accumulate(eq) - eq).max() / np.maximum.accumulate(eq).max()
        winrate = np.mean([t["pnl"]>0 for t in self.state["trades"]]) if self.state["trades"] else 0
        profit_factor = (sum(t["pnl"] for t in self.state["trades"] if t["pnl"]>0) / abs(sum(t["pnl"] for t in self.state["trades"] if t["pnl"]<0))) if self.state["trades"] else 0
        self.state["backtest_metrics"] = {
            "sharpe": sharpe,
            "maxdd": maxdd,
            "winrate": winrate,
            "profit_factor": profit_factor
        }
        return self.state["backtest_metrics"]

    def get_snapshot(self):
        return {
            "mode": self.state["mode"],
            "balance": self.state["balance"],
            "equity": self.state["equity"],
            "pnl": self.state["pnl"],
            "position": self.state["position"],
            "signal": self.state["signal"],
            "loop_count": self.state["loop_count"],
            "last_execution": self.state["last_execution"] or "--:--:--"
        }
