class SignalAlignment:
    """
    Verifica la alineación de la señal entre diferentes timeframes.
    """
    def __init__(self):
        self.alignment_score = 0.0

    def compute(self, tf_data):
        trends = [tf_data[tf]["trend"] for tf in ["5m", "15m", "1h"] if tf in tf_data]
        if len(trends) < 2:
            return 0.5
        if all(t == trends[0] for t in trends):
            return 1.0
        pos = sum(1 for t in trends if t == 1)
        neg = sum(1 for t in trends if t == -1)
        return max(pos, neg) / len(trends)
