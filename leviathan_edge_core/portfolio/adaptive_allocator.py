class AdaptiveCapitalAllocator:
    """
    Asigna el capital disponible entre los activos del universo en función
    de la calidad del Edge Score, la persistencia y la calidad de ejecución.
    """
    def __init__(self, daps, persistence, exec_qual, scores):
        self.daps = daps
        self.persistence = persistence
        self.exec_qual = exec_qual
        self.scores = scores

    def allocate(self, capital):
        total_score = sum(self.scores.values())
        if total_score <= 0:
            return {sym: capital * 0.08 for sym in self.scores}

        allocation = {}
        for sym, score in self.scores.items():
            weight = score / total_score
            allocation[sym] = capital * weight * 0.8
        return allocation
