#!/usr/bin/env python3
"""DEBATE — dos especialistas debaten y dan una conclusión conjunta (mejora 10).

Pones un tema y dos habilidades (por defecto cazador y valorador); cada uno da
su postura, ve la del otro y responde, y un tercero (moderador) sintetiza una
conclusión equilibrada. Útil para decisiones donde chocan dos criterios.

Uso:
    python debate.py "¿debería invertir en esta empresa pequeña?"
    python debate.py "..." --a cazador --b inversor --rondas 2

Sin dependencias externas.
"""

import json
import re
import sys
from urllib import request as urlreq

OLLAMA = "http://localhost:11434/api/chat"


def limpiar(t: str) -> str:
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def preguntar(modelo: str, sistema: str, usuario: str) -> str:
    datos = json.dumps({"model": modelo, "stream": False, "messages": [
        {"role": "system", "content": sistema},
        {"role": "user", "content": usuario}]}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=900) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


def existe(modelo: str) -> bool:
    try:
        with urlreq.urlopen("http://localhost:11434/api/tags", timeout=10) as r:
            nombres = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return any(n.startswith(modelo) for n in nombres)
    except OSError:
        return False


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit('Uso: python debate.py "tu pregunta" [--a cazador --b valorador --rondas 2]')
    def opt(nombre, defecto):
        return args[args.index(nombre) + 1] if nombre in args else defecto
    a = opt("--a", "cazador")
    b = opt("--b", "valorador")
    rondas = int(opt("--rondas", "2"))
    tema = args[0]

    for m in (a, b):
        if not existe(m):
            sys.exit(f"El modelo '{m}' no existe. Créalo o usa otro (ver GUIA.md).")

    print(f"DEBATE sobre: {tema}\nParticipantes: {a} vs {b} | {rondas} rondas\n")
    sistema = ("Participas en un debate razonado para ayudar al usuario a decidir. "
               "Da tu postura con argumentos concretos desde tu especialidad. Sé breve "
               "(máx. 6 frases). Si el otro tiene razón en algo, reconócelo. No inventes datos.")

    transcripcion = []
    ultima_b = "(aún no ha hablado)"
    try:
        for i in range(1, rondas + 1):
            print(f"--- Ronda {i} ---")
            ua = (f"Tema: {tema}\n\nPostura anterior de {b}: {ultima_b}\n\n"
                  f"Da tu postura como {a}.")
            resp_a = preguntar(a, sistema, ua)
            print(f"\n[{a.upper()}]\n{resp_a}\n")
            transcripcion.append(f"{a}: {resp_a}")

            ub = (f"Tema: {tema}\n\nPostura de {a}: {resp_a}\n\n"
                  f"Responde con tu postura como {b}.")
            ultima_b = preguntar(b, sistema, ub)
            print(f"[{b.upper()}]\n{ultima_b}\n")
            transcripcion.append(f"{b}: {ultima_b}")

        print("--- CONCLUSIÓN DEL MODERADOR ---")
        moderador = ("Eres un moderador imparcial. Resume el debate en: (1) puntos de "
                     "acuerdo, (2) diferencias reales, (3) una recomendación equilibrada "
                     "para el usuario dejando claro que la decisión es suya. Sé conciso.")
        conclusion = preguntar("casanostra", moderador,
                               f"Tema: {tema}\n\nDebate:\n" + "\n\n".join(transcripcion))
        print(f"\n{conclusion}")
    except OSError:
        sys.exit("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")


if __name__ == "__main__":
    main()
