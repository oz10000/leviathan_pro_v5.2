class ExchangeSync:
    def __init__(self, connector):
        self.connector = connector
    def get_open_positions(self):
        return []
    def reconcile_positions(self, local_positions):
        return True
