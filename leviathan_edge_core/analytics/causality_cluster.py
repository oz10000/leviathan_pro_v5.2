import numpy as np
from sklearn.cluster import DBSCAN

class CausalityCluster:
    def __init__(self):
        self.losses = []

    def add_loss(self, features: dict):
        self.losses.append(list(features.values()))

    def cluster(self):
        if len(self.losses) < 5:
            return {}
        X = np.array(self.losses)
        clustering = DBSCAN(eps=0.5, min_samples=2).fit(X)
        return {"labels": clustering.labels_.tolist()}
