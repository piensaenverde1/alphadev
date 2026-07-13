#!/usr/bin/env python3
"""NUCLEO — funciones compartidas para hablar con Ollama (mejora 1).

Módulo opcional: si está presente en la carpeta, los demás programas pueden
importarlo para no repetir el código de conexión. Los programas del sistema
siguen funcionando SIN este archivo (traen su propia copia mínima), para que
la descarga suelta con Invoke-WebRequest nunca se rompa.

Uso desde otro programa:
    from nucleo import preguntar, limpiar, hay_internet
"""

import json
import re
from urllib import request as urlreq

OLLAMA = "http://localhost:11434"


def limpiar(texto: str) -> str:
    """Quita el razonamiento interno <think>...</think> de modelos como qwen3."""
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()


def preguntar(modelo: str, mensajes: list, timeout: int = 900) -> str:
    """Envía una conversación al modelo y devuelve su respuesta ya limpia."""
    datos = json.dumps({"model": modelo, "stream": False, "messages": mensajes}).encode()
    req = urlreq.Request(OLLAMA + "/api/chat", data=datos,
                         headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=timeout) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


def preguntar_simple(modelo: str, texto: str, sistema: str = "") -> str:
    """Atajo para una sola pregunta con prompt de sistema opcional."""
    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.append({"role": "user", "content": texto})
    return preguntar(modelo, mensajes)


def modelos_instalados() -> list:
    """Lista de nombres de modelos disponibles en Ollama."""
    with urlreq.urlopen(OLLAMA + "/api/tags", timeout=10) as r:
        return [m["name"] for m in json.loads(r.read()).get("models", [])]


def hay_internet() -> bool:
    """True si se alcanza un host público en pocos segundos."""
    for url in ("https://duckduckgo.com", "https://www.google.com"):
        try:
            urlreq.urlopen(url, timeout=4)
            return True
        except OSError:
            continue
    return False


if __name__ == "__main__":
    # Prueba rápida del núcleo
    try:
        print("Modelos instalados:", ", ".join(modelos_instalados()) or "(ninguno)")
        print("¿Hay internet?:", "sí" if hay_internet() else "no")
    except OSError:
        print("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")
