import time
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


class BacktestEngine:
    def __init__(self, adapter, symbols=None, days=30, bar="5m"):
        self.adapter = adapter
        self.symbols = symbols or adapter.symbols[:20]
        self.days = days
        self.bar = bar
        self.max_candles = min(days * 288, 300)
        self.data = {}
        self.timeline = []
        self.results = None

    def download_all(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.adapter._download_public_candles,
                                sym, self.bar, self.max_candles): sym
                for sym in self.symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                df = future.result()
                if not df.empty:
                    self.data[sym] = df
        self._align_timestamps()

    def _align_timestamps(self):
        all_ts = set()
        for df in self.data.values():
            all_ts.update(df["ts"].values)
        self.timeline = sorted(all_ts)

    def run(self):
        print(f"Backtesting {len(self.symbols)} symbols over {len(self.timeline)} candles...")
        start_time = time.time()

        # Resetear estado del adaptador de forma segura
        state = self.adapter.state
        state["balance"] = 100.0
        state["equity"] = 100.0
        state["pnl"] = 0.0
        state["position"] = None
        state["equity_history"] = [100.0]
        state["trades"] = []

        for ts in self.timeline:
            market_snapshot = {}
            for sym, df in self.data.items():
                window = df[df["ts"] <= ts]
                if len(window) < 50:
                    continue
                market_snapshot[sym] = window.copy()
            if not market_snapshot:
                continue

            # 1. Evaluar señales
            best_signal = None
            best_symbol = None
            for sym, df in market_snapshot.items():
                signal = self.adapter.evaluate_signal(df)
                if signal is not None:
                    signal["symbol"] = sym
                    if best_signal is None or signal["meta"] > best_signal["meta"]:
                        best_signal = signal
                        best_symbol = sym

            # 2. Abrir posición si no hay una
            if best_signal is not None and state.get("position") is None:
                sl = best_signal.get("sl")
                tp = best_signal.get("tp")
                if sl is None:
                    sl = best_signal["entry"] - (1 if best_signal["direction"] == "LONG" else -1) * 0.7 * best_signal["atr"]
                if tp is None:
                    tp = best_signal["entry"] + (1 if best_signal["direction"] == "LONG" else -1) * 2.5 * best_signal["atr"]

                state["position"] = {
                    "symbol": best_symbol,
                    "dir": 1 if best_signal["direction"] == "LONG" else -1,
                    "entry": best_signal["entry"],
                    "atr": best_signal["atr"],
                    "size": 0.01,
                    "leverage": best_signal.get("leverage", 5),
                    "strategy": best_signal.get("strategy", ""),
                    "entry_time": time.time(),
                    "be_active": False,
                    "trail_active": False,
                    "sl": sl,
                    "trail_sl": sl,
                    "tp": tp,
                    "atr_pct_entry": best_signal["atr"] / best_signal["entry"]
                }

            # 3. Gestionar posición abierta
            pos = state.get("position")
            if pos is not None:
                sym = pos.get("symbol")
                if sym is None or sym == "":
                    state["position"] = None
                    continue

                df = market_snapshot.get(sym)
                if df is not None and len(df) > 0:
                    price = df["close"].iloc[-1]

                    # Asegurar claves mínimas en pos
                    pos.setdefault("sl", pos["entry"] - (1 if pos.get("dir", 1) == 1 else -1) * 0.7 * pos["atr"])
                    pos.setdefault("trail_sl", pos["sl"])
                    pos.setdefault("tp", pos["entry"] + (1 if pos.get("dir", 1) == 1 else -1) * 2.5 * pos["atr"])
                    pos.setdefault("be_active", False)
                    pos.setdefault("trail_active", False)
                    pos.setdefault("entry_time", time.time())
                    pos.setdefault("leverage", 5)
                    pos.setdefault("atr_pct_entry", pos["atr"] / pos["entry"])
                    pos.setdefault("size", 0.01)

                    from execution.exit_hybrid import HybridExit
                    exit_sig, reason, exit_price, updated = HybridExit.should_exit(pos, price, time.time())
                    if updated:
                        state["position"] = updated
                    if exit_sig:
                        d = pos.get("dir", 1)
                        pnl = ((exit_price - pos["entry"]) * d * pos["size"] * pos.get("leverage", 5) /
                               pos["entry"])
                        fee = abs(exit_price - pos["entry"]) * pos["size"] * self.adapter.commission
                        slip = pos["entry"] * pos["size"] * self.adapter.slippage
                        pnl -= (fee + slip)
                        state["balance"] += pnl
                        state["pnl"] += pnl
                        state["equity"] = state["balance"]
                        state.setdefault("trades", []).append({
                            "time": ts, "symbol": sym,
                            "strategy": pos.get("strategy", ""),
                            "direction": "LONG" if pos.get("dir", 1) == 1 else "SHORT",
                            "entry": pos["entry"], "exit_price": exit_price,
                            "pnl": pnl, "reason": reason
                        })
                        state["position"] = None

            state["equity_history"].append(state["balance"])

        self.results = self._compute_metrics()
        print(f"Backtest completed in {time.time() - start_time:.1f}s")
        return self.results

    def _compute_metrics(self):
        eq = np.array(self.adapter.state["equity_history"])
        rets = np.diff(eq) / eq[:-1]
        sharpe = np.mean(rets) / np.std(rets) * np.sqrt(365 * 24) if len(rets) > 1 else 0
        maxdd = (np.maximum.accumulate(eq) - eq).max() / np.maximum.accumulate(eq).max()
        trades = self.adapter.state.get("trades", [])
        winrate = np.mean([t["pnl"] > 0 for t in trades]) if trades else 0
        profit_factor = (sum(t["pnl"] for t in trades if t["pnl"] > 0) /
                         abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))) if trades else 0
        return {
            "sharpe": sharpe,
            "maxdd": maxdd,
            "winrate": winrate,
            "profit_factor": profit_factor,
            "trades": len(trades),
            "final_balance": self.adapter.state["balance"],
            "equity_history": self.adapter.state["equity_history"],
            "trade_list": trades
        }
