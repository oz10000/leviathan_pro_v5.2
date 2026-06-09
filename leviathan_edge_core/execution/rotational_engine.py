import time
import numpy as np
from datetime import datetime, timezone
from config import Config
from leviathan_edge_core.strategies.base_strategy import BaseStrategy
from leviathan_edge_core.risk.kelly import KellySizer
from leviathan_edge_core.execution.exit_hybrid import HybridExit
from leviathan_edge_core.execution.hour_filter import HourFilter
from leviathan_edge_core.daps.daps_core import DAPSCore
from leviathan_edge_core.daps.daps_balance import DAPSBalance
from leviathan_edge_core.daps.daps_equilibrium import DAPSEquilibrium
from leviathan_edge_core.daps.daps_adaptive_weights import DAPSAdaptiveWeights
from leviathan_edge_core.analytics.streak_detector import StreakDetector
from leviathan_edge_core.analytics.edge_decay import EdgeDecay
from leviathan_edge_core.analytics.regime_cluster import RegimeCluster
from leviathan_edge_core.analytics.temporal_profiler import TemporalProfiler
from leviathan_edge_core.analytics.execution_quality import ExecutionQuality
from leviathan_edge_core.analytics.expectancy_engine import ExpectancyEngine
from leviathan_edge_core.analytics.persistence_engine import PersistenceEngine as EdgePersistence
from leviathan_edge_core.analytics.anomaly_engine import AnomalyEngine
from leviathan_edge_core.analytics.causality_cluster import CausalityCluster
from leviathan_edge_core.analytics.performance_tracker import PerformanceTracker
from leviathan_edge_core.analytics.statistical_guard import StatisticalGuard
from leviathan_edge_core.convergence.mtf_convergence_engine import MTFConvergenceEngine
from leviathan_edge_core.convergence.divergence_detector import DivergenceDetector
from leviathan_edge_core.convergence.signal_alignment import SignalAlignment
from leviathan_edge_core.convergence.fractal_confirmation import FractalConfirmation
from leviathan_edge_core.convergence.temporal_resonance import TemporalResonance
from leviathan_edge_core.convergence.loss_reason_engine import LossReasonEngine
from leviathan_edge_core.convergence.imperfect_trade_detector import ImperfectTradeDetector
from leviathan_edge_core.convergence.leverage_safety_engine import LeverageSafetyEngine
from leviathan_edge_core.convergence.market_entropy import MarketEntropy
from leviathan_edge_core.portfolio.adaptive_allocator import AdaptiveCapitalAllocator


