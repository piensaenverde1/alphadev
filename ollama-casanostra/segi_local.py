#!/usr/bin/env python3
"""SEGI-LOCAL — ejecuta el Súper Examen SEGI contra un modelo local de Ollama.

Hace automático lo que SEGI dejaba manual:
  1. Le pregunta cada cuestión al modelo evaluado (por defecto casanostra),
     manteniendo la conversación en las preguntas de MEMORIA (Q034-Q036).
  2. Autocorrige código, JSON y exactas con el motor original de SEGI.
  3. Puntúa las preguntas de rúbrica con un modelo-juez (criterio a criterio).
  4. Imprime el informe por categorías y guarda las respuestas y el resultado.

Uso:
    python segi_local.py                         # evalúa casanostra, juez casanostra
    python segi_local.py --modelo casanostra --juez llama3.2
    python segi_local.py --solo Q011,Q034,Q035,Q036   # solo algunas preguntas
    python segi_local.py --rapido                # subconjunto representativo

Requiere: Ollama corriendo y segi_super_examen.py en la misma carpeta.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib import request as urlreq

import segi_super_examen as segi

OLLAMA = "http://localhost:11434/api/chat"
CARPETA = Path(__file__).parent
# Subconjunto representativo para una pasada rápida (una por área grande)
RAPIDO = ["Q001", "Q004", "Q008", "Q011", "Q012", "Q018", "Q020", "Q021",
          "Q027", "Q034", "Q035", "Q036", "Q037", "Q039"]


def limpiar(texto: str) -> str:
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()


def preguntar(modelo: str, mensajes: list) -> str:
    datos = json.dumps({"model": modelo, "stream": False, "messages": mensajes}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=900) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


def recoger_respuestas(modelo: str, preguntas: list) -> dict:
    """Pregunta cada cuestión al modelo. Las de MEMORIA comparten conversación."""
    respuestas = {}
    conversacion_memoria = []  # contexto compartido solo para la categoría Memoria
    for q in preguntas:
        print(f"  {q.id} ({q.category})... ", end="", flush=True)
        try:
            if q.category == "Memoria":
                conversacion_memoria.append({"role": "user", "content": q.prompt})
                salida = preguntar(modelo, conversacion_memoria)
                conversacion_memoria.append({"role": "assistant", "content": salida})
            else:
                salida = preguntar(modelo, [{"role": "user", "content": q.prompt}])
        except OSError as e:
            sys.exit(f"\nError con Ollama ({e}). ¿Corre 'ollama serve'? ¿Existe el modelo '{modelo}'?")
        respuestas[q.id] = salida
        print("ok")
    return respuestas


def puntuar_rubrica(juez: str, q, respuesta: str) -> tuple:
    """Un modelo-juez puntúa cada criterio de la rúbrica: 0, 0.5 o 1."""
    criterios = "\n".join(f"{i+1}. {c}" for i, c in enumerate(q.rubric))
    sistema = (
        "Eres un corrector estricto y justo. Te doy una pregunta, una lista de "
        "criterios y la respuesta de un alumno. Para CADA criterio decide si la "
        "respuesta lo cumple: 1 (sí), 0.5 (parcial) o 0 (no). Sé duro con datos "
        "inventados. Responde SOLO con un array JSON de números, uno por criterio, "
        "en orden, sin texto adicional. Ejemplo para 3 criterios: [1, 0.5, 0]"
    )
    usuario = (f"PREGUNTA:\n{q.prompt}\n\nCRITERIOS:\n{criterios}\n\n"
               f"RESPUESTA DEL ALUMNO:\n{respuesta}")
    try:
        veredicto = preguntar(juez, [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario}])
    except OSError:
        return -1.0, "juez no disponible"
    m = re.search(r"\[[^\]]*\]", veredicto)
    if not m:
        return -1.0, "el juez no devolvió notas parseables"
    try:
        notas = json.loads(m.group())
    except json.JSONDecodeError:
        return -1.0, "el juez devolvió un array inválido"
    # Ajustar a la longitud de la rúbrica y limitar a {0, 0.5, 1}
    notas = [max(0.0, min(1.0, float(n))) for n in notas][:len(q.rubric)]
    while len(notas) < len(q.rubric):
        notas.append(0.0)
    ratio = sum(notas) / len(notas) if notas else 0.0
    return ratio * q.max_points, f"Rúbrica juez: {sum(notas):.1f}/{len(notas)}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Ejecuta SEGI contra un modelo local")
    ap.add_argument("--modelo", default="casanostra", help="modelo evaluado")
    ap.add_argument("--juez", default="casanostra", help="modelo que corrige las rúbricas")
    ap.add_argument("--solo", default="", help="IDs separados por comas (ej: Q001,Q011)")
    ap.add_argument("--rapido", action="store_true", help="subconjunto representativo")
    ap.add_argument("--salida", type=Path, default=CARPETA / "resultado_segi_local.json")
    args = ap.parse_args()

    todas = segi.build_exam()
    if args.solo:
        ids = {x.strip() for x in args.solo.split(",")}
        preguntas = [q for q in todas if q.id in ids]
    elif args.rapido:
        preguntas = [q for q in todas if q.id in RAPIDO]
    else:
        preguntas = todas

    print(f"SEGI-LOCAL | modelo evaluado: {args.modelo} | juez: {args.juez} | {len(preguntas)} preguntas")
    if args.juez == args.modelo:
        print("AVISO: el juez y el evaluado son el mismo modelo (autocorrección; menos fiable).")
    print("\n[1/3] Preguntando al modelo...")
    respuestas = recoger_respuestas(args.modelo, preguntas)
    (CARPETA / "respuestas_segi.json").write_text(
        json.dumps(respuestas, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[2/3] Corrigiendo (auto para código/JSON/exactas, juez para rúbricas)...")
    resultados = []
    for q in preguntas:
        r = segi.grade_question(q, respuestas.get(q.id, ""))
        if q.kind == "manual":
            r.score, r.feedback = puntuar_rubrica(args.juez, q, respuestas.get(q.id, ""))
            r.auto_graded = True
            if r.score < 0:  # el juez falló: no cuenta como 0 injusto
                r.score = 0.0
        print(f"  {q.id}: {r.score:.2f}/{r.max_points:.2f}  {r.category}")
        resultados.append(r)

    print("\n[3/3] Informe")
    total = sum(r.score for r in resultados)
    maximo = sum(r.max_points for r in resultados)
    pct = 100 * total / maximo if maximo else 0
    cats = {}
    for r in resultados:
        b = cats.setdefault(r.category, [0.0, 0.0])
        b[0] += r.score; b[1] += r.max_points
    qmap = {q.id: q for q in preguntas}
    crit = [r for r in resultados if qmap[r.question_id].critical]
    crit_max = sum(r.max_points for r in crit)
    crit_pct = 100 * sum(r.score for r in crit) / crit_max if crit_max else 0

    print("=" * 60)
    print(f"NOTA GLOBAL: {total:.1f} / {maximo:.1f}  ({pct:.1f} %)")
    print(f"Áreas críticas: {crit_pct:.1f} %")
    print(f"Interpretación: {segi.interpret_score(pct, crit_pct, False)}")
    print("\nPor categoría:")
    for cat in sorted(cats):
        s, m = cats[cat]
        p = 100 * s / m if m else 0
        print(f"  {cat:16s} {s:6.2f}/{m:6.2f}  {p:5.1f}%")

    informe = {
        "modelo": args.modelo, "juez": args.juez,
        "nota": round(total, 2), "maximo": round(maximo, 2), "porcentaje": round(pct, 2),
        "criticas_porcentaje": round(crit_pct, 2),
        "categorias": {c: {"nota": round(v[0], 2), "max": round(v[1], 2)} for c, v in cats.items()},
        "detalle": [{"id": r.question_id, "categoria": r.category,
                     "nota": round(r.score, 2), "max": r.max_points} for r in resultados],
    }
    args.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRespuestas del modelo: respuestas_segi.json")
    print(f"Informe completo: {args.salida.name}")


if __name__ == "__main__":
    main()
