#!/usr/bin/env python3
"""MOTOR AGÉNTICO — dashboard de tu sistema Casanostra en números fríos.

Responde: ¿qué tengo?, ¿a qué velocidad va?, ¿cuánto sé?, ¿cómo rindo en los
exámenes?, ¿cuánto me ahorraría/costaría esto en una API de pago?

Uso:  python motor.py           (informe rápido, sin gastar tiempo de modelo)
      python motor.py --bench   (añade prueba real de velocidad tokens/segundo)

Sin dependencias: librería estándar + API local de Ollama.
"""

import json
import re
import sys
from pathlib import Path
from urllib import request as urlreq

BASE = "http://localhost:11434"
CARPETA = Path(__file__).parent
# Precio orientativo de una API de pago potente (entrada+salida promediado), €/millón de tokens
PRECIO_API_EUR_MTOK = 15.0


def api(ruta: str, cuerpo: dict | None = None) -> dict:
    if cuerpo is None:
        req = urlreq.Request(BASE + ruta)
    else:
        req = urlreq.Request(BASE + ruta, data=json.dumps(cuerpo).encode(),
                             headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def seccion(titulo: str) -> None:
    print(f"\n=== {titulo} " + "=" * max(0, 46 - len(titulo)))


def inventario() -> None:
    seccion("INVENTARIO (¿qué tengo?)")
    modelos = api("/api/tags").get("models", [])
    total_gb = 0.0
    for m in sorted(modelos, key=lambda x: -x.get("size", 0)):
        gb = m.get("size", 0) / 1e9
        total_gb += gb
        print(f"  {m['name']:<28} {gb:5.1f} GB")
    print(f"  {'TOTAL: ' + str(len(modelos)) + ' modelos':<28} {total_gb:5.1f} GB")
    habilidades = list((CARPETA / "habilidades").glob("*.Modelfile"))
    print(f"  Skills/SOPs definidos: {len(habilidades)}")


def conocimiento() -> None:
    seccion("CONTEXTO (¿cuánto sé?)")
    for carpeta in ["conocimiento", "cerebro_inversor", "noticias", "cursos"]:
        ruta = CARPETA / carpeta
        if ruta.exists():
            archivos = [p for p in ruta.rglob("*.md")]
            kb = sum(p.stat().st_size for p in archivos) / 1024
            print(f"  {carpeta + '/':<20} {len(archivos):3d} notas  ({kb:7.1f} KB)")
    indice = CARPETA / "indice_biblioteca.json"
    if indice.exists():
        frags = len(json.loads(indice.read_text(encoding="utf-8")))
        print(f"  {'biblioteca (RAG)':<20} {frags:3d} fragmentos indexados")
    memoria = CARPETA / "memoria.md"
    if memoria.exists():
        lineas = len(memoria.read_text(encoding="utf-8").splitlines())
        print(f"  {'memoria.md':<20} {lineas:3d} líneas de memoria")


def examenes() -> None:
    seccion("RENDIMIENTO (historial de exámenes)")
    ruta = CARPETA / "resultados.md"
    if not ruta.exists():
        print("  Sin exámenes todavía. Corre: python examen.py casanostra")
        return
    filas = re.findall(r"^\|\s*([\d-]+)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|",
                       ruta.read_text(encoding="utf-8"), re.M)
    if not filas:
        print("  resultados.md sin filas legibles aún.")
        return
    for fecha, modelo, media in filas[-10:]:
        barra = "#" * int(float(media))
        print(f"  {fecha}  {modelo:<16} {media:>4}/10  {barra}")
    mejores: dict[str, float] = {}
    for _, modelo, media in filas:
        mejores[modelo] = max(mejores.get(modelo, 0.0), float(media))
    campeon = max(mejores.items(), key=lambda x: x[1])
    print(f"  Mejor nota histórica: {campeon[0]} con {campeon[1]}/10")


def bench() -> None:
    seccion("VELOCIDAD REAL (prueba en vivo)")
    print("  Midiendo con casanostra (una respuesta corta)...")
    r = api("/api/chat", {
        "model": "casanostra", "stream": False,
        "messages": [{"role": "user", "content": "Cuenta del 1 al 20 separado por comas."}],
    })
    tokens = r.get("eval_count", 0)
    dur_s = r.get("eval_duration", 1) / 1e9
    total_s = r.get("total_duration", 1) / 1e9
    tps = tokens / dur_s if dur_s else 0
    print(f"  Tokens generados: {tokens}  |  Velocidad: {tps:.1f} tokens/s  |  Total: {total_s:.1f}s")
    return


def roi() -> None:
    seccion("ROI (números fríos)")
    print(f"  Coste de tu sistema local: 0,00 € por consulta, para siempre.")
    # Estimación: cada examen completo son ~30 respuestas + 30 correcciones
    ruta = CARPETA / "resultados.md"
    n_examenes = 0
    if ruta.exists():
        n_examenes = len(re.findall(r"^\|\s*[\d-]+\s*\|", ruta.read_text(encoding="utf-8"), re.M))
    tokens_estimados = n_examenes * 20 * 800  # por examen: ~20 llamadas de ~800 tokens
    eur = tokens_estimados / 1e6 * PRECIO_API_EUR_MTOK
    print(f"  Solo tus exámenes ({n_examenes} pasadas) habrían costado ~{eur:.2f} € en una API de pago.")
    print(f"  (estimación con {PRECIO_API_EUR_MTOK:.0f} €/millón de tokens; el chat diario, aparte)")
    print("  Tu contexto (C1) es portátil: si mañana cambias de modelo, todo esto se conserva.")


def main() -> None:
    print("MOTOR AGÉNTICO — Casanostra")
    try:
        inventario()
    except OSError:
        sys.exit("No conecto con Ollama. ¿Está corriendo `ollama serve`?")
    conocimiento()
    examenes()
    if "--bench" in sys.argv:
        bench()
    roi()
    print()


if __name__ == "__main__":
    main()