class RotationalEngine:
    def __init__(self, strategies, universe, capital, data_feeds):
        self.strategies = strategies
        self.universe = universe
        self.capital = float(capital)
        self.peak_capital = float(capital)
        self.data = data_feeds
        self.position = None
        self.last_trade_time = None
        self.hourly_trades = 0
        self.current_hour = None
        self._loop_count = 0
        self.status = "RUNNING"
        self.last_signal = None
        self.winrate = 0.0
        self.profit_factor = 0.0
        self.max_drawdown = 0.0
        self._signals_filtered = 0

        self.daps = DAPSCore()
        self.daps_balance = DAPSBalance()
        self.daps_equilibrium = DAPSEquilibrium()
        self.daps_weights = DAPSAdaptiveWeights()

        self.streak = StreakDetector()
        self.edge_decay = EdgeDecay()
        self.regime_cluster = RegimeCluster()
        self.temporal_profiler = TemporalProfiler()
        self.exec_qual = ExecutionQuality()
        self.expectancy = ExpectancyEngine()
        self.persistence = EdgePersistence()
        self.anomaly = AnomalyEngine()
        self.causality_cluster = CausalityCluster()
        self.perf_tracker = PerformanceTracker(window=25)

        self.mtf_conv = MTFConvergenceEngine()
        self.divergence = DivergenceDetector()
        self.signal_align = SignalAlignment()
        self.fractal = FractalConfirmation()
        self.temporal_res = TemporalResonance()
        self.loss_reason = LossReasonEngine()
        self.imperfect = ImperfectTradeDetector()
        self.leverage_safety = LeverageSafetyEngine()
        self.entropy = MarketEntropy()

        self.kelly = {s.name: KellySizer() for s in strategies}
        self.asset_scores = {sym: 0.85 for sym in universe}
        self.allocator = AdaptiveCapitalAllocator(
            self.daps, self.persistence, self.exec_qual, self.asset_scores
        )

        self.pnl_history = []

    def cycle(self):
        now = datetime.now(timezone.utc)
        if self.current_hour != now.hour:
            self.current_hour = now.hour
            self.hourly_trades = 0
        if self.hourly_trades >= 12:
            return None
        if self.last_trade_time and (now - self.last_trade_time).seconds < 30:
            return None

        if not HourFilter.is_tradeable_hour():
            return None

        if not StatisticalGuard.validate(self.pnl_history):
            self.status = "STAT_GUARD_BLOCK"
            return None

        epsilon = self.anomaly.anomaly_score()
        raw_expectancy = self.expectancy.compute()
        x_hat = np.clip(raw_expectancy / (self.capital * 0.04 + 1e-8), -1.0, 1.0)
        self.daps.step(epsilon, x_hat)
        eq_factor = self.daps_equilibrium.factor(self.daps.x)
        self.daps_balance.update(self.daps.x)

        self._signals_filtered = 0
        candidates = []

        for sym in self.universe:
            dfs = self.data.get(sym, {})
            if not dfs:
                self._signals_filtered += 1
                continue
            df5 = dfs.get("5m")
            df15 = dfs.get("15m")
            df1h = dfs.get("1h")
            if df5 is None or len(df5) < 20:
                self._signals_filtered += 1
                continue

            tf_data = {}
            for tf, df in [("5m", df5), ("15m", df15), ("1h", df1h)]:
                if df is not None and len(df) > 5:
                    row = df.iloc[-1]
                    tf_data[tf] = {
                        "trend": 1 if row["ema20"] > row["ema50"] else -1,
                        "momentum": float(row.get("momentum", 0)),
                        "volatility_regime": 0
                    }
            mtf_score = self.mtf_conv.compute(tf_data)
            if mtf_score < Config.MTF_CONVERGENCE_THRESHOLD:
                self._signals_filtered += 1
                continue

            price = df5["close"].values[-20:]
            vol = df5["volume"].values[-20:]
            rsi = df5["rsi_14"].values[-20:] if "rsi_14" in df5.columns else np.full(20, 50)
            macd_hist = df5["macd_hist"].values[-20:] if "macd_hist" in df5.columns else np.zeros(20)
            div_score = self.divergence.compute(price, vol, rsi, macd_hist)
            if div_score > Config.DIVERGENCE_MAX_TOLERANCE:
                self._signals_filtered += 1
                continue

            ent = self.entropy.shannon_entropy(price)
            if ent > Config.ENTROPY_MAX_ALLOWED:
                self._signals_filtered += 1
                continue

            row5 = df5.iloc[-1]
            row15 = df15.iloc[-1] if df15 is not None and len(df15) > 0 else row5
            direction = "LONG" if row5["ema20"] > row5["ema50"] else "SHORT"

            for strat in self.strategies:
                base_score = strat.compute_score(df5, df15, row5, row15, direction)
                meta = (float(base_score) *
                        float(mtf_score) *
                        (1.0 - float(div_score)) *
                        (1.0 - float(ent)) *
                        float(self.persistence.persistence_score()) *
                        float(self.exec_qual.quality_score()) *
                        float(eq_factor))

                if self.imperfect.is_defective(meta, div_score, ent, mtf_score):
                    self._signals_filtered += 1
                    continue

                alloc = self.allocator.allocate(self.capital).get(sym, 0.0)
                candidates.append((meta, sym, direction, strat, row5, alloc,
                                   mtf_score, div_score, ent))

        if not candidates:
            self.last_signal = None
            return None

        best = max(candidates, key=lambda x: x[0])
        meta, sym, direction, strat, row, capital_alloc, mtf, div, ent = best

        dd = (self.peak_capital - self.capital) / self.peak_capital if self.peak_capital else 0.0
        current_sharpe = self.perf_tracker.realtime_sharpe()
        safe_lev = self.leverage_safety.safe_leverage(
            sharpe_roll=current_sharpe,
            mtf_conv=mtf, divergence=div, drawdown=dd, entropy=ent
        )

        risk_pct = self.kelly[strat.name].fraction(sharpe=current_sharpe)
        entry = float(row["close"])
        atr = float(row["atr"])
        size = (float(capital_alloc) * risk_pct * safe_lev) / entry if entry > 0 else 0.0

        self.position = {
            "symbol": sym,
            "dir": 1 if direction == "LONG" else -1,
            "entry": entry,
            "atr": atr,
            "size": float(size),
            "leverage": float(safe_lev),
            "strategy": strat.name,
            "entry_time": time.time(),
            "be_active": False,
            "trail_active": False,
            "sl": float(entry - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr),
            "trail_sl": float(entry - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr),
            "meta_score": float(meta),
            "mtf": float(mtf),
            "div": float(div),
            "ent": float(ent)
        }
        self.last_signal = {"symbol": sym, "direction": direction, "score": float(meta)}
        self.last_trade_time = now
        self.hourly_trades += 1
        return self.position

    def update_position(self, price, atr_hist=None):
        if not self.position:
            return
        exit_sig, reason, exit_px, updated = HybridExit.should_exit(
            self.position, float(price), time.time(), atr_hist
        )
        if updated:
            self.position = updated
        if exit_sig:
            d = self.position["dir"]
            entry = float(self.position["entry"])
            leverage = float(self.position["leverage"])
            size = float(self.position["size"])
            pnl = ((float(exit_px) - entry) * d * leverage * size / entry) if entry != 0 else 0.0
            self.capital += pnl
            self.peak_capital = max(self.peak_capital, self.capital)

            self.expectancy.add(pnl)
            self.anomaly.feed(pnl, self.position.get("meta_score", 0.0))
            self.loss_reason.log_trade(pnl, {
                "mtf_convergence": self.position.get("mtf", 1.0),
                "divergence": self.position.get("div", 0.0),
                "entropy": self.position.get("ent", 0.0)
            })
            self.temporal_res.update(datetime.now(timezone.utc), pnl)
            self.streak.add_trade({"pnl": pnl, "time": datetime.now(timezone.utc)})
            self.pnl_history.append(pnl)
            self.perf_tracker.add_equity_snapshot(self.capital)
            self.position = None
