class CausalityCluster:
    """
    Agrupa operaciones por características comunes (símbolo, estrategia, régimen)
    para identificar patrones de causalidad en el rendimiento.
    """
    def __init__(self):
        self.clusters = {}

    def add_trade(self, symbol, strategy, pnl, mtf_score, div_score, ent_score):
        key = f"{symbol}:{strategy}"
        if key not in self.clusters:
            self.clusters[key] = {
                "count": 0, "total_pnl": 0.0,
                "avg_mtf": 0.0, "avg_div": 0.0, "avg_ent": 0.0
            }
        c = self.clusters[key]
        c["count"] += 1
        c["total_pnl"] += pnl
        c["avg_mtf"] = (c["avg_mtf"] * (c["count"] - 1) + mtf_score) / c["count"]
        c["avg_div"] = (c["avg_div"] * (c["count"] - 1) + div_score) / c["count"]
        c["avg_ent"] = (c["avg_ent"] * (c["count"] - 1) + ent_score) / c["count"]

    def best_cluster(self):
        if not self.clusters:
            return None
        return max(self.clusters, key=lambda k: self.clusters[k]["total_pnl"] / self.clusters[k]["count"])
