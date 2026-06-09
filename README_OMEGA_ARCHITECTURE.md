# Arquitectura Definitiva Leviathan DAPS-Ω v5.2 (Estado B)

## Flujo del Edge
1. **Universo**: Top 100 swaps OKX → Velocity‑Momentum Engine (12 activos).
2. **Datos**: Velas 5m/15m/1h vía REST.
3. **Features**: ATR, EMA, RSI, MACD.
4. **Filtros**: MTF Convergence, Divergence Detector, Market Entropy.
5. **Señales**: 4 estrategias + LSTM + Ensemble.
6. **DAPS Ω**: modulación con decaimiento exponencial (λ=0.99).
7. **Edge Score**: combinación ponderada (scoring.py).
8. **Rotational Engine**: selección de la mejor señal.
9. **Riesgo**: RiskManager (VaR, Kelly, límites) + Circuit Breaker.
10. **Ejecución**: OrderRouter (OKX REST) con órdenes de mercado + TP/SL condicionales.
11. **Salidas**: ExitHybrid (TP, SL, Break Even, Trailing Stop, Time Decay).
12. **Monitoreo**: EdgeMonitor (Profit Factor en tiempo real) + PnL Tracker.
13. **Reconciliación**: Reconciler (posiciones WS vs REST) con tabla sent_orders.
14. **Persistencia**: Snapshots JSON en artifacts de GitHub (DAPS, posiciones, métricas).

## Componentes críticos
- `rotational_engine.py`
- `daps/core.py`
- `risk_manager.py`
- `order_router.py`
- `exit_hybrid.py`

## Invariantes del sistema
- El Rotational Engine debe ejecutarse en cada ciclo.
- El DAPS debe recibir los precios de cierre y actualizar su estado.
- El RiskManager debe evaluar cada señal antes de ejecutar.
- El OrderRouter debe enviar órdenes con un clOrdId único.
- El ExitHybrid debe gestionar todas las posiciones abiertas.
- El EdgeMonitor debe registrar cada operación cerrada.

## Simulación
Ejecutar `analytics/simulation_runner.py` con los parámetros de período y capital.
Los resultados se comparan con `analytics/comparison_report.py`.
