class SignalAlignment:
    def evaluate(self, signal_direction: int, mtf_convergence: float, regime: str, entropy: float) -> float:
        base = mtf_convergence
        if regime == 'trend' and signal_direction == 1:
            base *= 1.2
        elif regime == 'mean_reversion':
            base *= 0.7
        base *= (1 - entropy)
        return min(1.0, base)
