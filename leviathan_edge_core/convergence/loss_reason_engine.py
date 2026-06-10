class LossReasonEngine:
    """
    Analiza las razones de las pérdidas para identificar patrones.
    Registra el contexto de cada trade perdedor (filtros, scores, régimen).
    """
    def __init__(self):
        self.loss_contexts = []

    def log_trade(self, pnl, context):
        if pnl < 0:
            self.loss_contexts.append(context)
            if len(self.loss_contexts) > 100:
                self.loss_contexts.pop(0)

    def dominant_reason(self):
        if not self.loss_contexts:
            return None
        mtf_fails = sum(1 for c in self.loss_contexts if c.get("mtf_convergence", 1.0) < 0.65)
        div_fails = sum(1 for c in self.loss_contexts if c.get("divergence", 0.0) > 0.35)
        ent_fails = sum(1 for c in self.loss_contexts if c.get("entropy", 0.0) > 0.70)
        reasons = {"mtf": mtf_fails, "divergence": div_fails, "entropy": ent_fails}
        return max(reasons, key=reasons.get)
