# LEVIATHAN EDGE CORE

Núcleo cuantitativo exchange‑agnóstico.
Contiene toda la lógica matemática, estadística y estratégica de LEVIATHAN V5.2 DAPS CAUSAL OPTIMIZED.

## Estructura
- `core/` – feature engineering, scoring, regímenes, edge.
- `strategies/` – estrategias de trading (expansion, pullback, etc.).
- `convergence/` – alineación multi‑timeframe, divergencia, entropía, causalidad.
- `daps/` – Dynamic Anomaly Persistence System.
- `analytics/` – expectancia, persistencia, anomalías, streaks.
- `risk/` – Kelly, leverage safety, drawdown, correlación.
- `optimization/` – Monte Carlo, búsqueda bayesiana, genética.
- `portfolio/` – asignación de capital adaptativa.
- `telemetry/` – métricas en tiempo real.

## Uso
El edge se alimenta con un DataFrame OHLCV y devuelve un dict con:
- score
- dirección (LONG/SHORT/NONE)
- TP, SL, trailing
- leverage sugerido
- entropía, convergencia, confianza, etc.

## Validación
Ejecutar `python verify_edge.py` para comprobar imports y consistencia.
