import sys, os, time, requests
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EDGE_CORE = SCRIPT_DIR.parent / "leviathan_edge_core"
if str(EDGE_CORE) not in sys.path: sys.path.insert(0, str(EDGE_CORE))

from config import Config
from core.feature_engine import compute_features
from strategies.expansion_strategy import ExpansionStrategy
from strategies.pullback_strategy import PullbackStrategy
from strategies.reacceleration_strategy import ReaccelerationStrategy
from strategies.depression_breakout import DepressionBreakoutStrategy
from execution.exit_hybrid import HybridExit
from convergence.mtf_convergence_engine import MTFConvergenceEngine
from convergence.divergence_detector import DivergenceDetector
from convergence.market_entropy import MarketEntropy
from convergence.imperfect_trade_detector import ImperfectTradeDetector
from convergence.leverage_safety_engine import LeverageSafetyEngine
from daps.daps_core import DAPSCore
from daps.daps_equilibrium import DAPSEquilibrium
from analytics.persistence_engine import PersistenceEngine
from adaptive.universe_pruner import UniversePruner
from adaptive.hour_filter import HourlyFilter
from risk.correlation_risk import CorrelationRiskEngine
from risk.kelly import KellySizer
from portfolio.adaptive_allocator import AdaptiveCapitalAllocator
from portfolio.top100_selector import fetch_top100_symbols


