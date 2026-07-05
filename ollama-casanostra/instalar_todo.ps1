# ============================================================================
#  INSTALADOR TODO-EN-UNO para WINDOWS — Claude Code + Ollama + Casanostra
#  Uso (PowerShell):  powershell -ExecutionPolicy Bypass -File .\instalar_todo.ps1
# ============================================================================
$ErrorActionPreference = "Stop"
$DIR = "$HOME\casanostra"
Write-Host "=============================================="
Write-Host " INSTALADOR TODO-EN-UNO (Windows): Claude Code + Casanostra"
Write-Host " Carpeta de instalacion: $DIR"
Write-Host "=============================================="

# ----------------------------------------------------------------- 1. Ollama
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  Write-Host "[1/6] Ollama ya instalado OK"
} else {
  Write-Host "[1/6] Ollama no encontrado."
  Write-Host "  Descargalo de https://ollama.com/download , instalalo y vuelve a ejecutar este script."
  exit 1
}

# ------------------------------------------------------------ 2. Claude Code
if (Get-Command claude -ErrorAction SilentlyContinue) {
  Write-Host "[2/6] Claude Code ya instalado OK"
} else {
  Write-Host "[2/6] Instalando Claude Code (instalador oficial de Anthropic)..."
  try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression }
  catch { Write-Host "  AVISO: no se pudo instalar Claude Code automaticamente. Manual: https://claude.com/claude-code" }
}

# ------------------------------------------- 3. Elegir modelo base segun RAM
Write-Host "[3/6] Detectando hardware..."
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
if     ($ramGB -ge 32) { $BASE = "qwen3:30b-a3b" }
elseif ($ramGB -ge 16) { $BASE = "qwen3:8b" }
elseif ($ramGB -ge 8)  { $BASE = "qwen3:4b" }
else                   { $BASE = "qwen3:1.7b" }
Write-Host "  RAM: $ramGB GB -> modelo base: $BASE"

# ----------------------------------------------------- 4. Escribir los archivos
Write-Host "[4/6] Creando archivos en $DIR ..."
New-Item -ItemType Directory -Force -Path "$DIR\habilidades","$DIR\habilidades_generadas" | Out-Null

$MODELFILE = @'
# Modelfile "casanostra" — asistente local estilo Claude sobre un modelo abierto
# Uso: ollama create casanostra -f Modelfile
# Cambia la línea FROM según la RAM de tu ordenador (ver README.md)

FROM __BASE__

# ---- Parámetros de inferencia ----
# Contexto amplio para conversaciones largas (baja a 8192 si tienes poca RAM)
PARAMETER num_ctx 16384
# Temperatura moderada: respuestas coherentes pero no repetitivas
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.05

# ---- Personalidad y estilo de trabajo ----
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

'@
$MAESTRO = @'
# Habilidad 1: MAESTRO — tutor personal autodidacta
# Uso: ollama create maestro -f habilidades/maestro.Modelfile
FROM qwen3:8b
PARAMETER num_ctx 16384
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
- Al final de cada sesión, entrega un resumen de 5 líneas titulado "APUNTES DE HOY" que el usuario pueda guardar con /recordar.
- Responde siempre en el idioma del usuario.
"""

'@
$FORJADOR = @'
# Habilidad 2: FORJADOR — programador senior con autocrítica
# Uso: ollama create forjador -f habilidades/forjador.Modelfile
FROM qwen3:8b
PARAMETER num_ctx 16384
PARAMETER temperature 0.4

SYSTEM """Eres FORJADOR, un ingeniero de software senior que nunca entrega código sin revisarlo antes.

Proceso obligatorio para CADA petición de código:
1. CONTRATO: reformula en 2 líneas qué debe hacer el código, sus entradas, salidas y casos límite. Si falta un dato imprescindible, haz UNA sola pregunta; si es razonable asumirlo, asume y declara la suposición.
2. DISEÑO: elige la solución más simple que funcione. Prohibido añadir abstracciones, opciones o manejo de errores para escenarios que no pueden ocurrir.
3. CÓDIGO: escribe el código completo y ejecutable, con nombres claros en el idioma del proyecto. Comenta solo lo que el código no puede expresar por sí mismo.
4. AUTOCRÍTICA (obligatoria, antes de responder): relee tu propio código buscando: errores de índice o límites, casos vacíos/nulos, recursos sin cerrar, inyección o entradas maliciosas, y errores de lógica. Corrige lo que encuentres SIN mencionarlo.
5. ENTREGA: presenta (a) el código final, (b) cómo ejecutarlo/probarlo con un comando exacto, (c) los 2-3 casos límite cubiertos y (d) UNA mejora futura posible, en una línea.

Reglas:
- Si el usuario pega un error, diagnostica la causa raíz antes de proponer el arreglo; nunca sugieras "prueba esto a ver".
- Si pide revisar código ajeno, entrega los hallazgos ordenados de más grave a menos grave, cada uno con línea, causa y arreglo concreto.
- Código peligroso (borrar datos, tocar producción): añade siempre una advertencia y una versión reversible primero.
- Nunca inventes funciones o librerías: si no estás seguro de que exista una API, dilo y ofrece la alternativa estándar.
"""

'@
$ALQUIMISTA = @'
# Habilidad 3: ALQUIMISTA — ingeniero de prompts que crea nuevas habilidades
# Uso: ollama create alquimista -f habilidades/alquimista.Modelfile
FROM qwen3:8b
PARAMETER num_ctx 16384
PARAMETER temperature 0.8

SYSTEM """Eres ALQUIMISTA, un ingeniero de prompts experto. Tu trabajo es convertir deseos vagos del usuario ("quiero que me ayude con X") en habilidades completas y listas para instalar en Ollama.

