#!/usr/bin/env python3
"""ESTUDIO-CRIPTO — informe automático del mercado cripto (mejora 3).

Genera un informe con fecha y hora en una carpeta del escritorio. Si hay
internet, busca titulares frescos y el asistente los analiza con método; si no,
avisa y hace el informe solo con lo aprendido (la biblioteca local). Pensado
para lanzarse a mano o cada 12 h con el Programador de tareas (cadencia).

Uso:
    python estudio_cripto.py
    python estudio_cripto.py --tema "mercado global de renta variable"

Sin dependencias externas: usa internauta/nucleo si están, o su propia copia.
Educativo: no es asesoramiento financiero.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib import parse, request as urlreq

OLLAMA = "http://localhost:11434/api/chat"
MODELO = "cazador"  # el analista de oportunidades; si no existe, usa casanostra
TEMA_DEFECTO = "estado actual del mercado de criptomonedas y del ecosistema cripto"


def escritorio() -> Path:
    # Windows y Linux/Mac
    for cand in [Path.home() / "Desktop", Path.home() / "Escritorio"]:
        if cand.exists():
            return cand
    return Path.home()


def limpiar(t: str) -> str:
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()


def hay_internet() -> bool:
    try:
        urlreq.urlopen("https://duckduckgo.com", timeout=4)
        return True
    except OSError:
        return False


def buscar(consulta: str, n: int = 6) -> list:
    resultados = []
    try:
        u = "https://html.duckduckgo.com/html/?" + parse.urlencode({"q": consulta})
        req = urlreq.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        html = urlreq.urlopen(req, timeout=8).read().decode("utf-8", "ignore")
        for m in re.finditer(r'result__a[^>]*>(.*?)</a>.*?result__snippet[^>]*>(.*?)</a>',
                             html, re.S):
            titulo = re.sub(r"<.*?>", "", m.group(1)).strip()
            texto = re.sub(r"<.*?>", "", m.group(2)).strip()
            if titulo:
                resultados.append(f"- {titulo}: {texto}")
    except OSError:
        pass
    return resultados[:n]


def modelo_disponible() -> str:
    try:
        with urlreq.urlopen("http://localhost:11434/api/tags", timeout=10) as r:
            nombres = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return MODELO if any(n.startswith(MODELO) for n in nombres) else "casanostra"
    except OSError:
        return "casanostra"


def preguntar(modelo: str, sistema: str, usuario: str) -> str:
    datos = json.dumps({"model": modelo, "stream": False, "messages": [
        {"role": "system", "content": sistema},
        {"role": "user", "content": usuario}]}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=900) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


def main() -> None:
    tema = TEMA_DEFECTO
    if "--tema" in sys.argv:
        tema = sys.argv[sys.argv.index("--tema") + 1]

    ahora = datetime.now()
    sello = ahora.strftime("%Y-%m-%d_%H-%M")
    carpeta = escritorio() / "estudio-cripto"
    carpeta.mkdir(parents=True, exist_ok=True)
    modelo = modelo_disponible()

    online = hay_internet()
    if online:
        print("🌐 Hay internet: buscando titulares frescos...")
        titulares = buscar(tema)
        fuente = "titulares de búsqueda web de hoy"
        contexto = "\n".join(titulares) if titulares else "(la búsqueda no devolvió resultados)"
        if not titulares:
            online = False
    if not online:
        print("📴 Sin internet (o sin resultados): informe con lo aprendido.")
        fuente = "conocimiento local (sin datos de hoy)"
        contexto = "No hay titulares frescos disponibles."

    sistema = (
        "Eres un analista prudente. Redacta un informe breve y con fundamentos "
        "sobre el tema, aplicando el método: qué está pasando, quién gana/pierde, "
        "efectos de segundo orden, riesgos y una conclusión calibrada. "
        "Distingue hechos aportados de opinión. Si los datos no bastan o no están "
        "al día, dilo claramente. No inventes cifras ni des recomendaciones de "
        "compra/venta. Empieza por un resumen de 3 líneas."
    )
    usuario = f"Tema: {tema}\n\nFuente ({fuente}):\n{contexto}"
    print(f"Analizando con '{modelo}'...")
    try:
        informe = preguntar(modelo, sistema, usuario)
    except OSError:
        sys.exit("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")

    cabecera = (f"# Estudio cripto — {ahora.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Tema: {tema}\nModelo: {modelo}\nFuente: {fuente}\n\n"
                "> Educativo, no asesoramiento financiero. Verifica los datos en "
                "fuentes oficiales antes de decidir.\n\n---\n\n")
    destino = carpeta / f"informe_{sello}.md"
    destino.write_text(cabecera + informe + "\n", encoding="utf-8")
    print(f"\n✅ Informe guardado en:\n   {destino}")
    print("   (para que se genere solo cada 12h, añádelo a cadencia.ps1)")


if __name__ == "__main__":
    main()
