class ExposureGuard:
    def __init__(self, max_exposure=3.0):
        self.max_exposure = max_exposure

    def validate(self, total_margin, balance):
        return (total_margin / balance) <= self.max_exposure
