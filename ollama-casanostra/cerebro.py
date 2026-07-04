#!/usr/bin/env python3
"""CEREBRO — agente autónomo local que se mejora a sí mismo creando habilidades.

Le das un objetivo ("quiero aprender inversión en índices", "mejora mi forma de
escribir emails") y el agente, de forma autónoma y 100% gratuita/local:

  1. ESTRATEGA  analiza el objetivo y decide qué equipo de especialistas crear.
  2. ALQUIMISTA escribe el prompt de sistema de cada especialista (genera
     prompts automáticamente — esto es el "código que genera prompts").
  3. EQUIPO     cada especialista trabaja su parte de la misión.
  4. CRÍTICO    revisa el resultado; si no aprueba, el equipo itera (máx. 3).
  5. Guarda el informe final y un Modelfile por especialista en
     habilidades_generadas/, listos para instalar con `ollama create`.

Uso:
    python3 cerebro.py "tu objetivo aquí"
    python3 cerebro.py            # te lo pregunta

Requiere: `ollama serve` corriendo y `pip install requests`.
Seguridad: este agente solo genera TEXTO (prompts, planes, código como texto).
Nunca ejecuta código ni comandos por sí mismo — tú revisas y decides.
"""

import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import requests

MODELO = "casanostra"           # cámbialo por tu modelo si usas otro
URL = "http://localhost:11434/api/chat"
MAX_ITERACIONES = 3
MAX_ESPECIALISTAS = 3
CARPETA_SALIDA = Path(__file__).parent / "habilidades_generadas"


def llamar(sistema: str, usuario: str) -> str:
    """Una llamada al modelo local con un rol de sistema dado."""
    r = requests.post(
        URL,
        json={
            "model": MODELO,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
            "stream": False,
        },
        timeout=900,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:40] or "habilidad"


# ---------------------------------------------------------------- roles fijos

ESTRATEGA = """Eres ESTRATEGA, el coordinador de un equipo de agentes de IA.
Dado un objetivo del usuario, decide el equipo mínimo necesario (1 a 3
especialistas, nunca más). Responde EXACTAMENTE en este formato, una línea por
especialista y nada más:

ESPECIALISTA: <nombre corto de una palabra> | <su misión concreta en una frase>

Elige especialistas complementarios, no redundantes."""

ALQUIMISTA = """Eres ALQUIMISTA, ingeniero de prompts. Te doy el nombre y la
misión de un especialista. Escribe SOLO su prompt de sistema (sin explicaciones
alrededor): identidad en una frase, proceso en pasos numerados, 4 reglas
concretas y verificables, formato de salida, y la obligación de admitir
incertidumbre en vez de inventar. En el idioma de la misión."""

CRITICO = """Eres CRÍTICO, revisor implacable pero justo. Te doy un objetivo y
el trabajo de un equipo. Evalúa si el trabajo cumple el objetivo.
Primera línea EXACTA: "VEREDICTO: APROBADO" o "VEREDICTO: MEJORAR".
Si es MEJORAR, añade una lista numerada de mejoras concretas y accionables
(máximo 5). No propongas mejoras cosméticas."""


# ---------------------------------------------------------------- flujo

def main() -> None:
    objetivo = " ".join(sys.argv[1:]).strip() or input("¿Cuál es tu objetivo? ").strip()
    if not objetivo:
        sys.exit("Necesito un objetivo.")

    print(f"\n🧠 CEREBRO trabajando en: {objetivo}\n")

    # 1. El estratega diseña el equipo
    print("1/4 ESTRATEGA diseñando el equipo...")
    plan = llamar(ESTRATEGA, f"Objetivo del usuario: {objetivo}")
    equipo = re.findall(r"ESPECIALISTA:\s*([^|]+)\|\s*(.+)", plan)[:MAX_ESPECIALISTAS]
    if not equipo:
        equipo = [("generalista", f"Resolver de la mejor forma posible: {objetivo}")]
    for nombre, mision in equipo:
        print(f"   → {nombre.strip()}: {mision.strip()}")

    # 2. El alquimista genera automáticamente el prompt de cada especialista
    print("\n2/4 ALQUIMISTA generando los prompts del equipo...")
    prompts = {}
    for nombre, mision in equipo:
        nombre = nombre.strip()
        prompts[nombre] = llamar(
            ALQUIMISTA, f"Especialista: {nombre}\nMisión: {mision.strip()}"
        )
        print(f"   → prompt de {nombre} listo")

    # 3-4. El equipo trabaja y el crítico revisa (bucle autónomo acotado)
    critica = ""
    trabajo = ""
    for iteracion in range(1, MAX_ITERACIONES + 1):
        print(f"\n3/4 EQUIPO trabajando (iteración {iteracion})...")
        resultados = []
        for nombre, mision in equipo:
            nombre = nombre.strip()
            encargo = f"Objetivo global: {objetivo}\nTu misión: {mision.strip()}"
            if critica:
                encargo += f"\n\nMejoras exigidas por el revisor:\n{critica}"
            resultados.append(f"## Aporte de {nombre}\n\n{llamar(prompts[nombre], encargo)}")
        trabajo = "\n\n".join(resultados)

        print("4/4 CRÍTICO revisando...")
        veredicto = llamar(CRITICO, f"Objetivo: {objetivo}\n\nTrabajo del equipo:\n{trabajo}")
        if veredicto.upper().startswith("VEREDICTO: APROBADO"):
            print("   ✅ Aprobado.")
            break
        critica = veredicto.partition("\n")[2].strip()
        print("   🔁 El crítico pide mejoras; el equipo itera.")

    # 5. Guardar informe + habilidades instalables
    carpeta = CARPETA_SALIDA / f"{date.today()}-{slug(objetivo)}"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "informe.md").write_text(
        f"# Objetivo\n\n{objetivo}\n\n# Resultado del equipo\n\n{trabajo}\n",
        encoding="utf-8",
    )
    for nombre in prompts:
        modelfile = (
            f"FROM {MODELO}\n"
            "PARAMETER num_ctx 16384\n"
            "PARAMETER temperature 0.6\n\n"
            f'SYSTEM """{prompts[nombre]}"""\n'
        )
        (carpeta / f"{slug(nombre)}.Modelfile").write_text(modelfile, encoding="utf-8")

    print(f"\n📁 Todo guardado en: {carpeta}")
    print("   - informe.md            → el resultado del trabajo")
    print("   - *.Modelfile           → habilidades nuevas generadas automáticamente")
    print("\nPara instalar una habilidad generada:")
    print(f"   ollama create <nombre> -f {carpeta}/<nombre>.Modelfile")


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectionError:
        sys.exit("No se pudo conectar con Ollama. ¿Está corriendo `ollama serve`?")
