#!/usr/bin/env python3
"""BIBLIOTECA — RAG local: pregunta a tus propios documentos (.txt y .md).

La mejora de mayor impacto para un asistente local: en vez de responder solo
con lo que el modelo "recuerda", busca en TUS apuntes y responde citando el
archivo de donde sale cada dato. Todo local y gratuito.

Uso:
    ollama pull nomic-embed-text                       # solo la primera vez
    python3 biblioteca.py indexar ~/Documentos/apuntes # indexa una carpeta
    python3 biblioteca.py "¿qué dicen mis apuntes sobre los fondos indexados?"

Sin dependencias: usa solo la librería estándar de Python + la API de Ollama.
"""

import json
import math
import sys
from pathlib import Path
from urllib import request as urlreq

MODELO_CHAT = "casanostra"
MODELO_EMBEDDINGS = "nomic-embed-text"
BASE = "http://localhost:11434"
INDICE = Path(__file__).parent / "indice_biblioteca.json"
TAM_FRAGMENTO, SOLAPE, TOP_RESULTADOS = 900, 150, 4


def api(ruta: str, cuerpo: dict) -> dict:
    req = urlreq.Request(
        BASE + ruta,
        data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlreq.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def incrustar(textos: list[str]) -> list[list[float]]:
    return api("/api/embed", {"model": MODELO_EMBEDDINGS, "input": textos})["embeddings"]


def trocear(texto: str) -> list[str]:
    trozos, i = [], 0
    while i < len(texto):
        trozos.append(texto[i : i + TAM_FRAGMENTO])
        i += TAM_FRAGMENTO - SOLAPE
    return [t.strip() for t in trozos if t.strip()]


def indexar(carpetas: list[str], incremental: bool = False) -> None:
    # Acepta VARIAS carpetas y las indexa TODAS juntas en un único índice
    # (antes solo tomaba una y sobrescribía: indexar la segunda borraba la primera).
    archivos = []
    for carpeta in carpetas:
        ruta = Path(carpeta).expanduser()
        archivos += [p for p in ruta.rglob("*") if p.suffix.lower() in (".txt", ".md")]
    if not archivos:
        sys.exit(f"No hay archivos .txt ni .md en: {', '.join(carpetas)}")

    # Mejora 5: indexado incremental. Con --nuevo solo se reincrustan los
    # archivos cuyo contenido cambió (por firma de tamaño+mtime), reutilizando
    # los vectores ya calculados de los que no cambiaron. Acelera mucho al crecer.
    previas = []
    firmas = {}
    if incremental and INDICE.exists():
        previas = json.loads(INDICE.read_text(encoding="utf-8"))
        firmas = _leer_firmas()

    entradas = []
    for p in archivos:
        firma = f"{p.stat().st_size}-{int(p.stat().st_mtime)}"
        cacheadas = [e for e in previas if e["archivo"] == p.name] if incremental else []
        if incremental and cacheadas and firmas.get(p.name) == firma:
            entradas.extend(cacheadas)
            print(f"  {p.name}: sin cambios (reutilizado)")
            continue
        trozos = trocear(p.read_text(encoding="utf-8", errors="ignore"))
        print(f"  {p.name}: {len(trozos)} fragmentos")
        for inicio in range(0, len(trozos), 16):
            lote = trozos[inicio : inicio + 16]
            for texto, vector in zip(lote, incrustar(lote)):
                entradas.append({"archivo": p.name, "texto": texto, "vector": vector})
        firmas[p.name] = firma

    INDICE.write_text(json.dumps(entradas), encoding="utf-8")
    if incremental:
        _guardar_firmas({p.name: firmas.get(p.name, "") for p in archivos})
    print(f"\nÍndice guardado: {len(entradas)} fragmentos → {INDICE}")


def _firmas_path():
    return INDICE.parent / "indice_firmas.json"


def _leer_firmas() -> dict:
    fp = _firmas_path()
    return json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}


def _guardar_firmas(firmas: dict) -> None:
    _firmas_path().write_text(json.dumps(firmas), encoding="utf-8")


def coseno(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def preguntar(pregunta: str) -> None:
    if not INDICE.exists():
        sys.exit("Primero indexa tus documentos: python3 biblioteca.py indexar <carpeta>")
    entradas = json.loads(INDICE.read_text(encoding="utf-8"))
    qv = incrustar([pregunta])[0]
    mejores = sorted(entradas, key=lambda e: coseno(qv, e["vector"]), reverse=True)
    mejores = mejores[:TOP_RESULTADOS]
    contexto = "\n\n".join(f"[{e['archivo']}]\n{e['texto']}" for e in mejores)
    sistema = (
        "Responde usando SOLO los fragmentos de los documentos del usuario que "
        "aparecen a continuación. Cita entre corchetes el archivo de donde sale "
        "cada dato. Si la respuesta no está en los fragmentos, di claramente que "
        "no aparece en los documentos.\n\n" + contexto
    )
    datos = {
        "model": MODELO_CHAT,
        "stream": True,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": pregunta},
        ],
    }
    req = urlreq.Request(
        BASE + "/api/chat",
        data=json.dumps(datos).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlreq.urlopen(req, timeout=600) as r:
        for linea in r:
            if linea.strip():
                trozo = json.loads(linea).get("message", {}).get("content", "")
                print(trozo, end="", flush=True)
    print()


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "indexar":
            incremental = "--nuevo" in sys.argv
            carpetas = [a for a in sys.argv[2:] if a != "--nuevo"]
            indexar(carpetas, incremental=incremental)  # una o varias carpetas
        elif len(sys.argv) >= 2:
            preguntar(" ".join(sys.argv[1:]))
        else:
            print(__doc__)
    except OSError:
        sys.exit(
            "No conecto con Ollama. ¿Está corriendo `ollama serve`? "
            "¿Descargaste el modelo con `ollama pull nomic-embed-text`?"
        )
