import time, numpy as np
from datetime import datetime
from config import Config
from portfolio.adaptive_allocator import AdaptiveCapitalAllocator
from core.edge_time import EdgeTimeManager
from core.era import ERAModule
from risk.dynamic_leverage import dynamic_leverage
from risk.kelly import KellySizer
from execution.exit_hybrid import HybridExit
from daps.daps_core import DAPSCore
from daps.daps_balance import DAPSBalance
from daps.daps_equilibrium import DAPSEquilibrium
from analytics.streak_detector import StreakDetector
from analytics.edge_decay import EdgeDecay
from analytics.regime_cluster import RegimeCluster
from analytics.temporal_profiler import TemporalProfiler
from analytics.execution_quality import ExecutionQuality
from analytics.expectancy_engine import ExpectancyEngine
from analytics.persistence_engine import PersistenceEngine
from analytics.anomaly_engine import AnomalyEngine
from analytics.causality_cluster import CausalityCluster
from convergence.mtf_convergence_engine import MTFConvergenceEngine
from convergence.divergence_detector import DivergenceDetector
from convergence.signal_alignment import SignalAlignment
from convergence.fractal_confirmation import FractalConfirmation
from convergence.temporal_resonance import TemporalResonance
from convergence.anomaly_causality import AnomalyCausality
from convergence.loss_reason_engine import LossReasonEngine
from convergence.imperfect_trade_detector import ImperfectTradeDetector
from convergence.leverage_safety_engine import LeverageSafetyEngine
from convergence.market_entropy import MarketEntropy
from adaptive.universe_pruner import UniversePruner
from adaptive.hour_filter import HourlyFilter
from risk.correlation_risk import CorrelationRiskEngine
from execution.order_validator import OrderValidator
from execution.exchange_sync import ExchangeSync
from execution.okx_api_connector import OKXConnector
import logging

logger = logging.getLogger("rotational_engine")

