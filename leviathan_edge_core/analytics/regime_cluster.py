import numpy as np
from collections import deque
from sklearn.cluster import KMeans

class RegimeCluster:
    def __init__(self, n_clusters=3):
        self.n_clusters = n_clusters
        self.buffer = deque(maxlen=500)
        self.model = None
        self.labels = None

    def update(self, features: dict):
        self.buffer.append(list(features.values()))
        if len(self.buffer) >= 30 and len(self.buffer) % 10 == 0:
            data = np.array(self.buffer)
            self.model = KMeans(n_clusters=self.n_clusters, n_init=1, random_state=42).fit(data)
            self.labels = self.model.labels_

    def current_label(self) -> int:
        if self.model is None:
            return -1
        return self.model.predict(np.array([list(self.buffer[-1])]))[0]

    def cluster_stability(self) -> float:
        if self.labels is None:
            return 0.0
        dominant = np.bincount(self.labels[-min(100, len(self.labels)):]).max() / min(100, len(self.labels))
        return dominant
