class ImperfectTradeDetector:
    """
    Detecta operaciones que, aunque tienen un meta-score aceptable,
    presentan debilidades en algún filtro específico que las hace propensas a fallar.
    """
    def __init__(self, mtf_threshold=0.65, div_threshold=0.35, ent_threshold=0.70):
        self.mtf_threshold = mtf_threshold
        self.div_threshold = div_threshold
        self.ent_threshold = ent_threshold

    def is_defective(self, meta, div_score, ent_score, mtf_score):
        if meta > 0.7:
            if mtf_score < self.mtf_threshold * 0.8:
                return True
            if div_score > self.div_threshold * 1.5:
                return True
            if ent_score > self.ent_threshold * 1.2:
                return True
        return False
