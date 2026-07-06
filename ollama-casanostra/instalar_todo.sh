#!/usr/bin/env bash
# ============================================================================
#  INSTALADOR TODO-EN-UNO — Claude Code + Ollama + Casanostra + habilidades
#  Auto-contenido: no necesita descargar nada más de tu repositorio.
#  Uso:  bash instalar_todo.sh      (Linux o macOS; en Windows usa WSL)
# ============================================================================
set -e

DIR="$HOME/casanostra"
echo "=============================================="
echo " INSTALADOR TODO-EN-UNO: Claude Code + Casanostra"
echo " Carpeta de instalación: $DIR"
echo "=============================================="

# ----------------------------------------------------------------- 1. Ollama
if command -v ollama >/dev/null 2>&1; then
  echo "[1/6] Ollama ya instalado ✓"
else
  echo "[1/6] Instalando Ollama..."
  if [[ "$(uname)" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then brew install ollama
    else
      echo "  En Mac sin Homebrew: descarga Ollama de https://ollama.com/download"
      echo "  instálalo y vuelve a ejecutar este script."; exit 1
    fi
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi
# Arrancar el servidor si no está corriendo
pgrep -f "ollama" >/dev/null 2>&1 || (nohup ollama serve >/dev/null 2>&1 & sleep 3)

# ------------------------------------------------------------ 2. Claude Code
if command -v claude >/dev/null 2>&1; then
  echo "[2/6] Claude Code ya instalado ✓"
else
  echo "[2/6] Instalando Claude Code (instalador oficial de Anthropic)..."
  curl -fsSL https://claude.ai/install.sh | bash || \
    echo "  ⚠ No se pudo instalar Claude Code automáticamente. Manual: https://claude.com/claude-code"
fi

# ------------------------------------------- 3. Elegir modelo base según RAM
echo "[3/6] Detectando hardware..."
if [[ "$(uname)" == "Darwin" ]]; then
  RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
else
  RAM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1048576 ))
fi
if   (( RAM_GB >= 32 )); then BASE="qwen3:30b-a3b"
elif (( RAM_GB >= 16 )); then BASE="qwen3:8b"
elif (( RAM_GB >= 8  )); then BASE="qwen3:4b"
else BASE="qwen3:1.7b"; fi
echo "  RAM: ${RAM_GB} GB → modelo base: ${BASE}"

# ----------------------------------------------------- 4. Escribir los archivos
echo "[4/6] Creando archivos en $DIR ..."
mkdir -p "$DIR/habilidades" "$DIR/habilidades_generadas"
cd "$DIR"

cat > Modelfile <<MODELFILE_EOF
FROM ${BASE}
PARAMETER num_ctx 16384
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.05

SYSTEM """Eres Casanostra, un asistente de IA local, privado y gratuito.

Estilo de trabajo:
- Razona paso a paso antes de responder a preguntas complejas: descompón el problema, considera alternativas y verifica tu propia respuesta antes de darla.
- Empieza siempre por la conclusión o el resultado, y después da el detalle de apoyo.
- Sé honesto sobre la incertidumbre: si no sabes algo o puedes estar equivocado, dilo explícitamente en vez de inventar datos, fechas o citas.
- Responde en el idioma del usuario (normalmente español).
- Para código: entrega código completo y ejecutable, explica las decisiones importantes y señala los casos límite.
- Para tareas largas: propón un plan breve, ejecútalo por partes y resume el progreso.
- Sé conciso: elimina relleno, no repitas la pregunta del usuario, no uses frases de cortesía innecesarias.

Límites:
- Si una petición es ambigua, haz una sola pregunta aclaratoria en lugar de suponer.
- Si el usuario describe un problema sin pedir un cambio, tu entregable es el diagnóstico, no la solución aplicada.
"""
MODELFILE_EOF

cat > habilidades/maestro.Modelfile <<'EOF'
FROM casanostra
PARAMETER temperature 0.6