class RotationalEngine:
    def __init__(self, strategies, universe, capital, data_feeds):
        self.strategies = strategies
        self.universe = universe
        self.capital = capital
        self.peak_capital = capital
        self.data = data_feeds
        self.position = None
        self.edge_mgr = EdgeTimeManager()
        self.era = ERAModule()
        self.last_trade_time = None
        self.hourly_trades = 0
        self.current_hour = None

        # DAPS
        self.daps = DAPSCore()
        self.daps_balance = DAPSBalance()
        self.daps_equilibrium = DAPSEquilibrium()

        # Analytics
        self.streak = StreakDetector()
        self.edge_decay = EdgeDecay()
        self.regime_cluster = RegimeCluster()
        self.temporal_profiler = TemporalProfiler()
        self.exec_qual = ExecutionQuality()
        self.expectancy = ExpectancyEngine()
        self.persistence = PersistenceEngine()
        self.anomaly = AnomalyEngine()
        self.causality_cluster = CausalityCluster()

        # Convergence
        self.mtf_conv = MTFConvergenceEngine()
        self.divergence = DivergenceDetector()
        self.signal_align = SignalAlignment()
        self.fractal = FractalConfirmation()
        self.temporal_res = TemporalResonance()
        self.anomaly_causality = AnomalyCausality()
        self.loss_reason = LossReasonEngine()
        self.imperfect = ImperfectTradeDetector()
        self.leverage_safety = LeverageSafetyEngine()
        self.entropy = MarketEntropy()

        # Adaptive
        self.pruner = UniversePruner()
        self.hour_filter = HourlyFilter()
        self.corr_engine = CorrelationRiskEngine()

        # Execution helpers
        self.order_validator = OrderValidator()
        self.connector = OKXConnector()
        self.exchange_sync = ExchangeSync(self.connector)

        self.kelly = {s.name: KellySizer() for s in strategies}
        self.asset_scores = {sym: 0.85 for sym in universe}
        self.allocator = AdaptiveCapitalAllocator(self.daps, self.persistence, self.exec_qual, self.asset_scores)
        self.equity_curve = [self.capital]
        self.all_trades = []

        self.current_state = {
            "current_symbol": "",
            "current_strategy": "",
            "current_score": 0,
            "no_trade_reason": "",
            "mtf_convergence": 0,
            "entropy": 0,
            "leverage": 0,
            "api_status": "connected",
            "websocket_status": "disconnected",
            "latency_ms": 0,
        }

    def cycle(self):
        now = datetime.utcnow()
        hour = now.hour

        self.exchange_sync.reconcile_positions(self._get_local_positions())

        if not self.hour_filter.is_allowed(hour):
            self.current_state["no_trade_reason"] = "hour_blocked"
            return None

        if self.current_hour != hour:
            self.current_hour = hour
            self.hourly_trades = 0
        if self.hourly_trades >= 12 or (self.last_trade_time and (now - self.last_trade_time).seconds < 30):
            self.current_state["no_trade_reason"] = "cooldown"
            return None

        for sym in self.universe:
            dfs = self.data.get(sym, {})
            df5 = dfs.get("5m") if dfs else None
            if df5 is not None and len(df5) > 0:
                self.corr_engine.update_price(sym, df5["close"].iloc[-1])

        if now.hour == Config.PRUNE_CHECK_HOUR and now.minute < 5:
            self.pruner.evaluate_all()

        candidates = []
        for sym in self.universe:
            if not self.pruner.is_allowed(sym):
                continue
            dfs = self.data.get(sym, {})
            if not dfs: continue
            df5 = dfs.get("5m")
            if df5 is None or len(df5) < 20: continue

            tf_data = {}
            for tf, df in [("5m", df5), ("15m", dfs.get("15m")), ("1h", dfs.get("1h"))]:
                if df is not None and len(df) > 5:
                    row = df.iloc[-1]
                    tf_data[tf] = {"trend": 1 if row["ema20"] > row["ema50"] else -1,
                                   "momentum": row.get("momentum", 0),
                                   "volatility_regime": 0}
            mtf_score = self.mtf_conv.compute(tf_data)
            if mtf_score < Config.MTF_CONVERGENCE_THRESHOLD:
                continue

            price_arr = df5["close"].values[-20:]
            vol_arr = df5["volume"].values[-20:]
            rsi_arr = df5["rsi_14"].values[-20:] if "rsi_14" in df5.columns else np.ones(20)*50
            macd_arr = df5["macd_hist"].values[-20:] if "macd_hist" in df5.columns else np.zeros(20)
            div_score = self.divergence.compute(price_arr, vol_arr, rsi_arr, macd_arr)
            if div_score > Config.DIVERGENCE_MAX_TOLERANCE:
                continue

            ent = self.entropy.shannon_entropy(price_arr)
            if ent > Config.ENTROPY_MAX_ALLOWED:
                continue

            row5 = df5.iloc[-1]
            direction = "LONG" if row5["ema20"] > row5["ema50"] else "SHORT"
            for strat in self.strategies:
                base_score = strat.compute_score(df5, df5, row5, row5, direction)
                meta = (base_score * mtf_score * (1-div_score) * (1-ent) *
                        self.persistence.persistence_score() *
                        self.exec_qual.quality_score() *
                        self.daps_equilibrium.equilibrium_score)
                if self.imperfect.is_defective(meta, div_score, ent, mtf_score):
                    continue
                alloc = self.allocator.allocate(self.capital).get(sym, 0)
                candidates.append((meta, sym, direction, strat, row5, alloc, mtf_score, div_score, ent))
                self.current_state.update({
                    "current_symbol": sym, "current_strategy": strat.name,
                    "current_score": meta, "mtf_convergence": mtf_score,
                    "entropy": ent, "no_trade_reason": "candidate_added"
                })

        if not candidates:
            return None

        active_syms = [c[1] for c in candidates]
        basket_corr = self.corr_engine.position_correlation_basket(active_syms)
        if basket_corr > Config.CORR_BASKET_LIMIT:
            self.current_state["no_trade_reason"] = "high_correlation"
            return None

        best = max(candidates, key=lambda x: x[0])
        meta, sym, direction, strat, row, capital_alloc, mtf, div, ent = best
        dd = (self.peak_capital - self.capital) / self.peak_capital if self.peak_capital else 0
        safe_lev = self.leverage_safety.safe_leverage(
            sharpe_roll=self._realtime_sharpe(), mtf_conv=mtf, divergence=div,
            drawdown=dd, entropy=ent)
        risk_pct = self.kelly[strat.name].fraction()
        entry = row["close"]; atr = row["atr"]
        size = (capital_alloc * risk_pct * safe_lev) / entry if entry > 0 else 0

        valid, reason = self.order_validator.validate(sym, size, entry, safe_lev)
        if not valid:
            self.current_state["no_trade_reason"] = f"order_invalid: {reason}"
            return None

        self.position = {
            "symbol": sym, "dir": 1 if direction=="LONG" else -1,
            "entry": entry, "atr": atr, "size": size,
            "leverage": safe_lev, "strategy": strat.name,
            "entry_time": time.time(),
            "be_active": False, "trail_active": False,
            "sl": entry - (1 if direction=="LONG" else -1)*Config.SL_ATR*atr,
            "trail_sl": entry - (1 if direction=="LONG" else -1)*Config.SL_ATR*atr,
            "meta_score": meta, "mtf": mtf, "div": div, "ent": ent
        }
        self.last_trade_time = now
        self.hourly_trades += 1
        self.current_state["leverage"] = safe_lev
        return self.position

    def _realtime_sharpe(self):
        if len(self.equity_curve) < 30: return 6.0
        rets = np.diff(self.equity_curve) / self.equity_curve[:-1]
        return np.mean(rets) / (np.std(rets)+1e-10) * np.sqrt(365*24)

    def update_position(self, price, atr_hist=None):
        if not self.position: return None, None
        exit_signal, reason, exit_px, updated = HybridExit.should_exit(
            self.position, price, time.time(), atr_hist)
        if updated: self.position = updated
        if exit_signal:
            d = self.position["dir"]
            pnl = ((exit_px - self.position["entry"]) * d *
                   self.position["leverage"] * self.position["size"] /
                   self.position["entry"])
            self.capital += pnl
            self.peak_capital = max(self.peak_capital, self.capital)
            self.equity_curve.append(self.capital)
            trade_record = {
                "time": datetime.utcnow().isoformat(),
                "symbol": self.position["symbol"],
                "strategy": self.position["strategy"],
                "direction": "LONG" if self.position["dir"]==1 else "SHORT",
                "entry": self.position["entry"],
                "exit_price": exit_px, "pnl": pnl, "reason": reason
            }
            self.all_trades.append(trade_record)
            self.position = None
            return pnl, trade_record
        return None, None

    def _get_local_positions(self):
        return {self.position["symbol"]: self.position} if self.position else {}

    def get_snapshot(self):
        return {
            "balance": self.capital, "equity": self.capital,
            "pnl": self.capital - Config.INITIAL_CAPITAL,
            "position": self.position, "signal": None,
            "loop_count": getattr(self, '_loop_count', 0),
            "last_execution": "",
            "oscillators": {}, "equity_history": self.equity_curve
        }
