class DAPSBalance:
    """
    Balance dinámico del sistema DAPS.
    Acumula la señal x con suavizado exponencial para evitar oscilaciones bruscas.
    """
    def __init__(self, alpha=0.1):
        self.value = 0.0
        self.alpha = alpha

    def update(self, x):
        self.value = (1 - self.alpha) * self.value + self.alpha * x
