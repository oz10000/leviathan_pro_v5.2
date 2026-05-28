#!/usr/bin/env python3
"""Terminal Pydroid completa con control demo/live y monitoreo de latencia."""

import os, sys, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "leviathan_edge_core"))

from config import Config
from runtime.okx_execution_bridge import OKXExecutionBridge
from runtime.velocity_momentum_engine import VelocityMomentumEngine
from runtime.execution_latency_profiler import ExecutionLatencyProfiler
from runtime.network_diagnostics import NetworkDiagnostics

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(bridge, net, lat_prof):
    stats = lat_prof.stats()
    net_rep = net.status_report()
    print("╔══════════════════════════════════════════════╗")
    print("║      LEVIATHAN V5.2B TERMINAL PRO            ║")
    print(f"║ Modo: {Config.EXECUTION_MODE.upper():<10} Conexión: {net_rep['connection_score']:.0f}/100   ║")
    try:
        bal = bridge.get_balance()
        print(f"║ Balance USDT: {bal:.2f}                      ║")
    except:
        print("║ Balance: DESCONOCIDO                         ║")
    print(f"║ Latencia: {stats['latency_ms']:.1f}ms  Jitter: {net_rep['jitter_ms']:.1f}ms  ║")
    print("╚══════════════════════════════════════════════╝")

def main():
    bridge = OKXExecutionBridge()
    vme = VelocityMomentumEngine()
    lat_prof = ExecutionLatencyProfiler()
    net = NetworkDiagnostics()

    # Ping inicial para llenar estadísticas
    for _ in range(3):
        net.ping()
        time.sleep(0.5)

    while True:
        clear()
        print_header(bridge, net, lat_prof)
        print("\nOpciones:")
        print("1. Ranking Omega Temporal")
        print("2. Abrir orden (manual)")
        print("3. Ver posiciones")
        print("4. Cambiar modo (DEMO/LIVE)")
        print("5. Loop de monitoreo de posiciones")
        print("6. Salir")
        choice = input("Selecciona: ")

        if choice == "1":
            universe = ["BTC","ETH","SOL","SUI","INJ","LINK","AVAX","DOGE","APT","RUNE"]
            scores = vme.rank_assets(universe)
            print("\n--- OMEGA RANKING ---")
            for i, (sym, sc) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True), 1):
                print(f"{i:2d}. {sym:6s} Ω={sc:.2f}")
            input("Enter...")

        elif choice == "2":
            sym = input("Símbolo (ej. BTC): ").strip().upper()
            side = input("Lado (buy/sell): ").strip().lower()
            amount = float(input("Cantidad (contratos): ") or 0.01)
            tp = float(input("TP (0 para omitir): ") or 0)
            sl = float(input("SL (0 para omitir): ") or 0)
            t0 = time.time()
            try:
                order = bridge.place_order(sym, side, amount, tp=tp if tp>0 else None, sl=sl if sl>0 else None)
                fill_time = time.time()
                # Simulamos precio de fill (en producción obtener de la orden)
                fill_price = order.get('price', 0.0)
                lat_prof.record_order(t0, fill_time, fill_price, fill_price)
                print(f"Orden enviada. ID: {order.get('id','N/A')}")
            except Exception as e:
                print(f"Error: {e}")
            input("Enter...")

        elif choice == "3":
            try:
                positions = bridge.get_positions()
                for p in positions:
                    if float(p.get('notional',0)) > 0:
                        print(f"{p['symbol']} {p['side']} {p['notional']} USDT PnL: {p['unrealizedPnl']}")
            except Exception as e:
                print(f"Error: {e}")
            input("Enter...")

        elif choice == "4":
            current = Config.EXECUTION_MODE
            Config.EXECUTION_MODE = "live" if current == "demo" else "demo"
            bridge = OKXExecutionBridge()  # reconectar con nuevas credenciales/modo
            print(f"Modo cambiado a: {Config.EXECUTION_MODE}")
            input("Enter...")

        elif choice == "5":
            print("Monitoreando posiciones (Ctrl+C para salir)...")
            try:
                while True:
                    positions = bridge.get_positions()
                    for p in positions:
                        if float(p.get('notional',0)) > 0:
                            # Aquí se podrían ajustar trailing stops automáticos
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {p['symbol']} {p['side']} PnL: {p['unrealizedPnl']:.2f}")
                    time.sleep(10)
            except KeyboardInterrupt:
                print("\nMonitoreo detenido.")
            input("Enter...")

        elif choice == "6":
            break
        else:
            print("Opción inválida")
            time.sleep(1)

if __name__ == "__main__":
    main()