Cuando el usuario te pida una nueva habilidad, entrega SIEMPRE este paquete completo:

1. ANÁLISIS (máximo 5 líneas): qué quiere conseguir realmente el usuario, qué haría fracasar la habilidad, y qué nivel de creatividad necesita (temperatura baja 0.3-0.5 para precisión, alta 0.7-0.9 para creatividad).

2. MODELFILE COMPLETO, dentro de un bloque de código, con esta estructura exacta:
   - FROM con el modelo base
   - PARAMETER temperature ajustada al análisis
   - PARAMETER num_ctx 16384
   - SYSTEM con el prompt de sistema

3. El prompt de sistema DEBE contener siempre estas secciones:
   - Identidad: quién es y cuál es su única misión (una frase).
   - Proceso: pasos numerados y obligatorios que sigue en cada respuesta.
   - Reglas: 4-6 prohibiciones y obligaciones concretas (no genéricas como "sé útil").
   - Formato de salida: estructura exacta de la respuesta.
   - Cláusula de honestidad: admitir incertidumbre en vez de inventar.

4. INSTALACIÓN: el comando exacto `ollama create <nombre> -f <archivo>` y un ejemplo de primera pregunta para probarla.

5. PRUEBA DE CALIDAD: 3 preguntas de prueba con el comportamiento esperado en cada una, para que el usuario verifique que la habilidad funciona antes de usarla en serio.

Reglas:
- Los prompts que escribes son específicos y accionables; nada de relleno tipo "eres muy inteligente".
- Cada regla del prompt debe ser verificable: alguien externo podría comprobar si se cumple.
- Si el deseo del usuario es demasiado amplio para una sola habilidad, divídelo y propón 2-3 habilidades separadas.
- Escribe los prompts en el idioma del usuario.
"""

'@
$CHAT = @'
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

'@
$CEREBRO = @'
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

'@
$BIBLIOTECA = @'
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

'@

# Escribir en UTF-8 SIN BOM (Ollama y Python lo requieren limpio)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText("$DIR\Modelfile", $MODELFILE.Replace("__BASE__", $BASE), $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\maestro.Modelfile", $MAESTRO, $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\forjador.Modelfile", $FORJADOR, $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\alquimista.Modelfile", $ALQUIMISTA, $utf8)
[IO.File]::WriteAllText("$DIR\chat_memoria.py", $CHAT, $utf8)
[IO.File]::WriteAllText("$DIR\cerebro.py", $CEREBRO, $utf8)
[IO.File]::WriteAllText("$DIR\biblioteca.py", $BIBLIOTECA, $utf8)

# --------------------------------------------- 5. Descargar modelos y crear todo
Write-Host "[5/6] Descargando $BASE y creando los asistentes (puede tardar varios minutos)..."
ollama pull $BASE
ollama pull nomic-embed-text
ollama create casanostra -f "$DIR\Modelfile"
ollama create maestro    -f "$DIR\habilidades\maestro.Modelfile"
ollama create forjador   -f "$DIR\habilidades\forjador.Modelfile"
ollama create alquimista -f "$DIR\habilidades\alquimista.Modelfile"

# ------------------------------------------------------------------ 6. Resumen
Write-Host ""
Write-Host "=============================================="
Write-Host "[6/6] INSTALACION COMPLETA"
Write-Host "=============================================="
Write-Host ""
Write-Host "ASISTENTES LOCALES GRATUITOS (no caducan nunca):"
Write-Host "  ollama run casanostra    -> asistente general"
Write-Host "  ollama run maestro       -> tutor personal"
Write-Host "  ollama run forjador      -> programador senior"
Write-Host "  ollama run alquimista    -> creador de habilidades nuevas"
if (Get-Command python -ErrorAction SilentlyContinue) {
  Write-Host "  python $DIR\chat_memoria.py            -> chat con memoria automatica"
  Write-Host "  python $DIR\cerebro.py `"objetivo`"      -> agente autonomo con equipo"
  Write-Host "  python $DIR\biblioteca.py indexar <carpeta>  -> indexar tus documentos"
  Write-Host "  python $DIR\biblioteca.py `"pregunta`"   -> preguntar a tus documentos"
} else {
  Write-Host "  (Para chat_memoria.py, cerebro.py y biblioteca.py instala Python:"
  Write-Host "   https://python.org/downloads -> marca 'Add python.exe to PATH')"
}
Write-Host ""
Write-Host "CLAUDE CODE (necesita cuenta de Claude; tu plan pone los limites):"
Write-Host "  1. Abre una ventana NUEVA de PowerShell"
Write-Host "  2. Ejecuta:  claude"
Write-Host "  3. Inicia sesion cuando te lo pida"
Write-Host ""
Write-Host "Interfaz grafica web (opcional, requiere Docker Desktop):"
Write-Host "  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -e OLLAMA_BASE_URL=http://host.docker.internal:11434 -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main"
Write-Host "  y abre http://localhost:3000"
