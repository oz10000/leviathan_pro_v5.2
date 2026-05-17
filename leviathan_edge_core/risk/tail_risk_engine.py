import numpy as np

class TailRiskEngine:
    def cvar(self, returns, alpha=0.95):
        sorted_ret = np.sort(returns)
        index = int(alpha * len(sorted_ret))
        return np.mean(sorted_ret[:index])
