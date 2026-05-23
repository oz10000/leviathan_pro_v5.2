import time
import numpy as np
from datetime import datetime, timezone
from config import Config
from strategies.base_strategy import BaseStrategy
from risk.kelly import KellySizer
from execution.exit_hybrid import HybridExit
from execution.hour_filter import HourFilter
from daps.daps_core import DAPSCore
from daps.daps_balance import DAPSBalance
from daps.daps_equilibrium import DAPSEquilibrium
from daps.daps_adaptive_weights import DAPSAdaptiveWeights
from analytics.streak_detector import StreakDetector
from analytics.edge_decay import EdgeDecay
from analytics.regime_cluster import RegimeCluster
from analytics.temporal_profiler import TemporalProfiler
from analytics.execution_quality import ExecutionQuality
from analytics.expectancy_engine import ExpectancyEngine
from analytics.persistence_engine import PersistenceEngine as EdgePersistence
from analytics.anomaly_engine import AnomalyEngine
from analytics.causality_cluster import CausalityCluster
from analytics.performance_tracker import PerformanceTracker
from analytics.statistical_guard import StatisticalGuard
from convergence.mtf_convergence_engine import MTFConvergenceEngine
from convergence.divergence_detector import DivergenceDetector
from convergence.signal_alignment import SignalAlignment
from convergence.fractal_confirmation import FractalConfirmation
from convergence.temporal_resonance import TemporalResonance
from convergence.loss_reason_engine import LossReasonEngine
from convergence.imperfect_trade_detector import ImperfectTradeDetector
from convergence.leverage_safety_engine import LeverageSafetyEngine
from convergence.market_entropy import MarketEntropy
from portfolio.adaptive_allocator import AdaptiveCapitalAllocator


