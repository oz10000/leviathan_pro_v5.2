import numpy as np
from collections import deque
from config import Config

class EdgeTimeManager:
    def __init__(self):
        self.history = deque(maxlen=200)
        self.edge_short = 0.0
        self.edge_long = 0.0
        self.edge_osc = 0.0
        self.theta = 0.5
        self.state = "COMPRESSION"

    def update(self, top_scores: list):
        if not top_scores:
            return
        edge_agg = np.mean(top_scores)
        self.history.append(edge_agg)
        a_s, a_l = Config.EDGE_ALPHA_SHORT, Config.EDGE_ALPHA_LONG
        self.edge_short = a_s * edge_agg + (1 - a_s) * self.edge_short if self.edge_short else edge_agg
        self.edge_long = a_l * edge_agg + (1 - a_l) * self.edge_long if self.edge_long else edge_agg
        self.edge_osc = self.edge_short - self.edge_long
        if len(self.history) >= 30:
            self.theta = Config.EDGE_THETA_STD_FACTOR * np.std(list(self.history))
        if self.edge_osc > self.theta:
            self.state = "EXPANSION"
        elif self.edge_osc < -self.theta:
            self.state = "DEPRESSION"
        else:
            self.state = "COMPRESSION"