SYSTEM """Eres MAESTRO, un catedrático personal cuyo único objetivo es que el usuario aprenda de verdad, no que memorice.

Método de trabajo obligatorio:
1. DIAGNÓSTICO: al empezar un tema nuevo, haz 3 preguntas cortas para medir el nivel real del usuario. No expliques nada hasta tener las respuestas.
2. PLAN: diseña una ruta de aprendizaje en niveles (principiante → intermedio → avanzado) con hitos medibles. Muéstrala como lista numerada y pide confirmación.
3. LECCIÓN: explica cada concepto en 3 capas: (a) analogía de la vida cotidiana, (b) definición técnica precisa, (c) ejemplo práctico ejecutable o aplicable hoy mismo.
4. PRÁCTICA: tras cada lección propón UN ejercicio concreto. Corrige la respuesta del usuario señalando primero lo que hizo bien, después el error exacto y por qué ocurre.
5. REPASO: cada 5 interacciones, haz un mini-examen de 3 preguntas sobre lo ya visto (repetición espaciada). Si falla algo, vuelve a explicarlo con una analogía DIFERENTE a la primera.

Reglas:
- Método socrático: antes de dar una respuesta directa, intenta que el usuario la deduzca con una pista.
- Nunca avances de nivel si el mini-examen tiene fallos.
- Honestidad total: si un dato puede estar desactualizado o no lo sabes con certeza, dilo y sugiere cómo verificarlo.
- Al final de cada sesión, entrega un resumen de 5 líneas titulado "APUNTES DE HOY".
- Responde siempre en el idioma del usuario.
"""
EOF

cat > habilidades/forjador.Modelfile <<'EOF'
FROM casanostra
PARAMETER temperature 0.4

SYSTEM """Eres FORJADOR, un ingeniero de software senior que nunca entrega código sin revisarlo antes.

Proceso obligatorio para CADA petición de código:
1. CONTRATO: reformula en 2 líneas qué debe hacer el código, sus entradas, salidas y casos límite. Si falta un dato imprescindible, haz UNA sola pregunta; si es razonable asumirlo, asume y declara la suposición.
2. DISEÑO: elige la solución más simple que funcione. Prohibido añadir abstracciones, opciones o manejo de errores para escenarios que no pueden ocurrir.
3. CÓDIGO: escribe el código completo y ejecutable, con nombres claros. Comenta solo lo que el código no puede expresar por sí mismo.
4. AUTOCRÍTICA (obligatoria, antes de responder): relee tu propio código buscando errores de índice o límites, casos vacíos/nulos, recursos sin cerrar, inyección o entradas maliciosas, y errores de lógica. Corrige lo que encuentres SIN mencionarlo.
5. ENTREGA: presenta (a) el código final, (b) cómo ejecutarlo/probarlo con un comando exacto, (c) los 2-3 casos límite cubiertos y (d) UNA mejora futura posible, en una línea.

Reglas:
- Si el usuario pega un error, diagnostica la causa raíz antes de proponer el arreglo; nunca sugieras "prueba esto a ver".
- Si pide revisar código ajeno, entrega los hallazgos ordenados de más grave a menos grave, cada uno con línea, causa y arreglo concreto.
- Código peligroso (borrar datos, tocar producción): añade siempre una advertencia y una versión reversible primero.
- Nunca inventes funciones o librerías: si no estás seguro de que exista una API, dilo y ofrece la alternativa estándar.
"""
EOF

cat > habilidades/alquimista.Modelfile <<'EOF'
FROM casanostra
PARAMETER temperature 0.8

SYSTEM """Eres ALQUIMISTA, un ingeniero de prompts experto. Tu trabajo es convertir deseos vagos del usuario ("quiero que me ayude con X") en habilidades completas y listas para instalar en Ollama.

Cuando el usuario te pida una nueva habilidad, entrega SIEMPRE este paquete completo:

1. ANÁLISIS (máximo 5 líneas): qué quiere conseguir realmente el usuario, qué haría fracasar la habilidad, y qué nivel de creatividad necesita (temperatura baja 0.3-0.5 para precisión, alta 0.7-0.9 para creatividad).
2. MODELFILE COMPLETO, dentro de un bloque de código: FROM casanostra, PARAMETER temperature ajustada, y SYSTEM con el prompt.
3. El prompt de sistema DEBE contener: Identidad (una frase), Proceso (pasos numerados obligatorios), Reglas (4-6 concretas y verificables), Formato de salida, y cláusula de honestidad (admitir incertidumbre en vez de inventar).
4. INSTALACIÓN: el comando exacto `ollama create <nombre> -f <archivo>` y un ejemplo de primera pregunta para probarla.
5. PRUEBA DE CALIDAD: 3 preguntas de prueba con el comportamiento esperado en cada una.

Reglas:
- Los prompts que escribes son específicos y accionables; nada de relleno tipo "eres muy inteligente".
- Cada regla del prompt debe ser verificable por alguien externo.
- Si el deseo del usuario es demasiado amplio para una sola habilidad, divídelo y propón 2-3 habilidades separadas.
- Escribe los prompts en el idioma del usuario.
"""
EOF

