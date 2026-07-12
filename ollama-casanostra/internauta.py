#!/usr/bin/env python3
"""INTERNAUTA — casanostra con internet cuando lo hay, y local cuando no.

- Comprueba si hay conexión. Si la hay, busca en internet (DuckDuckGo, sin
  clave ni registro), le da los resultados FRESCOS al modelo y guarda un
  resumen con fecha en conocimiento_web/ (así aprende para el futuro offline).
- Si NO hay internet, avisa claramente y responde solo con lo aprendido:
  su biblioteca RAG local (conocimiento indexado + búsquedas guardadas).

Uso:
    python internauta.py "¿cómo está el mercado cripto esta semana?"
    python internauta.py --local "..."     # fuerza modo offline aunque haya red

Sin claves ni dependencias externas: librería estándar + Ollama local.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib import parse, request as urlreq

MODELO = "casanostra"
OLLAMA = "http://localhost:11434/api/chat"
CARPETA = Path(__file__).parent
WEB = CARPETA / "conocimiento_web"
INDICE = CARPETA / "indice_biblioteca.json"


def hay_internet() -> bool:
    """True si podemos alcanzar un host público en pocos segundos."""
    for url in ("https://duckduckgo.com", "https://www.google.com"):
        try:
            urlreq.urlopen(url, timeout=4)
            return True
        except OSError:
            continue
    return False


def buscar_web(consulta: str, n: int = 5) -> list[dict]:
    """Búsqueda sin clave con la API instantánea de DuckDuckGo + HTML lite."""
    resultados = []
    # 1) Respuesta instantánea (definiciones, resúmenes)
    try:
        u = "https://api.duckduckgo.com/?" + parse.urlencode(
            {"q": consulta, "format": "json", "no_html": 1, "skip_disambig": 1})
        d = json.loads(urlreq.urlopen(u, timeout=8).read().decode("utf-8", "ignore"))
        if d.get("AbstractText"):
            resultados.append({"titulo": d.get("Heading", ""),
                               "texto": d["AbstractText"],
                               "url": d.get("AbstractURL", "")})
        for t in d.get("RelatedTopics", []):
            if isinstance(t, dict) and t.get("Text"):
                resultados.append({"titulo": "", "texto": t["Text"],
                                   "url": t.get("FirstURL", "")})
    except OSError:
        pass
    # 2) Resultados de la versión HTML lite (titulares recientes)
    try:
        u = "https://html.duckduckgo.com/html/?" + parse.urlencode({"q": consulta})
        req = urlreq.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        html = urlreq.urlopen(req, timeout=8).read().decode("utf-8", "ignore")
        for m in re.finditer(r'result__a[^>]*>(.*?)</a>.*?result__snippet[^>]*>(.*?)</a>',
                             html, re.S):
            titulo = re.sub(r"<.*?>", "", m.group(1)).strip()
            texto = re.sub(r"<.*?>", "", m.group(2)).strip()
            if titulo:
                resultados.append({"titulo": titulo, "texto": texto, "url": ""})
    except OSError:
        pass
    # Deduplicar y recortar
    vistos, limpio = set(), []
    for r in resultados:
        clave = r["texto"][:80]
        if clave and clave not in vistos:
            vistos.add(clave)
            limpio.append(r)
    return limpio[:n]


def contexto_local(consulta: str, n: int = 4) -> str:
    """Fragmentos más parecidos de la biblioteca ya indexada (modo offline)."""
    if not INDICE.exists():
        return ""
    entradas = json.loads(INDICE.read_text(encoding="utf-8"))
    palabras = set(re.findall(r"\w+", consulta.lower()))
    def solapa(e):
        return len(palabras & set(re.findall(r"\w+", e["texto"].lower())))
    mejores = sorted(entradas, key=solapa, reverse=True)[:n]
    return "\n\n".join(f"[{e['archivo']}] {e['texto']}" for e in mejores if solapa(e))


def preguntar(sistema: str, consulta: str) -> str:
    datos = json.dumps({"model": MODELO, "stream": False, "messages": [
        {"role": "system", "content": sistema},
        {"role": "user", "content": consulta}]}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=600) as r:
        texto = json.loads(r.read())["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()


def guardar_aprendizaje(consulta: str, fuentes: list[dict]) -> None:
    WEB.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y-%m-%d_%H-%M")
    slug = re.sub(r"[^a-z0-9]+", "-", consulta.lower())[:40].strip("-") or "busqueda"
    cuerpo = f"# Búsqueda web: {consulta}\nFecha: {sello}\n\n"
    for f in fuentes:
        cuerpo += f"## {f['titulo'] or '(fuente)'}\n{f['texto']}\n{f['url']}\n\n"
    (WEB / f"{sello}_{slug}.md").write_text(cuerpo, encoding="utf-8")


def main() -> None:
    forzar_local = "--local" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--local"]
    consulta = " ".join(args).strip()
    if not consulta:
        sys.exit("Uso: python internauta.py \"tu pregunta\"")

    online = (not forzar_local) and hay_internet()

    if online:
        print("🌐 HAY INTERNET — buscando información fresca...\n")
        fuentes = buscar_web(consulta)
        if fuentes:
            guardar_aprendizaje(consulta, fuentes)
            contexto = "\n\n".join(
                f"[{f['titulo']}] {f['texto']} ({f['url']})" for f in fuentes)
            sistema = (
                "Responde a la pregunta usando estos resultados de búsqueda web "
                "recientes. Cita la fuente cuando afirmes un dato y distingue "
                "hecho de opinión. Si los resultados no bastan, dilo.\n\n"
                "RESULTADOS WEB:\n" + contexto)
            print(preguntar(sistema, consulta))
            print("\n(💾 guardado en conocimiento_web/ — la próxima vez lo sabré sin internet)")
        else:
            print("Había conexión pero la búsqueda no devolvió resultados; "
                  "paso a modo local.\n")
            online = False

    if not online:
        modo = "forzado por ti" if forzar_local else "NO HAY INTERNET"
        print(f"📴 MODO LOCAL ({modo}) — respondo solo con lo aprendido.\n")
        contexto = contexto_local(consulta)
        if contexto:
            sistema = ("Responde usando SOLO estos apuntes de tu biblioteca local. "
                       "Si la respuesta depende de datos actuales que no tienes, "
                       "avisa de que sin internet no puedes garantizar que estén "
                       "al día.\n\nAPUNTES:\n" + contexto)
        else:
            sistema = ("No tienes internet ni apuntes relevantes sobre esto. "
                       "Responde con tus fundamentos generales y AVISA claramente "
                       "de que no puedes consultar datos actuales.")
        print(preguntar(sistema, consulta))


if __name__ == "__main__":
    try:
        main()
    except OSError:
        sys.exit("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")
