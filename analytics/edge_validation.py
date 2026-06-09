def validate_edge(rotational_engine_called, daps_called, risk_manager_called):
    """
    Retorna True si todos los componentes críticos están siendo invocados.
    """
    return rotational_engine_called and daps_called and risk_manager_called
