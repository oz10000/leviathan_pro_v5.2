import numpy as np

class MonteCarloEngine:
    def __init__(self, trade_pnls: list, base_capital=100.0):
        self.pnls = np.array(trade_pnls)
        self.base_capital = base_capital

    def run(self, n_runs=1000, slippage_std=0.0002, fill_prob=0.98):
        metrics = {'sharpe': [], 'maxdd': [], 'roi': [], 'all': []}
        for _ in range(n_runs):
            capital = self.base_capital
            eq = [capital]
            for pnl in self.pnls:
                slip = np.random.normal(0, slippage_std) * capital
                if np.random.random() > fill_prob:
                    pnl = -slip
                else:
                    pnl = pnl * capital + slip
                capital += pnl
                eq.append(capital)
            eq_arr = np.array(eq)
            returns = np.diff(eq_arr) / eq_arr[:-1]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 * 24)
            maxdd = (eq_arr - np.maximum.accumulate(eq_arr)).min() / np.maximum.accumulate(eq_arr).max()
            roi = (eq_arr[-1] - self.base_capital) / self.base_capital
            metrics['sharpe'].append(sharpe)
            metrics['maxdd'].append(maxdd)
            metrics['roi'].append(roi)
        metrics['all'] = metrics['sharpe']
        return {k: {'mean': np.mean(v), 'p5': np.percentile(v, 5), 'p95': np.percentile(v, 95), 'all': v} for k, v in metrics.items() if k != 'all'}
