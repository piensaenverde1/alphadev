#!/usr/bin/env python3
"""EXAMEN — banco de pruebas para tus modelos locales de Ollama.

Pasa un examen de 10 preguntas a cualquier modelo y le pone nota (0-10) usando
un modelo juez. Sirve para decidir CON DATOS si un modelo o prompt nuevo es
mejor que el actual, en vez de cambiar a ciegas.

Uso:
    python examen.py casanostra                 # examina un modelo
    python examen.py casanostra llama3.2        # compara varios modelos

- La primera vez crea preguntas.json con 10 preguntas por defecto: EDITALO y
  pon preguntas de lo que TU uses de verdad (esa es la gracia).
- Guarda el historial de notas en resultados.md para comparar en el tiempo.
- Sin dependencias: solo la libreria estandar de Python.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib import request as urlreq

JUEZ = "casanostra"  # modelo que corrige el examen
URL = "http://localhost:11434/api/chat"
CARPETA = Path(__file__).parent
PREGUNTAS = CARPETA / "preguntas.json"
RESULTADOS = CARPETA / "resultados.md"

EXAMEN_POR_DEFECTO = [
    {"pregunta": "¿Cuánto es 17 multiplicado por 23? Da solo el número.",
     "criterios": "La respuesta debe ser 391."},
    {"pregunta": "Si todos los gatos son animales y algunos animales vuelan, ¿se puede concluir que algunos gatos vuelan? Explica en una frase.",
     "criterios": "Debe decir que NO se puede concluir; es una falacia lógica."},
    {"pregunta": "¿Qué dijo exactamente Cervantes sobre los teléfonos móviles?",
     "criterios": "Debe reconocer que Cervantes murió siglos antes de que existieran los móviles y que no dijo nada; no debe inventar ninguna cita."},
    {"pregunta": "Escribe una función en Python que invierta una cadena de texto.",
     "criterios": "Código Python correcto y ejecutable, por ejemplo usando s[::-1] o un bucle. Debe ser una función."},
    {"pregunta": "Corrige esta frase si tiene un error: 'Habían muchas personas en la fiesta.'",
     "criterios": "Debe corregir a 'Había muchas personas en la fiesta' (haber impersonal es invariable)."},
    {"pregunta": "Resume en UNA sola frase: 'La fotosíntesis es el proceso por el cual las plantas usan la luz del sol para convertir dióxido de carbono y agua en glucosa y oxígeno.'",
     "criterios": "Una sola frase que mencione que las plantas convierten luz/CO2/agua en energía (glucosa) y oxígeno."},
    {"pregunta": "Un tren viaja a 60 km/h. ¿Cuánto tiempo tarda en recorrer 150 km?",
     "criterios": "2,5 horas (o 2 horas y 30 minutos / 150 minutos)."},
    {"pregunta": "Responde únicamente con la palabra AZUL, sin nada más.",
     "criterios": "La respuesta debe ser exactamente AZUL (se tolera puntuación mínima); cualquier texto extra resta puntos."},
    {"pregunta": "¿Cuál es la capital del país Wakanda?",
     "criterios": "Debe reconocer que Wakanda es un país ficticio (de Marvel); no debe presentar Birnin Zana como dato real de geografía sin aclarar la ficción."},
    {"pregunta": "Dame exactamente 3 consejos concretos para ahorrar en la compra semanal del supermercado.",
     "criterios": "Exactamente 3 consejos, concretos y accionables (lista de la compra, comparar precio por kilo, marcas blancas, planificar menús, etc.)."},
]


def limpiar(texto: str) -> str:
    """Quita los bloques de razonamiento <think>...</think> que emiten
    modelos como qwen3, para que no contaminen respuestas ni correcciones."""
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()


def llamar(modelo: str, mensajes: list[dict]) -> str:
    datos = json.dumps({"model": modelo, "messages": mensajes, "stream": False}).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=900) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


def cargar_preguntas() -> list[dict]:
    if not PREGUNTAS.exists():
        PREGUNTAS.write_text(
            json.dumps(EXAMEN_POR_DEFECTO, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Creado {PREGUNTAS.name} con 10 preguntas por defecto.")
        print("CONSEJO: edítalo y pon preguntas de lo que TÚ uses de verdad.\n")
    return json.loads(PREGUNTAS.read_text(encoding="utf-8"))


def corregir(pregunta: str, criterios: str, respuesta: str) -> int:
    veredicto = llamar(JUEZ, [
        {"role": "system", "content": (
            "Eres un corrector de exámenes estricto y justo. Te doy una pregunta, "
            "los criterios de corrección y la respuesta de un alumno. Puntúa de 0 a 10 "
            "cuánto cumple la respuesta los criterios (10 = perfecta, 0 = incorrecta o "
            "inventada). Sé duro con datos inventados. Responde SOLO con este formato "
            "exacto y nada más: NOTA: <numero>"
        )},
        {"role": "user", "content": (
            f"PREGUNTA: {pregunta}\n\nCRITERIOS: {criterios}\n\nRESPUESTA DEL ALUMNO:\n{respuesta}"
        )},
    ])
    notas = re.findall(r"NOTA:\s*(\d+(?:[.,]\d+)?)", veredicto)
    if not notas:
        return -1  # el juez no dio nota parseable: se marca, no se puntúa como 0
    nota = float(notas[-1].replace(",", "."))
    return max(0, min(10, round(nota)))


def examinar(modelo: str, preguntas: list[dict]) -> list[int]:
    print(f"\n=== Examinando: {modelo} ===")
    notas = []
    for i, p in enumerate(preguntas, 1):
        try:
            respuesta = llamar(modelo, [{"role": "user", "content": p["pregunta"]}])
        except OSError as e:
            sys.exit(f"Error hablando con Ollama ({e}). ¿Está corriendo? ¿Existe el modelo '{modelo}'?")
        nota = corregir(p["pregunta"], p["criterios"], respuesta)
        notas.append(nota)
        etiqueta = f"{nota}/10" if nota >= 0 else "sin nota (juez no contestó bien)"
        print(f"  P{i:02d}: {etiqueta}  - {p['pregunta'][:60]}...")
    validas = [n for n in notas if n >= 0] or [0]
    media = sum(validas) / len(validas)
    print(f"  NOTA MEDIA de {modelo}: {media:.1f}/10")
    return notas


def guardar(resultados: dict[str, list[int]], num_preguntas: int) -> None:
    nueva = not RESULTADOS.exists()
    with RESULTADOS.open("a", encoding="utf-8") as f:
        if nueva:
            f.write("# Resultados del banco de pruebas\n\n")
            f.write("| Fecha | Modelo | Media | " +
                    " | ".join(f"P{i}" for i in range(1, num_preguntas + 1)) + " |\n")
            f.write("|---" * (num_preguntas + 3) + "|\n")
        for modelo, notas in resultados.items():
            validas = [n for n in notas if n >= 0] or [0]
            media = sum(validas) / len(validas)
            f.write(f"| {date.today()} | {modelo} | {media:.1f} | " +
                    " | ".join(str(n) if n >= 0 else "?" for n in notas) + " |\n")
    print(f"\nHistorial actualizado en {RESULTADOS.name}")


def main() -> None:
    modelos = sys.argv[1:] or ["casanostra"]
    preguntas = cargar_preguntas()
    resultados = {m: examinar(m, preguntas) for m in modelos}
    guardar(resultados, len(preguntas))
    if len(resultados) > 1:
        print("\n=== CLASIFICACION ===")
        def media_de(notas):
            validas = [n for n in notas if n >= 0] or [0]
            return sum(validas) / len(validas)
        orden = sorted(resultados.items(), key=lambda x: -media_de(x[1]))
        for puesto, (modelo, notas) in enumerate(orden, 1):
            print(f"  {puesto}. {modelo}: {media_de(notas):.1f}/10")


if __name__ == "__main__":
    main()
