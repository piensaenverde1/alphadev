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

cat > chat_memoria.py <<'EOF'
#!/usr/bin/env python3
"""Chat con memoria persistente para casanostra. Comandos: /recordar <texto>, /memoria, /salir"""
import json, sys
from pathlib import Path
from urllib import request as urlreq

MODELO = "casanostra"
URL = "http://localhost:11434/api/chat"
ARCHIVO = Path(__file__).parent / "memoria.md"

def leer(): return ARCHIVO.read_text(encoding="utf-8") if ARCHIVO.exists() else ""

def preguntar(mensajes):
    datos = json.dumps({"model": MODELO, "messages": mensajes, "stream": True}).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    respuesta = ""
    with urlreq.urlopen(req, timeout=600) as r:
        for linea in r:
            if not linea.strip(): continue
            texto = json.loads(linea).get("message", {}).get("content", "")
            print(texto, end="", flush=True); respuesta += texto
    print(); return respuesta

def main():
    sistema = "Continúa la conversación con el usuario."
    if leer(): sistema += "\n\nMemoria de sesiones anteriores:\n" + leer()
    mensajes = [{"role": "system", "content": sistema}]
    print("Casanostra con memoria. /recordar <dato>, /memoria, /salir")
    while True:
        try: entrada = input("\nTú> ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not entrada: continue
        if entrada == "/salir": break
        if entrada == "/memoria": print(leer() or "(vacía)"); continue
        if entrada.startswith("/recordar "):
            with ARCHIVO.open("a", encoding="utf-8") as f: f.write(f"- {entrada[10:]}\n")
            print("Guardado."); continue
        mensajes.append({"role": "user", "content": entrada})
        try: salida = preguntar(mensajes)
        except OSError: sys.exit("No conecto con Ollama. ¿Está corriendo `ollama serve`?")
        mensajes.append({"role": "assistant", "content": salida})

if __name__ == "__main__": main()
EOF

cat > cerebro.py <<'EOF'
#!/usr/bin/env python3
"""CEREBRO — agente autónomo local con equipo: estratega → alquimista → equipo → crítico.
Uso: python3 cerebro.py "tu objetivo". Solo genera texto; nunca ejecuta comandos.
Guarda informe + Modelfiles de habilidades nuevas en habilidades_generadas/."""
import json, re, sys, unicodedata
from datetime import date
from pathlib import Path
from urllib import request as urlreq

MODELO, URL = "casanostra", "http://localhost:11434/api/chat"
MAX_ITER, MAX_ESP = 3, 3
SALIDA = Path(__file__).parent / "habilidades_generadas"

def llamar(sistema, usuario):
    datos = json.dumps({"model": MODELO, "stream": False, "messages": [
        {"role": "system", "content": sistema}, {"role": "user", "content": usuario}]}).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=900) as r:
        return json.loads(r.read())["message"]["content"].strip()

def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "habilidad"

ESTRATEGA = """Eres ESTRATEGA, coordinador de un equipo de agentes de IA. Dado un objetivo,
decide el equipo mínimo (1 a 3 especialistas). Responde SOLO líneas con este formato:
ESPECIALISTA: <nombre de una palabra> | <misión concreta en una frase>"""
ALQUIMISTA = """Eres ALQUIMISTA, ingeniero de prompts. Te doy nombre y misión de un especialista.
Escribe SOLO su prompt de sistema: identidad en una frase, proceso numerado, 4 reglas concretas
y verificables, formato de salida, y obligación de admitir incertidumbre en vez de inventar."""
CRITICO = """Eres CRÍTICO, revisor implacable pero justo. Evalúa si el trabajo cumple el objetivo.
Primera línea EXACTA: "VEREDICTO: APROBADO" o "VEREDICTO: MEJORAR". Si es MEJORAR, lista
numerada de mejoras concretas (máximo 5). Nada cosmético."""

def main():
    objetivo = " ".join(sys.argv[1:]).strip() or input("¿Cuál es tu objetivo? ").strip()
    if not objetivo: sys.exit("Necesito un objetivo.")
    print(f"\n🧠 CEREBRO trabajando en: {objetivo}\n\n1/4 ESTRATEGA diseñando el equipo...")
    plan = llamar(ESTRATEGA, f"Objetivo del usuario: {objetivo}")
    equipo = re.findall(r"ESPECIALISTA:\s*([^|]+)\|\s*(.+)", plan)[:MAX_ESP] or \
             [("generalista", f"Resolver de la mejor forma posible: {objetivo}")]
    for n, m in equipo: print(f"   → {n.strip()}: {m.strip()}")
    print("\n2/4 ALQUIMISTA generando los prompts del equipo...")
    prompts = {n.strip(): llamar(ALQUIMISTA, f"Especialista: {n.strip()}\nMisión: {m.strip()}")
               for n, m in equipo}
    critica, trabajo = "", ""
    for i in range(1, MAX_ITER + 1):
        print(f"\n3/4 EQUIPO trabajando (iteración {i})...")
        partes = []
        for n, m in equipo:
            n = n.strip()
            encargo = f"Objetivo global: {objetivo}\nTu misión: {m.strip()}"
            if critica: encargo += f"\n\nMejoras exigidas por el revisor:\n{critica}"
            partes.append(f"## Aporte de {n}\n\n{llamar(prompts[n], encargo)}")
        trabajo = "\n\n".join(partes)
        print("4/4 CRÍTICO revisando...")
        v = llamar(CRITICO, f"Objetivo: {objetivo}\n\nTrabajo del equipo:\n{trabajo}")
        if v.upper().startswith("VEREDICTO: APROBADO"): print("   ✅ Aprobado."); break
        critica = v.partition("\n")[2].strip(); print("   🔁 El crítico pide mejoras; el equipo itera.")
    carpeta = SALIDA / f"{date.today()}-{slug(objetivo)}"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "informe.md").write_text(
        f"# Objetivo\n\n{objetivo}\n\n# Resultado del equipo\n\n{trabajo}\n", encoding="utf-8")
    for n, p in prompts.items():
        (carpeta / f"{slug(n)}.Modelfile").write_text(
            f'FROM {MODELO}\nPARAMETER temperature 0.6\n\nSYSTEM """{p}"""\n', encoding="utf-8")
    print(f"\n📁 Guardado en: {carpeta}\n   informe.md + un .Modelfile por especialista")
    print(f"   Instalar: ollama create <nombre> -f {carpeta}/<nombre>.Modelfile")

if __name__ == "__main__":
    try: main()
    except OSError: sys.exit("No conecto con Ollama. ¿Está corriendo `ollama serve`?")
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
echo ""
echo "CLAUDE CODE (necesita cuenta de Claude; tu plan pone los límites):"
echo "  1. Abre un terminal NUEVO (para que cargue el PATH)"
echo "  2. Ejecuta:  claude"
echo "  3. Inicia sesión cuando te lo pida"
echo ""