cat > chat_memoria.py <<'CHAT_EOF'
#!/usr/bin/env python3
"""Chat con memoria persistente y AUTOMÁTICA para casanostra.

- /recordar <texto>  guarda un dato a mano
- /memoria           muestra la memoria actual
- /salir             termina la sesión
- Al salir, el propio modelo resume la conversación y guarda lo importante
  en memoria.md sin que tengas que hacer nada (memoria automática).

Sin dependencias: solo la librería estándar de Python.
"""

import json
import sys
from datetime import date
from pathlib import Path
from urllib import request as urlreq

MODELO = "casanostra"
URL = "http://localhost:11434/api/chat"
ARCHIVO = Path(__file__).parent / "memoria.md"


def leer() -> str:
    return ARCHIVO.read_text(encoding="utf-8") if ARCHIVO.exists() else ""


def anotar(texto: str) -> None:
    with ARCHIVO.open("a", encoding="utf-8") as f:
        f.write(texto.rstrip() + "\n")


def preguntar(mensajes: list[dict], stream: bool = True) -> str:
    datos = json.dumps({"model": MODELO, "messages": mensajes, "stream": stream}).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    if not stream:
        with urlreq.urlopen(req, timeout=600) as r:
            return json.loads(r.read())["message"]["content"].strip()
    respuesta = ""
    with urlreq.urlopen(req, timeout=600) as r:
        for linea in r:
            if not linea.strip():
                continue
            texto = json.loads(linea).get("message", {}).get("content", "")
            print(texto, end="", flush=True)
            respuesta += texto
    print()
    return respuesta


def resumen_automatico(mensajes: list[dict]) -> None:
    """Memoria automática: al salir, el modelo resume la sesión y la guarda."""
    charla = [m for m in mensajes if m["role"] != "system"]
    if len(charla) < 2:
        return
    print("\nGuardando memoria automática...")
    transcripcion = "\n".join(f"{m['role']}: {m['content']}" for m in charla)
    resumen = preguntar(
        [
            {
                "role": "system",
                "content": (
                    "Resume esta conversación en un máximo de 5 viñetas con SOLO "
                    "los datos útiles para el futuro: decisiones tomadas, datos "
                    "personales o del proyecto, tareas pendientes y preferencias "
                    "del usuario. Si no hay nada que valga la pena recordar, "
                    "responde exactamente NADA."
                ),
            },
            {"role": "user", "content": transcripcion[-8000:]},
        ],
        stream=False,
    )
    if resumen.upper().strip() != "NADA":
        anotar(f"\n## Sesión {date.today()}\n{resumen}")
        print(f"Memoria guardada en {ARCHIVO}")


def main() -> None:
    sistema = "Continúa la conversación con el usuario."
    memoria = leer()
    if memoria:
        sistema += "\n\nMemoria de sesiones anteriores:\n" + memoria
    mensajes = [{"role": "system", "content": sistema}]
    print("Casanostra con memoria automática. /recordar <dato>, /memoria, /salir")
    try:
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
                print(leer() or "(vacía)")
                continue
            if entrada.startswith("/recordar "):
                anotar(f"- {entrada[len('/recordar '):]}")
                print("Guardado.")
                continue
            mensajes.append({"role": "user", "content": entrada})
            try:
                salida = preguntar(mensajes)
            except OSError:
                sys.exit("No conecto con Ollama. ¿Está corriendo `ollama serve`?")
            mensajes.append({"role": "assistant", "content": salida})
    finally:
        try:
            resumen_automatico(mensajes)
        except OSError:
            pass


if __name__ == "__main__":
    main()

CHAT_EOF

cat > cerebro.py <<'EOF'
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

EOF

cat > biblioteca.py <<'BIBLIO_EOF'
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


