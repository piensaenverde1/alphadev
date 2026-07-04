#!/usr/bin/env python3
"""Chat con memoria persistente para el asistente local "casanostra" (Ollama).

Los modelos locales olvidan todo al cerrar la sesión. Este script añade una
memoria en un archivo de texto plano (memoria.md) que se inyecta en cada
conversación, imitando la memoria entre sesiones de los asistentes de pago.

Uso:
    python3 chat_memoria.py

Comandos dentro del chat:
    /recordar <texto>   guarda un dato en la memoria permanente
    /memoria            muestra la memoria actual
    /salir              termina la sesión
Requiere: pip install requests  (y tener `ollama serve` corriendo)
"""

import json
import sys
from pathlib import Path

import requests

MODELO = "casanostra"
URL = "http://localhost:11434/api/chat"
ARCHIVO_MEMORIA = Path(__file__).parent / "memoria.md"


def leer_memoria() -> str:
    if ARCHIVO_MEMORIA.exists():
        return ARCHIVO_MEMORIA.read_text(encoding="utf-8")
    return ""


def guardar_recuerdo(texto: str) -> None:
    with ARCHIVO_MEMORIA.open("a", encoding="utf-8") as f:
        f.write(f"- {texto}\n")


def preguntar(mensajes: list[dict]) -> str:
    """Envía la conversación a Ollama y muestra la respuesta en streaming."""
    respuesta = ""
    with requests.post(
        URL,
        json={"model": MODELO, "messages": mensajes, "stream": True},
        stream=True,
        timeout=600,
    ) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea:
                continue
            trozo = json.loads(linea)
            texto = trozo.get("message", {}).get("content", "")
            print(texto, end="", flush=True)
            respuesta += texto
    print()
    return respuesta


def main() -> None:
    memoria = leer_memoria()
    sistema = "Continúa la conversación con el usuario."
    if memoria:
        sistema += (
            "\n\nMemoria de sesiones anteriores (datos que el usuario pidió recordar):\n"
            + memoria
        )
    mensajes = [{"role": "system", "content": sistema}]

    print("Casanostra local con memoria. Escribe /salir para terminar.")
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
            print(leer_memoria() or "(memoria vacía)")
            continue
        if entrada.startswith("/recordar "):
            guardar_recuerdo(entrada[len("/recordar "):])
            print("Guardado en memoria.md")
            continue

        mensajes.append({"role": "user", "content": entrada})
        try:
            salida = preguntar(mensajes)
        except requests.ConnectionError:
            sys.exit("No se pudo conectar con Ollama. ¿Está corriendo `ollama serve`?")
        mensajes.append({"role": "assistant", "content": salida})


if __name__ == "__main__":
    main()