class RotationalEngine:
    """
    Motor principal de trading rotativo.
    Integra estrategias, filtros causales, DAPS, gestión de riesgo
    y todas las protecciones operativas.
    """

    def __init__(self, strategies, universe, capital, data_feeds):
        self.strategies = strategies
        self.universe = universe
        self.capital = capital
        self.peak_capital = capital
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

        # ─── DAPS ───────────────────────────────────────────────
        self.daps = DAPSCore()
        self.daps_balance = DAPSBalance()
        self.daps_equilibrium = DAPSEquilibrium()
        self.daps_weights = DAPSAdaptiveWeights()

        # ─── Analytics ──────────────────────────────────────────
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

        # ─── Convergence ────────────────────────────────────────
        self.mtf_conv = MTFConvergenceEngine()
        self.divergence = DivergenceDetector()
        self.signal_align = SignalAlignment()
        self.fractal = FractalConfirmation()
        self.temporal_res = TemporalResonance()
        self.loss_reason = LossReasonEngine()
        self.imperfect = ImperfectTradeDetector()
        self.leverage_safety = LeverageSafetyEngine()
        self.entropy = MarketEntropy()

        # ─── Risk & Allocation ──────────────────────────────────
        self.kelly = {s.name: KellySizer() for s in strategies}
        self.asset_scores = {sym: 0.85 for sym in universe}
        self.allocator = AdaptiveCapitalAllocator(
            self.daps, self.persistence, self.exec_qual, self.asset_scores
        )

        # ─── Validación estadística ────────────────────────────
        self.pnl_history = []

    # ==================================================================
    # CICLO PRINCIPAL
    # ==================================================================
    def cycle(self):
        now = datetime.now(timezone.utc)

        # Control horario
        if self.current_hour != now.hour:
            self.current_hour = now.hour
            self.hourly_trades = 0
        if self.hourly_trades >= 12:
            return None
        if self.last_trade_time and (now - self.last_trade_time).seconds < 30:
            return None

        # Filtro horario (anti dead‑zone)
        if not HourFilter.is_tradeable_hour():
            return None

        # Statistical Guard (bloquea si métricas recientes son insuficientes)
        if not StatisticalGuard.validate(self.pnl_history):
            self.status = "STAT_GUARD_BLOCK"
            return None

        # ─── Actualización DAPS ─────────────────────────────────
        epsilon = self.anomaly.anomaly_score()
        raw_expectancy = self.expectancy.compute()
        x_hat = np.clip(raw_expectancy / (self.capital * 0.04 + 1e-8), -1.0, 1.0)
        self.daps.step(epsilon, x_hat)
        eq_factor = self.daps_equilibrium.factor(self.daps.x)
        self.daps_balance.update(self.daps.x)

        # ─── Evaluación de candidatos ──────────────────────────
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

            # MTF convergence
            tf_data = {}
            for tf, df in [("5m", df5), ("15m", df15), ("1h", df1h)]:
                if df is not None and len(df) > 5:
                    row = df.iloc[-1]
                    tf_data[tf] = {
                        "trend": 1 if row["ema20"] > row["ema50"] else -1,
                        "momentum": row.get("momentum", 0),
                        "volatility_regime": 0
                    }
            mtf_score = self.mtf_conv.compute(tf_data)
            if mtf_score < Config.MTF_CONVERGENCE_THRESHOLD:
                self._signals_filtered += 1
                continue

            # Divergencia
            price = df5["close"].values[-20:]
            vol = df5["volume"].values[-20:]
            rsi = df5["rsi_14"].values[-20:] if "rsi_14" in df5.columns else np.full(20, 50)
            macd_hist = df5["macd_hist"].values[-20:] if "macd_hist" in df5.columns else np.zeros(20)
            div_score = self.divergence.compute(price, vol, rsi, macd_hist)
            if div_score > Config.DIVERGENCE_MAX_TOLERANCE:
                self._signals_filtered += 1
                continue

            # Entropía
            ent = self.entropy.shannon_entropy(price)
            if ent > Config.ENTROPY_MAX_ALLOWED:
                self._signals_filtered += 1
                continue

            row5 = df5.iloc[-1]
            row15 = df15.iloc[-1] if df15 is not None and len(df15) > 0 else row5
            direction = "LONG" if row5["ema20"] > row5["ema50"] else "SHORT"

            for strat in self.strategies:
                base_score = strat.compute_score(df5, df15, row5, row15, direction)
                meta = (base_score *
                        mtf_score *
                        (1 - div_score) *
                        (1 - ent) *
                        self.persistence.persistence_score() *
                        self.exec_qual.quality_score() *
                        eq_factor)

                if self.imperfect.is_defective(meta, div_score, ent, mtf_score):
                    self._signals_filtered += 1
                    continue

                alloc = self.allocator.allocate(self.capital).get(sym, 0)
                candidates.append((meta, sym, direction, strat, row5, alloc,
                                   mtf_score, div_score, ent))

        if not candidates:
            self.last_signal = None
            return None

        # ─── Mejor candidato ────────────────────────────────────
        best = max(candidates, key=lambda x: x[0])
        meta, sym, direction, strat, row, capital_alloc, mtf, div, ent = best

        # Leverage dinámico seguro
        dd = (self.peak_capital - self.capital) / self.peak_capital if self.peak_capital else 0
        current_sharpe = self.perf_tracker.realtime_sharpe()
        safe_lev = self.leverage_safety.safe_leverage(
            sharpe_roll=current_sharpe,
            mtf_conv=mtf, divergence=div, drawdown=dd, entropy=ent
        )

        # Kelly sizing con safe‑factor
        risk_pct = self.kelly[strat.name].fraction(sharpe=current_sharpe)
        entry = row["close"]
        atr = row["atr"]
        size = (capital_alloc * risk_pct * safe_lev) / entry if entry > 0 else 0

        # ─── Construcción de posición ───────────────────────────
        self.position = {
            "symbol": sym,
            "dir": 1 if direction == "LONG" else -1,
            "entry": entry,
            "atr": atr,
            "size": size,
            "leverage": safe_lev,
            "strategy": strat.name,
            "entry_time": time.time(),
            "be_active": False,
            "trail_active": False,
            "sl": entry - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr,
            "trail_sl": entry - (1 if direction == "LONG" else -1) * Config.SL_ATR * atr,
            "meta_score": meta,
            "mtf": mtf,
            "div": div,
            "ent": ent
        }
        self.last_signal = {"symbol": sym, "direction": direction, "score": meta}
        self.last_trade_time = now
        self.hourly_trades += 1
        return self.position

    # ==================================================================
    # GESTIÓN DE POSICIÓN ABIERTA
    # ==================================================================
    def update_position(self, price, atr_hist=None):
        if not self.position:
            return
        exit_sig, reason, exit_px, updated = HybridExit.should_exit(
            self.position, price, time.time(), atr_hist
        )
        if updated:
            self.position = updated
        if exit_sig:
            d = self.position["dir"]
            pnl = ((exit_px - self.position["entry"]) * d *
                   self.position["leverage"] * self.position["size"] /
                   self.position["entry"])
            self.capital += pnl
            self.peak_capital = max(self.peak_capital, self.capital)

            # Alimentar analytics
            self.expectancy.add(pnl)
            self.anomaly.feed(pnl, self.position.get("meta_score", 0))
            self.loss_reason.log_trade(pnl, {
                "mtf_convergence": self.position.get("mtf", 1),
                "divergence": self.position.get("div", 0),
                "entropy": self.position.get("ent", 0)
            })
            self.temporal_res.update(datetime.now(timezone.utc), pnl)
            self.streak.add_trade({"pnl": pnl, "time": datetime.now(timezone.utc)})
            self.pnl_history.append(pnl)
            self.perf_tracker.add_equity_snapshot(self.capital)

            self.position = None