def indexar(carpeta: str) -> None:
    ruta = Path(carpeta).expanduser()
    archivos = [p for p in ruta.rglob("*") if p.suffix.lower() in (".txt", ".md")]
    if not archivos:
        sys.exit(f"No hay archivos .txt ni .md en {ruta}")
    entradas = []
    for p in archivos:
        trozos = trocear(p.read_text(encoding="utf-8", errors="ignore"))
        print(f"  {p.name}: {len(trozos)} fragmentos")
        # incrustar en lotes de 16 para no saturar la API
        for inicio in range(0, len(trozos), 16):
            lote = trozos[inicio : inicio + 16]
            for texto, vector in zip(lote, incrustar(lote)):
                entradas.append({"archivo": p.name, "texto": texto, "vector": vector})
    INDICE.write_text(json.dumps(entradas), encoding="utf-8")
    print(f"\nÍndice guardado: {len(entradas)} fragmentos → {INDICE}")


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
            indexar(sys.argv[2])
        elif len(sys.argv) >= 2:
            preguntar(" ".join(sys.argv[1:]))
        else:
            print(__doc__)
    except OSError:
        sys.exit(
            "No conecto con Ollama. ¿Está corriendo `ollama serve`? "
            "¿Descargaste el modelo con `ollama pull nomic-embed-text`?"
        )

BIBLIO_EOF

cat > interfaz.sh <<'INTERFAZ_EOF'
#!/usr/bin/env bash
# Interfaz gráfica gratuita (Open WebUI) para tus modelos locales de Ollama.
# Te da un chat tipo web con historial, subida de documentos y selector de
# modelos (casanostra, maestro, forjador, alquimista...).
# Uso: bash interfaz.sh
set -e

if command -v docker >/dev/null 2>&1; then
  echo "Instalando Open WebUI con Docker..."
  docker rm -f open-webui >/dev/null 2>&1 || true
  docker run -d -p 3000:8080 \
    --add-host=host.docker.internal:host-gateway \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -v open-webui:/app/backend/data \
    --name open-webui --restart always \
    ghcr.io/open-webui/open-webui:main
  echo ""
  echo "✅ Listo. Abre en tu navegador:  http://localhost:3000"
  echo "   (la primera cuenta que crees será la de administrador; es local, no sale de tu PC)"
else
  echo "Docker no encontrado; instalando con pip (necesita Python 3.11 o superior)..."
  python3 -m pip install --user open-webui || pip3 install --user open-webui
  echo ""
  echo "✅ Instalado. Arranca la interfaz con:"
  echo "     open-webui serve"
  echo "   y abre en tu navegador:  http://localhost:8080"
fi

INTERFAZ_EOF
chmod +x interfaz.sh

cat > examen.py <<'EXAMEN_EOF'
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

EXAMEN_EOF

# --------------------------------------------- 5. Descargar modelo y crear todo
echo "[5/6] Descargando ${BASE} y creando los asistentes (puede tardar varios minutos)..."
ollama pull "${BASE}"
ollama pull nomic-embed-text   # embeddings para biblioteca.py (RAG)
ollama create casanostra -f Modelfile
ollama create maestro    -f habilidades/maestro.Modelfile
ollama create forjador   -f habilidades/forjador.Modelfile
ollama create alquimista -f habilidades/alquimista.Modelfile

# ------------------------------------------------------------------ 6. Resumen
echo ""
echo "=============================================="
echo "[6/6] ✅ INSTALACIÓN COMPLETA"
echo "=============================================="
echo ""
echo "ASISTENTES LOCALES GRATUITOS (no caducan nunca):"
echo "  ollama run casanostra    → asistente general"
echo "  ollama run maestro       → tutor personal"
echo "  ollama run forjador      → programador senior"
echo "  ollama run alquimista    → creador de habilidades nuevas"
echo "  python3 $DIR/chat_memoria.py     → chat con memoria persistente"
echo "  python3 $DIR/cerebro.py \"objetivo\"  → agente autónomo con equipo"
echo "  python3 $DIR/biblioteca.py indexar <carpeta>  → indexar tus documentos"
echo "  python3 $DIR/biblioteca.py \"pregunta\"          → preguntar a tus documentos"
echo "  bash $DIR/interfaz.sh                  → interfaz gráfica web (Open WebUI)"
echo "  python3 $DIR/examen.py <modelo1> <modelo2>  → banco de pruebas con notas"
echo ""
echo "CLAUDE CODE (necesita cuenta de Claude; tu plan pone los límites):"
echo "  1. Abre un terminal NUEVO (para que cargue el PATH)"
echo "  2. Ejecuta:  claude"
echo "  3. Inicia sesión cuando te lo pida"
echo ""
