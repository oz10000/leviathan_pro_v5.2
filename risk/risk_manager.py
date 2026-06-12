import logging
from config import Config

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, client=None, edge_monitor=None):
        self.client = client
        self.edge_monitor = edge_monitor
        self.max_position_size = Config.MAX_POSITION_SIZE * Config.CAPITAL
        self.max_daily_loss = Config.MAX_DAILY_LOSS * Config.CAPITAL
        self.max_exposure = Config.MAX_EXPOSURE * Config.CAPITAL
        self.current_exposure = 0.0
        self.daily_pnl = 0.0

    def evaluate(self, signal, daps_engine):
        symbol = signal['symbol']
        edge_score = signal.get('edge_score', 0.5)
        leverage = signal.get('leverage', Config.MAX_LEVERAGE)

        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning("Daily loss limit reached, blocking trade")
            return False, 0

        if self.current_exposure >= self.max_exposure:
            logger.info("Max exposure reached, blocking trade")
            return False, 0

        from leviathan_edge_core.risk.kelly import KellySizer
        win_rate = 0.7
        payoff = 0.8
        fraction = KellySizer.fraction(win_rate, payoff, Config.KELLY_SAFE_FACTOR)
        size = Config.CAPITAL * fraction * leverage

        if self.edge_monitor and self.edge_monitor.should_alert():
            logger.warning("Edge alert active: reducing position size by 50%")
            size *= 0.5

        size = min(size, self.max_position_size)
        remaining = self.max_exposure - self.current_exposure
        size = min(size, remaining)

        if size <= 0:
            return False, 0
        return True, size

    def update(self, pnl, exposure_change):
        self.daily_pnl += pnl
        self.current_exposure += exposure_change

    def reset_daily(self):
        self.daily_pnl = 0.0
