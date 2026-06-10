class PersistenceEngine:
    """
    Mide la persistencia del Edge: cuánto tiempo se mantienen las señales rentables
    sin degradación significativa.
    """
    def __init__(self, window=50):
        self.window = window
        self.scores = []

    def persistence_score(self):
        if len(self.scores) < 10:
            return 1.0
        mid = len(self.scores) // 2
        first_half = sum(self.scores[:mid]) / mid
        second_half = sum(self.scores[mid:]) / (len(self.scores) - mid)
        if first_half <= 0:
            return 0.5
        ratio = second_half / first_half
        return max(0.0, min(1.0, ratio))

    def update(self, score):
        self.scores.append(score)
        if len(self.scores) > self.window:
            self.scores.pop(0)
