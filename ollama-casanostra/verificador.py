#!/usr/bin/env python3
"""VERIFICADOR — forjador escribe código Python, se ejecuta y se corrige solo (mejora 7).

Le das una tarea de programación; forjador escribe una función y unas pruebas,
el verificador las EJECUTA en un proceso aislado, y si fallan le devuelve el
error para que se corrija. Repite hasta que pasen o se agoten los intentos.

Uso:
    python verificador.py "una función que diga si un año es bisiesto"
    python verificador.py "..." --intentos 4

Solo ejecuta código Python generado localmente por tu propio modelo, en un
proceso separado con límite de tiempo. Aun así: revisa lo que hace antes de
usarlo en algo importante.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib import request as urlreq

OLLAMA = "http://localhost:11434/api/chat"
MODELO = "forjador"
MAX_INTENTOS = 3


def limpiar(t: str) -> str:
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def extraer_codigo(texto: str) -> str:
    bloques = re.findall(r"```(?:python)?\n(.*?)```", texto, re.S)
    return bloques[0].strip() if bloques else texto.strip()


def preguntar(sistema: str, usuario: str) -> str:
    modelo = MODELO
    datos = json.dumps({"model": modelo, "stream": False, "messages": [
        {"role": "system", "content": sistema},
        {"role": "user", "content": usuario}]}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    try:
        with urlreq.urlopen(req, timeout=600) as r:
            return limpiar(json.loads(r.read())["message"]["content"])
    except OSError:
        # si no existe forjador, reintentar con casanostra
        datos2 = json.dumps({"model": "casanostra", "stream": False, "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario}]}).encode()
        req2 = urlreq.Request(OLLAMA, data=datos2, headers={"Content-Type": "application/json"})
        with urlreq.urlopen(req2, timeout=600) as r:
            return limpiar(json.loads(r.read())["message"]["content"])


def ejecutar(codigo: str) -> tuple:
    """Ejecuta el código en un proceso aislado. Devuelve (ok, salida)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prueba.py"
        p.write_text(codigo + "\nprint('__OK__')\n", encoding="utf-8")
        try:
            proc = subprocess.run([sys.executable, "-I", str(p)],
                                  capture_output=True, text=True, timeout=6, cwd=d)
        except subprocess.TimeoutExpired:
            return False, "Tiempo de ejecución excedido (posible bucle infinito)."
    if proc.returncode == 0 and "__OK__" in proc.stdout:
        return True, proc.stdout.strip()
    return False, (proc.stderr or proc.stdout).strip()[:800]


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit('Uso: python verificador.py "descripción de la función" [--intentos 3]')
    intentos = int(args[args.index("--intentos") + 1]) if "--intentos" in args else MAX_INTENTOS
    tarea = args[0]

    sistema = ("Eres un programador Python. Escribe SOLO un bloque de código en "
               "```python``` que contenga: la función pedida Y varias líneas de "
               "assert que la prueben con casos normales y límite. El código debe "
               "poder ejecutarse tal cual. No escribas explicaciones fuera del bloque.")
    usuario = f"Tarea: {tarea}"
    error_previo = ""

    for intento in range(1, intentos + 1):
        print(f"\n--- Intento {intento}/{intentos} ---")
        prompt = usuario if not error_previo else (
            f"{usuario}\n\nTu código anterior falló con este error. Corrígelo:\n{error_previo}")
        try:
            respuesta = preguntar(sistema, prompt)
        except OSError:
            sys.exit("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")
        codigo = extraer_codigo(respuesta)
        print(codigo)
        ok, salida = ejecutar(codigo)
        if ok:
            print("\n✅ El código pasa sus propias pruebas.")
            destino = Path(__file__).parent / "ultimo_codigo_verificado.py"
            destino.write_text(codigo + "\n", encoding="utf-8")
            print(f"Guardado en: {destino.name}")
            return
        print(f"\n❌ Falló: {salida}")
        error_previo = salida

    print(f"\nNo se consiguió código correcto en {intentos} intentos.")
    print("Revisa la tarea (¿está clara?) o súbela a forjador manualmente.")


if __name__ == "__main__":
    main()
