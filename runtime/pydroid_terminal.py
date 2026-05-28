#!/usr/bin/env python3
"""
Consola ASCII para Leviathan V5.2B en Pydroid.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "leviathan_edge_core"))

from config import Config
from execution.okx_api_connector import OKXConnector
from runtime.velocity_momentum_engine import VelocityMomentumEngine
from runtime.pnl_tracker import PnLTracker


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(conn):
    print("╔══════════════════════════════════════════╗")
    print("║   LEVIATHAN V5.2B — VELOCITY-MOMENTUM    ║")
    print("║        PYDROID TERMINAL v1.0             ║")
    print("╠══════════════════════════════════════════╣")
    mode = Config.EXECUTION_MODE.upper()
    print(f"║ Exchange: OKX {mode:<10}                ║")
    try:
        bal = conn.get_balance()
        print(f"║ Balance:  {bal:.2f} USDT                  ║")
    except Exception:
        print("║ Balance:  DESCONOCIDO                  ║")
    print("╚══════════════════════════════════════════╝")


def main():
    conn = OKXConnector()
    vme = VelocityMomentumEngine()
    pnl_tracker = PnLTracker()

    while True:
        clear()
        print_header(conn)
        print("\nOpciones:")
        print("1. Ranking Omega Temporal (Top Activos)")
        print("2. Abrir orden de mercado (manual)")
        print("3. Ver posiciones abiertas")
        print("4. Iniciar loop automático")
        print("5. Salir")
        choice = input("Selecciona: ")

        if choice == "1":
            universe = ["BTC", "ETH", "SOL", "SUI", "INJ", "LINK", "AVAX", "DOGE", "APT", "RUNE"]
            scores = vme.rank_assets(universe)
            print("\n--- OMEGA TEMPORAL RANKING ---")
            for i, (sym, sc) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True), 1):
                print(f"{i:2d}. {sym:6s} Ω={sc:.2f}")
            input("\nEnter para continuar...")

        elif choice == "2":
            sym = input("Símbolo (ej. BTC): ").strip().upper()
            side = input("Lado (buy/sell): ").strip().lower()
            amount = float(input("Cantidad (contratos): ") or 0.01)
            tp = float(input("TP (0 para omitir): ") or 0)
            sl = float(input("SL (0 para omitir): ") or 0)
            resp = conn.place_order(sym, side, amount, "long" if side == "buy" else "short",
                                    tp=tp if tp > 0 else None, sl=sl if sl > 0 else None)
            print(f"Respuesta: {resp}")
            input("Enter para continuar...")

        elif choice == "3":
            try:
                positions = conn.get_positions()
                if positions.get("code") == "0":
                    for p in positions["data"]:
                        if float(p.get("notionalUsd", 0)) > 0:
                            print(f"{p['instId']} {p['posSide']} {p['notionalUsd']} USDT")
                else:
                    print("Sin posiciones abiertas.")
            except Exception as e:
                print(f"Error: {e}")
            input("Enter para continuar...")

        elif choice == "4":
            print("Loop automático iniciado... (Ctrl+C para detener)")
            try:
                while True:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo completado.")
                    time.sleep(30)
            except KeyboardInterrupt:
                print("\nLoop detenido.")
            input("Enter para continuar...")

        elif choice == "5":
            break
        else:
            print("Opción inválida")
            time.sleep(1)


if __name__ == "__main__":
    main()
