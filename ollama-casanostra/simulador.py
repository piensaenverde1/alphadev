#!/usr/bin/env python3
"""SIMULADOR — cartera de inversión EN PAPEL (mejora 6).

Prueba si las señales del sistema (o tuyas) baten al índice, SIN dinero real.
Tú registras señales de compra/venta con el precio del día (que tú miras en tu
broker); el simulador lleva la cuenta y compara tu cartera contra un índice de
referencia que también registras. Regla del catedrático: si en 6-12 meses no
bate al índice, conectar dinero real habría sido regalarlo.

Uso:
    python simulador.py comprar AAPL 10 190.50      # 10 "acciones" a 190.50
    python simulador.py vender AAPL 5 205.00
    python simulador.py indice 5200                 # anota el valor del índice hoy
    python simulador.py precio AAPL 210.00          # actualiza precio para valorar
    python simulador.py estado                      # cartera vs índice
    python simulador.py historial

Todo se guarda en cartera_papel.json. Educativo, no asesoramiento.
"""

import json
import sys
from datetime import date
from pathlib import Path

ARCHIVO = Path(__file__).parent / "cartera_papel.json"
CAPITAL_INICIAL = 1000.0  # capital virtual de partida


def cargar() -> dict:
    if ARCHIVO.exists():
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    return {"efectivo": CAPITAL_INICIAL, "posiciones": {}, "precios": {},
            "indice": [], "historial": []}


def guardar(d: dict) -> None:
    ARCHIVO.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar(d: dict, texto: str) -> None:
    d["historial"].append(f"{date.today()} | {texto}")


def valor_cartera(d: dict) -> float:
    valor = d["efectivo"]
    for tk, cant in d["posiciones"].items():
        valor += cant * d["precios"].get(tk, 0.0)
    return valor


def comprar(d, tk, cant, precio):
    coste = cant * precio
    if coste > d["efectivo"]:
        print(f"Efectivo insuficiente: necesitas {coste:.2f}€, tienes {d['efectivo']:.2f}€.")
        return
    d["efectivo"] -= coste
    d["posiciones"][tk] = d["posiciones"].get(tk, 0) + cant
    d["precios"][tk] = precio
    registrar(d, f"COMPRA {cant} {tk} a {precio} = {coste:.2f}€")
    print(f"Comprado. Efectivo restante: {d['efectivo']:.2f}€")


def vender(d, tk, cant, precio):
    if d["posiciones"].get(tk, 0) < cant:
        print(f"No tienes {cant} de {tk} (tienes {d['posiciones'].get(tk,0)}).")
        return
    d["efectivo"] += cant * precio
    d["posiciones"][tk] -= cant
    if d["posiciones"][tk] == 0:
        del d["posiciones"][tk]
    d["precios"][tk] = precio
    registrar(d, f"VENTA {cant} {tk} a {precio} = {cant*precio:.2f}€")
    print(f"Vendido. Efectivo: {d['efectivo']:.2f}€")


def estado(d):
    valor = valor_cartera(d)
    rent = 100 * (valor - CAPITAL_INICIAL) / CAPITAL_INICIAL
    print(f"\n=== CARTERA EN PAPEL ({date.today()}) ===")
    print(f"Capital inicial: {CAPITAL_INICIAL:.2f}€")
    print(f"Valor actual:    {valor:.2f}€  ({rent:+.2f}%)")
    print(f"Efectivo:        {d['efectivo']:.2f}€")
    if d["posiciones"]:
        print("Posiciones:")
        for tk, cant in d["posiciones"].items():
            print(f"  {tk}: {cant} x {d['precios'].get(tk,0):.2f}€ = {cant*d['precios'].get(tk,0):.2f}€")
    else:
        print("Sin posiciones abiertas.")
    # Comparación con el índice
    if len(d["indice"]) >= 2:
        i0, i1 = d["indice"][0]["valor"], d["indice"][-1]["valor"]
        rent_indice = 100 * (i1 - i0) / i0
        print(f"\nÍndice de referencia: {rent_indice:+.2f}% en el mismo periodo")
        diff = rent - rent_indice
        veredicto = "BATES al índice ✓" if diff > 0 else "por DEBAJO del índice ✗"
        print(f"Tu cartera: {diff:+.2f} puntos respecto al índice -> {veredicto}")
        if diff <= 0:
            print("Recuerda: la mayoría no bate al índice. Si esto persiste,")
            print("la lección es que la estrategia pasiva (indexado) gana.")
    else:
        print("\n(Registra el índice al menos dos veces para comparar: python simulador.py indice <valor>)")


def main():
    d = cargar()
    args = sys.argv[1:]
    if not args or args[0] == "estado":
        estado(d)
    elif args[0] == "comprar" and len(args) == 4:
        comprar(d, args[1].upper(), float(args[2]), float(args[3])); guardar(d)
    elif args[0] == "vender" and len(args) == 4:
        vender(d, args[1].upper(), float(args[2]), float(args[3])); guardar(d)
    elif args[0] == "precio" and len(args) == 3:
        d["precios"][args[1].upper()] = float(args[2]); guardar(d)
        print(f"Precio de {args[1].upper()} actualizado a {args[2]}€")
    elif args[0] == "indice" and len(args) == 2:
        d["indice"].append({"fecha": str(date.today()), "valor": float(args[1])})
        guardar(d); print(f"Índice registrado: {args[1]} ({date.today()})")
    elif args[0] == "historial":
        for h in d["historial"]:
            print(h)
        if not d["historial"]:
            print("Sin operaciones todavía.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
