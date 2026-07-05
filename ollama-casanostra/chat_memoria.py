#!/usr/bin/env python3
"""Chat con memoria persistente y AUTOMÁTICA para casanostra.

- /recordar <texto>  guarda un dato a mano
- /memoria           muestra la memoria actual
- /salir             termina la sesión
- Al salir, el propio modelo resume la conversación y guarda lo importante
  en memoria.md sin que tengas que hacer nada (memoria automática).

Sin dependencias: solo la librería estándar de Python.
"""

import json
import sys
from datetime import date
from pathlib import Path
from urllib import request as urlreq

MODELO = "casanostra"
URL = "http://localhost:11434/api/chat"
ARCHIVO = Path(__file__).parent / "memoria.md"


def leer() -> str:
    return ARCHIVO.read_text(encoding="utf-8") if ARCHIVO.exists() else ""


def anotar(texto: str) -> None:
    with ARCHIVO.open("a", encoding="utf-8") as f:
        f.write(texto.rstrip() + "\n")


def preguntar(mensajes: list[dict], stream: bool = True) -> str:
    datos = json.dumps({"model": MODELO, "messages": mensajes, "stream": stream}).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    if not stream:
        with urlreq.urlopen(req, timeout=600) as r:
            return json.loads(r.read())["message"]["content"].strip()
    respuesta = ""
    with urlreq.urlopen(req, timeout=600) as r:
        for linea in r:
            if not linea.strip():
                continue
            texto = json.loads(linea).get("message", {}).get("content", "")
            print(texto, end="", flush=True)
            respuesta += texto
    print()
    return respuesta


def resumen_automatico(mensajes: list[dict]) -> None:
    """Memoria automática: al salir, el modelo resume la sesión y la guarda."""
    charla = [m for m in mensajes if m["role"] != "system"]
    if len(charla) < 2:
        return
    print("\nGuardando memoria automática...")
    transcripcion = "\n".join(f"{m['role']}: {m['content']}" for m in charla)
    resumen = preguntar(
        [
            {
                "role": "system",
                "content": (
                    "Resume esta conversación en un máximo de 5 viñetas con SOLO "
                    "los datos útiles para el futuro: decisiones tomadas, datos "
                    "personales o del proyecto, tareas pendientes y preferencias "
                    "del usuario. Si no hay nada que valga la pena recordar, "
                    "responde exactamente NADA."
                ),
            },
            {"role": "user", "content": transcripcion[-8000:]},
        ],
        stream=False,
    )
    if resumen.upper().strip() != "NADA":
        anotar(f"\n## Sesión {date.today()}\n{resumen}")
        print(f"Memoria guardada en {ARCHIVO}")


def main() -> None:
    sistema = "Continúa la conversación con el usuario."
    memoria = leer()
    if memoria:
        sistema += "\n\nMemoria de sesiones anteriores:\n" + memoria
    mensajes = [{"role": "system", "content": sistema}]
    print("Casanostra con memoria automática. /recordar <dato>, /memoria, /salir")
    try:
        while True:
            try:
                entrada = input("\nTú> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not entrada:
                continue
            if entrada == "/salir":
                break
            if entrada == "/memoria":
                print(leer() or "(vacía)")
                continue
            if entrada.startswith("/recordar "):
                anotar(f"- {entrada[len('/recordar '):]}")
                print("Guardado.")
                continue
            mensajes.append({"role": "user", "content": entrada})
            try:
                salida = preguntar(mensajes)
            except OSError:
                sys.exit("No conecto con Ollama. ¿Está corriendo `ollama serve`?")
            mensajes.append({"role": "assistant", "content": salida})
    finally:
        try:
            resumen_automatico(mensajes)
        except OSError:
            pass


if __name__ == "__main__":
    main()
