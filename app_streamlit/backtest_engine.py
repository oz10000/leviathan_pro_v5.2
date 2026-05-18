import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class BacktestEngine:
    """
    Backtest acelerado multi‑activo usando API pública de OKX.
    Simula el paso del tiempo vela a vela sobre el período elegido.
    """
    def __init__(self, adapter, symbols=None, days=30, bar="5m"):
        self.adapter = adapter
        self.symbols = symbols or adapter.symbols[:20]  # hasta 20 activos para no saturar
        self.days = days
        self.bar = bar
        self.max_candles = min(days * 288, 300)  # 288 velas de 5m al día; OKX limita a 300 por request
        self.data = {}          # {symbol: DataFrame}
        self.results = None

    def download_all(self):
        """Descarga velas históricas para todos los símbolos en paralelo (limitado a 4 hilos)."""
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.adapter._download_public_candles, sym, self.bar, self.max_candles): sym
                       for sym in self.symbols}
            for future in as_completed(futures):
                sym = futures[future]
                df = future.result()
                if not df.empty:
                    self.data[sym] = df
            # Asegurar que todos los DataFrames tienen el mismo índice temporal
            # (rellenar huecos con NaN y forward‑fill precios)
            self._align_timestamps()

    def _align_timestamps(self):
        """Crea un índice común de timestamps para todos los activos."""
        all_ts = set()
        for df in self.data.values():
            all_ts.update(df["ts"].values)
        self.timeline = sorted(all_ts)

    def run(self):
        """Ejecuta el backtest secuencial vela a vela."""
        print(f"Backtesting {len(self.symbols)} symbols over {len(self.timeline)} candles...")
        start_time = time.time()
        # Resetear el adaptador a capital inicial
        self.adapter.state["balance"] = 100.0
        self.adapter.state["equity"] = 100.0
        self.adapter.state["pnl"] = 0.0
        self.adapter.state["position"] = None
        self.adapter.state["equity_history"] = [100.0]
        self.adapter.state["trades"] = []

        for ts in self.timeline:
            # Construir un DataFrame de mercado en este instante (precios, features)
            market_snapshot = {}
            for sym, df in self.data.items():
                # Obtener la vela actual (última hasta ts)
                window = df[df["ts"] <= ts]
                if len(window) < 50:
                    continue
                market_snapshot[sym] = window.copy()
            if not market_snapshot:
                continue

            # Llamar al adaptador con la foto del mercado
            # (El adaptador debe aceptar múltiples DataFrames; por ahora simulamos con el primer activo)
            # *** NOTA: Para simular correctamente, el adaptador debe iterar sobre market_snapshot.
            # Esto requiere una modificación en CoreAdapter.run_cycle() para aceptar market_data.
            # Aquí usamos una versión simplificada: escaneamos el mejor activo del snapshot.
            best_symbol = None
            best_signal = None
            for sym, df in market_snapshot.items():
                # Evaluar señal con el Edge Core (misma lógica que run_cycle pero sin efecto colateral)
                signal = self.adapter.evaluate_signal(df)
                if signal and signal["meta"] > (best_signal["meta"] if best_signal else 0):
                    best_signal = signal
                    best_symbol = sym
            if best_signal:
                # Abrir posición si no hay una abierta
                if self.adapter.state["position"] is None:
                    self.adapter.state["position"] = {
                        "symbol": best_symbol,
                        "dir": 1 if best_signal["direction"] == "LONG" else -1,
                        "entry": best_signal["entry"],
                        "atr": best_signal["atr"],
                        "size": 0.01,
                        "leverage": best_signal.get("leverage", 5),
                        "strategy": best_signal.get("strategy", ""),
                        "entry_time": time.time(),
                        "be_active": False,
                        "trail_active": False,
                        "sl": best_signal["sl"],
                        "trail_sl": best_signal["sl"],
                        "tp": best_signal["tp"]
                    }
            # Gestionar posición abierta (cierre)
            if self.adapter.state["position"] is not None:
                pos = self.adapter.state["position"]
                sym = pos["symbol"]
                df = market_snapshot.get(sym)
                if df is not None and len(df) > 0:
                    price = df["close"].iloc[-1]
                    # Llamar a HybridExit para decidir salida
                    from execution.exit_hybrid import HybridExit
                    exit_sig, reason, exit_price, updated = HybridExit.should_exit(pos, price, time.time())
                    if updated:
                        self.adapter.state["position"] = updated
                    if exit_sig:
                        d = pos["dir"]
                        pnl = ((exit_price - pos["entry"]) * d * pos["size"] * pos["leverage"] /
                               pos["entry"])
                        # Comisiones y slippage
                        fee = abs(exit_price - pos["entry"]) * pos["size"] * self.adapter.commission
                        slip = pos["entry"] * pos["size"] * self.adapter.slippage
                        pnl -= (fee + slip)
                        self.adapter.state["balance"] += pnl
                        self.adapter.state["pnl"] += pnl
                        self.adapter.state["equity"] = self.adapter.state["balance"]
                        self.adapter.state["trades"].append({
                            "time": ts, "symbol": sym,
                            "strategy": pos.get("strategy", ""),
                            "direction": "LONG" if pos["dir"] == 1 else "SHORT",
                            "entry": pos["entry"], "exit_price": exit_price,
                            "pnl": pnl, "reason": reason
                        })
                        self.adapter.state["position"] = None

            # Guardar equity en cada paso
            self.adapter.state["equity_history"].append(self.adapter.state["balance"])

        # Calcular métricas finales
        self.results = self._compute_metrics()
        print(f"Backtest completed in {time.time()-start_time:.1f}s")
        return self.results

    def _compute_metrics(self):
        eq = np.array(self.adapter.state["equity_history"])
        rets = np.diff(eq) / eq[:-1]
        sharpe = np.mean(rets) / np.std(rets) * np.sqrt(365*24) if len(rets) > 1 else 0
        maxdd = (np.maximum.accumulate(eq) - eq).max() / np.maximum.accumulate(eq).max()
        trades = self.adapter.state["trades"]
        winrate = np.mean([t["pnl"] > 0 for t in trades]) if trades else 0
        profit_factor = (sum(t["pnl"] for t in trades if t["pnl"] > 0) /
                         abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))) if trades else 0
        return {
            "sharpe": sharpe,
            "maxdd": maxdd,
            "winrate": winrate,
            "profit_factor": profit_factor,
            "trades": len(trades),
            "final_balance": self.adapter.state["balance"],
            "equity_history": self.adapter.state["equity_history"],
            "trade_list": trades
        }