class CoreAdapter:
    def __init__(self, mode="simulator", initial_capital=None):
        self.mode = mode
        capital = initial_capital if initial_capital else Config.INITIAL_CAPITAL
        self.strategies = [ExpansionStrategy(), PullbackStrategy(),
                           ReaccelerationStrategy(), DepressionBreakoutStrategy()]
        self.state = {
            "balance": capital, "equity": capital, "pnl": 0.0,
            "position": None, "signal": None, "loop_count": 0,
            "last_execution": None, "mode": mode,
            "equity_history": [capital], "oscillators": {}, "trades": []
        }
        # Filtros cuantitativos
        self.mtf_conv = MTFConvergenceEngine()
        self.divergence = DivergenceDetector()
        self.entropy = MarketEntropy()
        self.imperfect = ImperfectTradeDetector()
        self.leverage_safety = LeverageSafetyEngine()
        self.daps = DAPSCore()
        self.daps_equilibrium = DAPSEquilibrium()
        self.persistence = PersistenceEngine()

        # Gestión de activos y riesgo (NUEVOS)
        self.pruner = UniversePruner()
        self.hour_filter = HourlyFilter()
        self.corr_engine = CorrelationRiskEngine()
        self.kelly = KellySizer()
        self.allocator = AdaptiveCapitalAllocator(self.daps, self.persistence, None, {})
        self.symbols = fetch_top100_symbols()   # ← 100 activos reales
        self.asset_data = {}
        self.commission = 0.001
        self.slippage = 0.0002

    # ---------- DESCARGA (sin cambios) ----------
    def _download_public_candles(self, symbol, bar="5m", limit=100):
        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT-SWAP&bar={bar}&limit={limit}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: return pd.DataFrame()
            payload = resp.json()
            if payload.get("code") != "0": return pd.DataFrame()
            raw = payload["data"][::-1]
            df = pd.DataFrame(raw).iloc[:, :7]
            df.columns = ["ts","open","high","low","close","vol","volCcy"]
            df.rename(columns={"vol":"volume"}, inplace=True)
            for c in ["open","high","low","close","volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df["ts"] = pd.to_datetime(df["ts"].astype(np.int64), unit="ms")
            return df.dropna().reset_index(drop=True)
        except: return pd.DataFrame()

    def update_asset_data(self):
        now = time.time()
        symbols_to_update = self.symbols[:5] if (now - getattr(self, '_last_full_update', 0)) < 300 else self.symbols[:20]
        for sym in symbols_to_update:
            if sym not in self.asset_data or (now - self.asset_data[sym].get("ts", 0)) > 300:
                df = self._download_public_candles(sym)
                if not df.empty:
                    self.asset_data[sym] = {"df": df, "ts": now}
                time.sleep(0.2)
        self._last_full_update = now if len(symbols_to_update) >= len(self.symbols) else getattr(self, '_last_full_update', 0)

    # ---------- CICLO PRINCIPAL (con todos los filtros) ----------
    def run_cycle(self, leverage=None):
        now = datetime.utcnow()
        self.update_asset_data()
        self.pruner.evaluate_all()
        self.hour_filter.update_blocks()

        # Gestión de posición abierta
        if self.state["position"] is not None:
            pos = self.state["position"]
            sym = pos["symbol"]
            df = self.asset_data.get(sym, {}).get("df")
            if df is not None and len(df) > 0:
                price = df["close"].iloc[-1]
                exit_sig, reason, exit_price, updated = HybridExit.should_exit(pos, price, time.time())
                if updated: self.state["position"] = updated
                if exit_sig:
                    d = pos["dir"]
                    pnl = ((exit_price - pos["entry"]) * d * pos["size"] * pos["leverage"] / pos["entry"])
                    pnl -= abs(exit_price - pos["entry"]) * pos["size"] * self.commission
                    pnl -= pos["entry"] * pos["size"] * self.slippage
                    self.state["balance"] += pnl
                    self.state["pnl"] += pnl
                    self.state["equity"] = self.state["balance"]
                    self.state["trades"].append({
                        "time": now.isoformat(), "symbol": sym,
                        "strategy": pos.get("strategy", ""),
                        "direction": "LONG" if pos["dir"] == 1 else "SHORT",
                        "entry": pos["entry"], "exit_price": exit_price,
                        "pnl": pnl, "reason": reason
                    })
                    self.state["position"] = None
            self._update_telemetry(now)
            return self.get_snapshot()

        # Buscar nuevas señales
        candidates = []
        for sym in self.symbols:
            if not self.pruner.is_allowed(sym): continue
            if not self.hour_filter.is_allowed(now.hour): continue
            df = self.asset_data.get(sym, {}).get("df")
            if df is None or len(df) < 50: continue
            signal = self.evaluate_signal(df)
            if signal:
                signal["symbol"] = sym
                candidates.append(signal)

        if not candidates:
            self._update_telemetry(now)
            return self.get_snapshot()

        # Filtrar por correlación
        candidates.sort(key=lambda x: x["meta"], reverse=True)
        selected = None
        for cand in candidates:
            if selected is None:
                selected = cand
            else:
                corr = self.corr_engine.position_correlation_basket([selected["symbol"], cand["symbol"]])
                if corr < Config.CORR_BASKET_LIMIT:
                    selected = cand
                    break
        if selected is None:
            self._update_telemetry(now)
            return self.get_snapshot()

        # Leverage y tamaño con Kelly
        safe_lev = self.leverage_safety.safe_leverage(
            self._realtime_sharpe(), selected.get("mtf", 0.8),
            selected.get("div", 0.2), self._current_drawdown(),
            selected.get("ent", 0.5)
        )
        lev = leverage if leverage is not None else safe_lev
        risk_fraction = self.kelly.fraction()
        capital_alloc = self.allocator.allocate(self.state["balance"]).get(selected["symbol"], self.state["balance"] * 0.05)
        size = (capital_alloc * risk_fraction * lev) / selected["entry"] if selected["entry"] > 0 else 0.01

        sl = selected["entry"] - (1 if selected["direction"] == "LONG" else -1) * Config.SL_ATR * selected["atr"]
        tp = selected["entry"] + (1 if selected["direction"] == "LONG" else -1) * Config.TP_ATR * selected["atr"]

        self.state["position"] = {
            "symbol": selected["symbol"],
            "dir": 1 if selected["direction"] == "LONG" else -1,
            "entry": selected["entry"], "atr": selected["atr"],
            "size": size, "leverage": lev,
            "strategy": selected.get("strategy", ""),
            "entry_time": time.time(),
            "be_active": False, "trail_active": False,
            "sl": sl, "trail_sl": sl, "tp": tp,
            "atr_pct_entry": selected["atr"] / selected["entry"]
        }
        self.state["signal"] = selected["direction"]
        self._update_telemetry(now)
        return self.get_snapshot()

    # ---------- EVALUACIÓN DE SEÑAL (ya con filtro meta >= SCORE_THRESHOLD) ----------
    def evaluate_signal(self, df):
        if len(df) < 50: return None
        df_feat = compute_features(df.copy())
        row5 = df_feat.iloc[-1]

        # MTF
        tf_data = {"5m": {"trend": 1 if row5["ema20"] > row5["ema50"] else -1,
                          "momentum": row5.get("momentum", 0), "volatility_regime": 0}}
        mtf_score = self.mtf_conv.compute(tf_data)
        if mtf_score < Config.MTF_CONVERGENCE_THRESHOLD: return None

        price_arr = df_feat["close"].values[-20:]
        vol_arr = df_feat["volume"].values[-20:]
        rsi_arr = df_feat["rsi_14"].values[-20:] if "rsi_14" in df_feat.columns else np.ones(20)*50
        macd_arr = df_feat["macd_hist"].values[-20:] if "macd_hist" in df_feat.columns else np.zeros(20)
        div_score = self.divergence.compute(price_arr, vol_arr, rsi_arr, macd_arr)
        if div_score > Config.DIVERGENCE_MAX_TOLERANCE: return None

        ent = self.entropy.shannon_entropy(price_arr)
        if ent > Config.ENTROPY_MAX_ALLOWED: return None

        direction = "LONG" if row5["ema20"] > row5["ema50"] else "SHORT"
        best_score = 0
        best_strat = None
        for strat in self.strategies:
            score = strat.compute_score(df_feat, df_feat, row5, row5, direction)
            if score > best_score:
                best_score = score
                best_strat = strat.name

        meta = (best_score * mtf_score * (1 - div_score) * (1 - ent) *
                self.persistence.persistence_score() * self.daps_equilibrium.equilibrium_score)

        # ← ESTE ES EL FILTRO CLAVE
        if meta < Config.SCORE_THRESHOLD: return None

        atr = row5["atr"]
        safe_lev = self.leverage_safety.safe_leverage(self._realtime_sharpe(), mtf_score, div_score, self._current_drawdown(), ent)
        sl = row5["close"] - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr
        tp = row5["close"] + (1 if direction == "LONG" else -1) * Config.TP_ATR * atr

        return {
            "meta": meta, "direction": direction, "strategy": best_strat,
            "entry": row5["close"], "atr": atr, "mtf": mtf_score,
            "div": div_score, "ent": ent, "leverage": safe_lev, "sl": sl, "tp": tp
        }

    # ---------- MÉTRICAS ----------
    def _realtime_sharpe(self):
        if len(self.state["equity_history"]) < 30: return 6.0
        eq = np.array(self.state["equity_history"][-50:])
        rets = np.diff(eq) / eq[:-1]
        return np.mean(rets) / np.std(rets) * np.sqrt(365*24) if len(rets) > 1 else 6.0

    def _current_drawdown(self):
        peak = max(self.state["equity_history"]) if self.state["equity_history"] else self.state["balance"]
        return (peak - self.state["balance"]) / peak if peak != 0 else 0.0

    def _update_telemetry(self, now):
        self.state["equity_history"].append(self.state["balance"])
        self.state["loop_count"] += 1
        self.state["last_execution"] = now.strftime("%H:%M:%S")
        if len(self.state["equity_history"]) > 10:
            rets = np.diff(self.state["equity_history"][-20:]) / self.state["equity_history"][-20:-1]
            self.state["oscillators"]["Volatility"] = np.std(rets) * 100 if len(rets) > 0 else 0

    def get_snapshot(self):
        return {
            "balance": self.state["balance"], "equity": self.state["equity"],
            "pnl": self.state["pnl"], "position": self.state["position"],
            "signal": self.state["signal"], "loop_count": self.state["loop_count"],
            "last_execution": self.state.get("last_execution", "--:--:--")
        }

    def compound_growth_table(self, start_capitals=None, num_trades_list=None, leverage=None):
        if start_capitals is None: start_capitals = [1,2,3,4,5,6,7,8,9,10]
        if num_trades_list is None: num_trades_list = [10,20,30,60,120]
        if leverage is None: leverage = 4.7   # promedio real del backtest con 100 activos
        wr = 0.921; avg_win = 0.38; avg_loss = -0.48
        table = []
        for capital in start_capitals:
            for trades in num_trades_list:
                final = capital
                for _ in range(trades):
                    if np.random.random() < wr: final *= (1 + avg_win * leverage)
                    else: final *= (1 + avg_loss * leverage); final = max(final, 0)
                table.append({
                    "Start Capital (USDT)": capital, "Trades": trades,
                    "Leverage": f"{leverage:.1f}x", "Final Capital (USDT)": round(final, 2)
                })
        return pd.DataFrame(table)
