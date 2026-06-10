class KellySizer:
    """
    Calcula la fracción óptima de capital según el criterio de Kelly.
    Soporta tanto el cálculo clásico (win_rate, payoff_ratio) como
    una estimación rápida basada en el Sharpe ratio.
    """

    @staticmethod
    def fraction(win_rate=0.6, payoff_ratio=1.0, safe_factor=0.25, sharpe=None):
        """
        Devuelve la fracción de capital a arriesgar.

        Parámetros:
        - win_rate: tasa de aciertos (0 a 1).
        - payoff_ratio: ratio ganancia media / pérdida media.
        - safe_factor: factor de seguridad (0 a 1). Reduce la fracción de Kelly
          para evitar sobreapalancamiento. Por defecto 0.25 (Kelly/4).
        - sharpe: si se proporciona, se usa una heurística basada en Sharpe
          en lugar de la fórmula clásica de Kelly.
        """
        if sharpe is not None:
            if sharpe > 1.5:
                return 0.50 * safe_factor
            elif sharpe > 1.0:
                return 0.25 * safe_factor
            elif sharpe > 0.5:
                return 0.15 * safe_factor
            else:
                return 0.05 * safe_factor

        if payoff_ratio <= 0:
            return 0.0

        kelly = (win_rate * payoff_ratio - (1 - win_rate)) / payoff_ratio
        return max(0.0, kelly * safe_factor)
