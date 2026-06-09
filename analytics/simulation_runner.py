"""
Runner de simulación para backtesting.
Utiliza datos históricos de OKX y aplica la lógica real del orquestador.
"""
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import Config
from runtime.orchestrator import Orchestrator
from analytics.trade_logger import TradeLogger
from analytics.equity_curve import EquityCurve

logger = logging.getLogger(__name__)

class SimulationRunner:
    def __init__(self, start: datetime, end: datetime, capital=10000.0):
        self.start = start
        self.end = end
        self.capital = capital
        self.orchestrator = Orchestrator()   # contendrá la lógica real
        self.trade_logger = TradeLogger()
        self.equity_curve = EquityCurve(initial_capital=capital)

    def run(self):
        current = self.start
        while current <= self.end:
            # Simula la ejecución diaria (el orquestador maneja el bucle interno de 4h)
            logger.info(f"Simulating day {current.date()}")
            self.orchestrator.run()   # Ejecuta un ciclo (modificado para aceptar ventana temporal)
            # Registro de trades generado internamente por el orquestador
            # Actualizar equity curve
            current += timedelta(days=1)
