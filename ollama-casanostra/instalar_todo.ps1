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
$RESOLUTOR = @'
# Habilidad 4: RESOLUTOR — experto en resolver problemas con solución automática
# Uso: ollama create resolutor -f habilidades/resolutor.Modelfile
FROM casanostra
PARAMETER temperature 0.5

SYSTEM """Eres RESOLUTOR, un experto en resolver problemas de cualquier tipo (técnicos, cotidianos, de dinero, de organización). Tu misión es entregar SIEMPRE una solución elegida y lista para aplicar, no una lista de opciones para que el usuario decida.

Proceso obligatorio para CADA problema:
1. DEFINIR: reformula el problema en una frase y define qué significa "resuelto" con un criterio verificable ("resuelto = el ordenador arranca en menos de 1 minuto").
2. CAUSA RAÍZ: distingue el síntoma de la causa. Pregunta "¿por qué ocurre?" en cadena (hasta 5 veces) hasta llegar a algo que se pueda atacar. Si hay varias causas posibles, ordénalas de más probable a menos.
3. OPCIONES: genera 3 soluciones distintas (la rápida, la sólida y la barata), cada una con su pro y su contra en una línea.
4. DECIDIR AUTOMÁTICAMENTE: elige TÚ la mejor según el criterio de éxito y justifícalo en una frase. Prohibido responder "depende" o devolverle la decisión al usuario; solo pregunta si falta un dato imprescindible (máximo una pregunta).
5. PLAN DE ACCIÓN: pasos numerados y concretos, donde el paso 1 se pueda hacer en los próximos 5 minutos.
6. VERIFICACIÓN Y PLAN B: cómo comprobar que quedó resuelto (el criterio del paso 1), y cuál es la señal exacta que activa el plan B (la segunda mejor opción, dila).

Reglas:
- Actúa como si el usuario fuera a ejecutar tu plan tal cual: nada de vaguedades tipo "consulta con un experto" como paso principal.
- Si el problema es demasiado grande, divídelo y resuelve primero el sub-problema que desbloquea a los demás, diciéndolo explícitamente.
- Si el problema descrito no se puede reproducir u observar, tu paso 1 es siempre cómo observarlo (registrar cuándo pasa, con qué condiciones).
- Honestidad: si tu solución tiene riesgo de empeorar algo, dilo y da la versión reversible primero.
- Formato de salida fijo: PROBLEMA / CAUSA MÁS PROBABLE / SOLUCIÓN ELEGIDA (con justificación) / PLAN (pasos numerados) / VERIFICACIÓN / PLAN B.
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
$EXAMEN = @'
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
    global PREGUNTAS
    args = sys.argv[1:]
    # Un argumento .json es un banco de preguntas alternativo; el resto, modelos
    bancos = [a for a in args if a.endswith(".json")]
    modelos = [a for a in args if not a.endswith(".json")] or ["casanostra"]
    if bancos:
        ruta = Path(bancos[0])
        if not ruta.exists():
            ruta = CARPETA / bancos[0]
        if not ruta.exists():
            sys.exit(f"No encuentro el banco de preguntas: {bancos[0]}")
        PREGUNTAS = ruta
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

'@

$CONOC_PROG = @'
# Apuntes maestros de programación

## Principios que separan a un 10 de un 5

- La mejor solución es la más simple que funciona. Cada abstracción, opción o
  capa extra debe justificar su existencia hoy, no "por si acaso mañana".
- Los nombres son documentación: `dias_hasta_vencimiento` vale más que `d` y
  que tres líneas de comentario. Si necesitas comentar QUÉ hace una línea,
  el nombre está mal elegido.
- Funciones pequeñas con una sola responsabilidad. Si al describir una función
  dices "y", probablemente son dos funciones.
- Valida solo en las fronteras del sistema (entrada del usuario, APIs externas,
  archivos). Dentro de tu propio código, confía en tus propias garantías.
- No repitas conocimiento (DRY), pero no fusiones código que solo se parece
  por casualidad: duplicar dos líneas es mejor que una abstracción equivocada.

## Proceso profesional para cualquier tarea de código

1. CONTRATO: qué entra, qué sale, qué casos límite existen. Escríbelo antes.
2. DISEÑO: la estructura más simple. Piensa en datos primero, código después.
3. IMPLEMENTAR: de fuera a dentro, dejando lo difícil aislado en funciones puras.
4. PROBAR: primero el caso normal, luego los límites (ver sección de pruebas).
5. REFACTORIZAR: solo cuando funciona. Nunca optimices lo que no has medido.

## Depuración por causa raíz (nunca "prueba a ver")

1. REPRODUCIR: si no puedes reproducir el fallo, no puedes arreglarlo.
2. LEER el error completo: la última línea dice el qué; la traza dice el dónde.
3. AISLAR por bisección: corta el problema por la mitad hasta acorralar la línea.
4. UNA hipótesis cada vez: cambia UNA cosa, observa, repite. Cambiar tres cosas
   a la vez destruye la información.
5. VERIFICAR el arreglo: el bug reproducido antes ya no ocurre, y lo demás sigue
   funcionando. Un arreglo sin verificación es una superstición.
6. PREGUNTAR por qué existió: ¿qué permitió que este bug llegara aquí? Arregla
   también eso (test que faltaba, validación de frontera, nombre confuso).

## Casos límite que SIEMPRE hay que probar

- Vacío, un elemento, muchos elementos.
- Cero, negativo, número enorme, decimal cuando esperas entero.
- Nulo/None, cadena vacía, espacios, tildes y emojis (unicode).
- El mismo elemento repetido; entradas ya ordenadas y en orden inverso.
- División: divisor cero. Índices: primero, último, fuera de rango.

## Seguridad mínima no negociable

- NUNCA construyas SQL concatenando texto del usuario: usa parámetros
  (`cursor.execute("... WHERE nombre = ?", (nombre,))`). Lo contrario es
  inyección SQL, el error más explotado de la historia.
- NUNCA pongas claves, contraseñas o tokens en el código ni en Git: variables
  de entorno o archivo ignorado por Git.
- Sanea nombres de archivo que vengan de fuera (`os.path.basename`) para evitar
  que "../../etc/passwd" escape de tu carpeta.
- Todo lo que ejecute comandos del sistema con texto del usuario es una bomba:
  usa listas de argumentos, jamás interpolación en un string de shell.

## Rendimiento con cabeza

- Primero mide (perfilador o cronómetro), después optimiza. La intuición sobre
  dónde está el cuello de botella falla casi siempre.
- Complejidades que hay que saber de memoria: buscar en lista = O(n); buscar en
  diccionario/set = O(1); ordenar = O(n log n); bucle dentro de bucle sobre los
  mismos datos = O(n²), sospecha siempre de él.
- El truco más rentable en Python: convertir "buscar en lista dentro de un
  bucle" en "buscar en un set", pasa de O(n²) a O(n).

## Python idiomático (errores comunes)

- Listas y diccionarios se pasan POR REFERENCIA: `y = x` no copia; `y.append()`
  también modifica `x`. Copia con `x.copy()` o `list(x)`.
- Jamás uses una lista como valor por defecto de un parámetro
  (`def f(datos=[])` se comparte entre llamadas); usa `None` y créala dentro.
- `s[::-1]` invierte una cadena. `enumerate` antes que `range(len(...))`.
- Abre archivos con `with open(...) as f:` — se cierran solos incluso con error.
- Excepciones: captura la más específica posible; un `except:` desnudo esconde
  hasta los errores de teclado.

## Git esencial

- Commits pequeños con mensajes que explican el PORQUÉ.
- Rama nueva para cada cosa; main siempre funciona.
- Antes de tocar nada delicado: `git status` y `git diff` para saber dónde estás.

'@
$CONOC_PROMPTS = @'
# Apuntes maestros de ingeniería de prompts

## Anatomía de un prompt profesional (las 6 piezas)

1. IDENTIDAD: quién es el modelo y su única misión, en una frase.
   ("Eres un revisor de contratos de alquiler español.")
2. CONTEXTO: los datos que necesita y que no puede adivinar.
   (el texto, el público objetivo, las restricciones)
3. TAREA: el verbo exacto. "Analiza", "resume en 3 puntos", "traduce" —
   nunca "ayúdame con".
4. PROCESO: pasos numerados si la tarea tiene orden ("primero identifica X,
   después compara con Y").
5. FORMATO DE SALIDA: estructura exacta de la respuesta (tabla, JSON, lista
   de N elementos, una sola palabra...). Lo que no pidas, no llegará.
6. CRITERIOS Y LÍMITES: qué hace buena la respuesta y qué está prohibido
   ("si no aparece en el texto, di 'no consta'; no inventes").

## Técnicas que funcionan (y cuándo usarlas)

- EJEMPLOS (few-shot): la técnica más potente. 2-3 pares entrada→salida
  enseñan el formato mejor que cualquier explicación. Úsala siempre que el
  formato importe.
- PENSAR PASO A PASO: para problemas de lógica o cálculo, pide "razona paso a
  paso antes de dar la respuesta final". Mejora la precisión a cambio de
  respuestas más largas.
- DELIMITADORES: separa los datos de las instrucciones con ``` o ###.
  Evita que el modelo confunda el texto a procesar con órdenes.
- ROL: "eres un auditor escéptico" cambia el comportamiento de verdad; úsalo
  para ajustar tono y nivel de exigencia.
- SALIDA ESTRUCTURADA: si vas a procesar la respuesta con código, exige un
  formato parseable ("responde SOLO con este formato: NOTA: <numero>") y
  parsea con tolerancia (busca el patrón, no la igualdad exacta).
- RESTRICCIÓN DE HONESTIDAD: añade siempre "si no lo sabes, dilo" en tareas
  con datos. Reduce las invenciones más que ninguna otra instrucción.

## Cómo iterar un prompt (el bucle del ingeniero)

1. Escribe la versión 1 con las 6 piezas.
2. Pruébala con un BANCO DE CASOS fijo (5-10 entradas con salida esperada).
3. Cambia UNA sola cosa por iteración. Si cambias tres, no sabrás cuál actuó.
4. Puntúa cada versión contra el banco. Conserva la mejor, no la última.
5. Cuando el prompt falla en un caso nuevo, añade ese caso al banco antes
   de tocar el prompt.

## Temperatura: el dial de creatividad

- 0.2–0.4: extracción de datos, corrección, clasificación, código. Precisión.
- 0.5–0.7: conversación general, explicaciones, resúmenes. Equilibrio.
- 0.8–1.0: lluvia de ideas, nombres, ficción. Variedad (y más errores).

## Anti-patrones (lo que estropea prompts)

- Relleno motivacional: "eres muy inteligente y lo harás genial" no aporta nada.
- Instrucciones contradictorias: "sé exhaustivo" + "sé breve" — elige.
- Prompt kilométrico sin estructura: si tú no puedes escanearlo, el modelo
  tampoco. Usa secciones y listas.
- Reglas no verificables: "sé útil" no se puede comprobar; "responde en menos
  de 100 palabras" sí. Toda regla debería ser comprobable por un tercero.
- Pedir N cosas en una pregunta: divide en N prompts o el modelo hará 2 bien
  y 3 regular.
- Negaciones ambiguas: "no seas demasiado técnico" — ¿cuánto es demasiado?
  Mejor: "explícalo para alguien sin estudios de informática".

## Plantilla reutilizable

```
Eres [IDENTIDAD], tu única misión es [MISIÓN].

Contexto: [DATOS QUE NECESITA]

Tarea: [VERBO + OBJETO CONCRETO]
Proceso:
1. [PASO]
2. [PASO]

Formato de salida: [ESTRUCTURA EXACTA]

Reglas:
- [REGLA VERIFICABLE]
- Si la información no está en el contexto, di "no consta"; no inventes.

Ejemplo:
Entrada: [EJEMPLO DE ENTRADA]
Salida: [EJEMPLO DE SALIDA PERFECTA]
```

'@
$CONOC_BUCLES = @'
# Apuntes maestros de bucles agénticos (agentes que trabajan solos)

## La idea central

Un agente no es un modelo más listo: es un modelo normal dentro de un BUCLE
bien diseñado. La inteligencia extra sale de la estructura: generar → criticar
→ revisar supera casi siempre a una única respuesta directa, incluso con el
mismo modelo.

## Los 4 patrones fundamentales

1. GENERADOR-CRÍTICO (el más rentable)
   - El generador produce; un crítico con instrucciones DISTINTAS revisa contra
     criterios concretos; el generador corrige con esa crítica. 2-3 rondas.
   - Clave: el crítico debe tener criterios verificables ("¿cumple X? ¿hay
     datos inventados?"), no "¿está bien?".

2. PLAN-EJECUTA-VERIFICA
   - Primero un plan corto (3-7 pasos). Luego ejecutar paso a paso. Al final,
     verificar el resultado contra el objetivo ANTES de darlo por terminado.
   - Clave: el plan se escribe una vez y se muestra; ejecutar sin plan produce
     deriva, y planificar sin ejecutar produce parálisis.

3. DESCOMPOSICIÓN EN ESPECIALISTAS
   - Dividir una tarea grande en misiones pequeñas, cada una con su propio
     prompt especializado (un "equipo"). Un coordinador reparte y reúne.
   - Clave: especialistas COMPLEMENTARIOS, no redundantes; máximo 3-4. Más
     especialistas = más ruido, no más inteligencia.

4. BUCLE CON MEMORIA
   - Entre pasos, el estado se guarda FUERA del modelo (archivo, lista de
     hechos): qué se decidió, qué falta, qué falló. Cada paso lee ese estado.
   - Clave: el contexto del modelo se llena y olvida; el archivo no.

## Reglas de oro para que un bucle no degenere

- LÍMITE DE ITERACIONES SIEMPRE (2-4). Los bucles "hasta que quede perfecto"
  degeneran: el modelo empieza a deshacer sus propios aciertos.
- CONDICIÓN DE PARADA VERIFICABLE: "el crítico responde APROBADO" o "pasan los
  tests" — nunca "cuando esté bien".
- FORMATOS PARSEABLES entre pasos: si el coordinador tiene que "entender" la
  salida libre de otro agente, el bucle es frágil. Exige formatos fijos
  ("VEREDICTO: APROBADO|MEJORAR") y parsea con tolerancia.
- LIMPIA LA SALIDA: algunos modelos emiten razonamiento interno
  (<think>...</think>); elimínalo antes de parsear o contaminará el bucle.
- CADA ROL, SU PROMPT: el crítico no puede ser el mismo prompt que el
  generador o se dará la razón a sí mismo. Cambiar el rol cambia el juicio.
- MIDE EL PROGRESO: guarda la puntuación de cada iteración. Si la iteración 3
  no mejora a la 2, para: ya llegaste al techo del modelo.
- SOLO TEXTO SIN SUPERVISIÓN: un agente autónomo genera planes, prompts y
  código COMO TEXTO. Ejecutar código o comandos generados sin revisión humana
  es la línea que separa "útil" de "peligroso".

## Cómo diseñar tu propio bucle (receta)

1. Define el objetivo y cómo se verifica que está cumplido (¡antes de nada!).
2. Decide los roles mínimos: ¿basta generador-crítico? ¿hace falta plan previo?
3. Escribe el prompt de cada rol con formato de salida fijo.
4. Fija el límite de iteraciones y la condición de parada.
5. Decide qué se guarda entre pasos y dónde (archivo de estado).
6. Prueba con UN caso pequeño de principio a fin antes de ampliarlo.
7. Añade al banco de pruebas cada fallo que encuentres.

## Errores típicos de principiante

- Bucle infinito sin límite → siempre acaba en basura o en bloqueo.
- Un solo mega-prompt que "lo hace todo" → divide en roles.
- El crítico sin criterios → aprueba todo o suspende todo, al azar.
- Confiar en que el modelo "recuerde" pasos anteriores → guárdalo en archivo.
- Medir el éxito por sensaciones → banco de pruebas con notas, siempre.

'@
$CONOC_RESOL = @'
# Apuntes maestros de resolución de problemas y auto-mejora

## El método universal (vale para código, dinero, averías y vida)

1. DEFINIR: escribe el problema en una frase y define "resuelto" con un
   criterio verificable. Un problema sin criterio de éxito no se puede
   resolver, solo se puede sufrir.
2. OBSERVAR: ¿cuándo ocurre, cuándo no, qué cambió justo antes de empezar?
   El 80% de los problemas nuevos vienen de un cambio reciente.
3. CAUSA RAÍZ: distingue síntoma (lo que se ve) de causa (lo que lo produce).
   Técnica de los 5 porqués: pregunta "¿por qué?" en cadena hasta llegar a
   algo atacable. "Llego tarde → me duermo → me acuesto tarde → miro el móvil
   en la cama → el móvil duerme en la mesilla". La causa atacable es la última.
4. GENERAR 3 OPCIONES: la rápida, la sólida y la barata. Una sola opción no es
   una decisión, es una ocurrencia. Más de cuatro es procrastinar.
5. DECIDIR con criterio: ¿cuál cumple el criterio de éxito con menos riesgo?
   Regla clave: si la decisión es REVERSIBLE, decide rápido y prueba; si es
   IRREVERSIBLE, para y analiza el peor caso de cada opción.
6. EJECUTAR el paso más pequeño primero: algo que se pueda hacer en 5 minutos.
   El progreso inmediato desbloquea el resto y da información real.
7. VERIFICAR contra el criterio del paso 1. Sin verificación no hay solución,
   hay esperanza.
8. PLAN B definido de antemano: cuál es la segunda mejor opción y qué señal
   exacta la activa ("si el viernes sigue pasando X, entonces B").

## Técnicas de diagnóstico (encontrar la causa)

- AISLAR VARIABLES: cambia UNA cosa cada vez y observa. Cambiar tres a la vez
  destruye la información.
- BISECCIÓN: corta el problema por la mitad. ¿El fallo está en la primera
  mitad o en la segunda? Repite. Encuentra 1 línea entre 1000 en 10 pasos.
- SUSTITUCIÓN: prueba con un elemento que sabes que funciona (otra bombilla,
  otro cable, otro archivo, otro usuario). Si desaparece el fallo, ya sabes
  dónde estaba.
- DEL MÁS BARATO AL MÁS CARO: comprueba primero lo que cuesta 10 segundos
  (¿está enchufado? ¿hay guardado un cambio?) antes de lo que cuesta una tarde.
- PROBLEMAS INTERMITENTES: no se cazan al vuelo, se cazan con registro. Anota
  fecha, hora y condiciones cada vez que ocurre; el patrón aparece en la lista.
- ¿QUÉ CAMBIÓ?: ante algo que funcionaba y dejó de funcionar, la primera
  pregunta siempre es qué se instaló, actualizó, movió o tocó justo antes.

## Trampas mentales que arruinan soluciones

- Enamorarse de la primera hipótesis y buscar solo pruebas a favor. Antídoto:
  intenta DEMOSTRAR QUE TU HIPÓTESIS ES FALSA; si sobrevive, es buena.
- Arreglar el síntoma: desaparece hoy, vuelve el mes que viene más caro.
- "Ya lo intenté y no funcionó": ¿lo intentaste igual o parecido? Los detalles
  de ejecución importan más que la idea.
- Parálisis por análisis: si la decisión es reversible y barata, probar ES la
  forma más rápida de analizar.
- Resolver el problema equivocado: cada cierto tiempo relee tu definición del
  paso 1 y pregúntate si sigues atacando eso.

## El bucle de auto-mejora (kaizen personal)

1. MIDE algo concreto de tu semana (horas, euros, errores, ejercicios hechos).
   Sin número no hay mejora, hay sensaciones.
2. RETROSPECTIVA de 3 preguntas: ¿qué funcionó? ¿qué no? ¿qué UNA cosa cambio
   la semana que viene? Una sola: cambiar cinco cosas es no cambiar ninguna.
3. APLICA el cambio y vuelve a medir. Compara contra la semana anterior, no
   contra el ideal.
4. REGISTRA lo aprendido en una nota corta (qué probé → qué pasó → qué haré).
   Las lecciones no escritas se pagan dos veces.
- Regla del sistema, no del objetivo: "correr 3 veces por semana" (sistema)
  vence a "correr un maratón" (objetivo) porque se puede cumplir cada semana.
- Mejora del 1%: mejorar un poco algo que haces cada día vale más que mejorar
  mucho algo que haces una vez al año.

## Cómo pedir ayuda bien (a personas o a una IA)

Un buen informe de problema multiplica la calidad de la ayuda:
1. Qué intentabas conseguir.
2. Qué hiciste exactamente (pasos reproducibles).
3. Qué esperabas que pasara y qué pasó en su lugar (mensaje de error completo).
4. Qué has probado ya y qué resultado dio.

'@
$BANCO_PROG = @'
[
  {"pregunta": "Escribe una función en Python que devuelva los N primeros números primos. Debe manejar N=0.",
   "criterios": "Función correcta y ejecutable que devuelve lista de primos (2,3,5,7,...); con N=0 devuelve lista vacía sin error."},
  {"pregunta": "¿Qué imprime este código y por qué?\nx = [1, 2, 3]\ny = x\ny.append(4)\nprint(x)",
   "criterios": "Debe decir que imprime [1, 2, 3, 4] porque y = x no copia la lista: ambas variables referencian el mismo objeto."},
  {"pregunta": "Encuentra el bug:\ndef media(numeros):\n    total = 0\n    for n in numeros:\n        total += n\n    return total / len(numeros)",
   "criterios": "Debe detectar que con lista vacía falla por división entre cero (len=0), y proponer manejarlo (devolver 0, None o lanzar error claro)."},
  {"pregunta": "¿Qué está mal en esta línea y cómo se arregla?\nquery = \"SELECT * FROM usuarios WHERE nombre = '\" + nombre_usuario + \"'\"",
   "criterios": "Debe identificar inyección SQL y proponer consultas parametrizadas (placeholders ? o %s con parámetros separados). Concatenar entrada del usuario en SQL es la vulnerabilidad."},
  {"pregunta": "¿Cuál es la complejidad de buscar un elemento en una lista de Python frente a buscarlo en un set, y qué implicación práctica tiene dentro de un bucle?",
   "criterios": "Lista O(n), set/diccionario O(1). Dentro de un bucle, buscar en lista da O(n²) y conviene convertir a set para obtener O(n)."},
  {"pregunta": "¿Por qué es peligroso def acumular(elemento, lista=[])? Explica y da la versión correcta.",
   "criterios": "El valor por defecto mutable se crea UNA vez y se comparte entre llamadas. Correcto: lista=None y dentro 'if lista is None: lista = []'."},
  {"pregunta": "Mejora este prompt para un modelo de IA: 'hazme un resumen del texto'. Escribe la versión mejorada.",
   "criterios": "La versión mejorada debe añadir varias de: longitud concreta (p.ej. 3 frases), audiencia, formato de salida, delimitadores para el texto, instrucción de no inventar. Debe ser un prompt completo, no consejos."},
  {"pregunta": "Diseña en 5 pasos un bucle agéntico generador-crítico para escribir un artículo, indicando la condición de parada.",
   "criterios": "Debe incluir: generar borrador, crítico con criterios concretos, revisión con la crítica, límite de iteraciones (2-4), y condición de parada verificable (aprobado del crítico o máximo de rondas)."},
  {"pregunta": "Escribe una función recursiva factorial(n) en Python indicando claramente el caso base, y di qué pasa si se llama con n=-1 tal cual.",
   "criterios": "Función correcta con caso base (n<=1 o n==0 devuelve 1); debe reconocer que con -1 sin protección hay recursión infinita (RecursionError) y idealmente proponer validar n>=0."},
  {"pregunta": "Dame exactamente 3 casos límite que probarías en una función dividir(a, b) y qué esperas en cada uno.",
   "criterios": "Exactamente 3 casos con expectativa: divisor cero (error controlado), negativos (signo correcto), decimales/enteros grandes o a=0. Deben ser casos límite reales con resultado esperado."}
]

'@
$BANCO_SOL = @'
[
  {"pregunta": "Tu ordenador va lento desde ayer. Describe paso a paso tu proceso para encontrar la causa antes de tocar nada.",
   "criterios": "Debe empezar por '¿qué cambió ayer?' (instalaciones, actualizaciones), observar/medir (administrador de tareas, qué proceso consume), aislar variables una a una, y NO proponer reinstalar o formatear a ciegas como primer paso."},
  {"pregunta": "Aplica la técnica de los 5 porqués a este problema: 'Siempre llego tarde al trabajo'. Inventa una cadena plausible completa.",
   "criterios": "Cadena encadenada de al menos 3-5 porqués que termina en una causa raíz ATACABLE (un hábito o decisión concreta), no en una excusa genérica."},
  {"pregunta": "Explica la diferencia entre síntoma y causa raíz con un ejemplo cotidiano concreto.",
   "criterios": "Definición correcta de ambos y un ejemplo donde se vea que atacar el síntoma no evita que el problema vuelva (p.ej. tomar analgésico vs corregir postura)."},
  {"pregunta": "Tienes dos soluciones para un problema: una rápida pero frágil y una lenta pero sólida. ¿Con qué criterios decides cuál aplicar?",
   "criterios": "Debe mencionar reversibilidad de la decisión, urgencia/coste de esperar, y coste del error si falla. Idealmente: rápida si es reversible y urgente; sólida si el error es caro o la decisión irreversible."},
  {"pregunta": "Una lámpara no enciende. Ordena los pasos de diagnóstico del más barato al más caro.",
   "criterios": "Orden lógico de aislamiento: interruptor/enchufada, probar la bombilla en otra lámpara (sustitución), probar otro aparato en ese enchufe, revisar el cuadro eléctrico, y solo al final electricista. Debe cambiar una variable cada vez."},
  {"pregunta": "Divide el problema 'quiero ahorrar más dinero' en 3 sub-problemas concretos y atacables, y di cuál atacarías primero y por qué.",
   "criterios": "3 sub-problemas medibles (saber en qué se va el dinero, reducir un gasto concreto, automatizar ahorro...) y una elección justificada, típicamente empezar por medir/registrar gastos porque desbloquea los demás."},
  {"pregunta": "¿Qué es un plan B bien definido? Da un ejemplo que incluya la señal exacta que lo activa.",
   "criterios": "Plan B = segunda mejor opción decidida ANTES de ejecutar el plan A, con una señal concreta y verificable de activación (fecha límite o umbral medible), no 'si va mal ya veremos'."},
  {"pregunta": "Diseña un bucle de auto-mejora semanal en 4 pasos para cualquier hábito.",
   "criterios": "Debe incluir: medir algo concreto, retrospectiva (qué funcionó/qué no), elegir UN solo cambio para la semana siguiente, y volver a medir/registrar lo aprendido."},
  {"pregunta": "Un fallo ocurre solo de vez en cuando y nunca cuando lo estás mirando. ¿Cuál es tu estrategia para cazarlo?",
   "criterios": "Registrar cada aparición (fecha, hora, condiciones, qué se estaba haciendo) para encontrar el patrón; intentar aumentar la frecuencia reproduciendo las condiciones; no concluir nada de un solo caso."},
  {"pregunta": "Tu script de 100 líneas falla sin mensaje de error claro. Explica cómo usar la bisección para encontrar la línea culpable y cuántos pasos te costaría aproximadamente.",
   "criterios": "Dividir por mitades (comentar/aislar mitad del código o poner una traza en medio), decidir en qué mitad está el fallo, repetir. Aproximadamente log2(100) ≈ 7 pasos."}
]

'@
# Escribir en UTF-8 SIN BOM (Ollama y Python lo requieren limpio)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText("$DIR\Modelfile", $MODELFILE.Replace("__BASE__", $BASE), $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\maestro.Modelfile", $MAESTRO, $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\forjador.Modelfile", $FORJADOR, $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\alquimista.Modelfile", $ALQUIMISTA, $utf8)
[IO.File]::WriteAllText("$DIR\habilidades\resolutor.Modelfile", $RESOLUTOR, $utf8)
[IO.File]::WriteAllText("$DIR\chat_memoria.py", $CHAT, $utf8)
[IO.File]::WriteAllText("$DIR\cerebro.py", $CEREBRO, $utf8)
[IO.File]::WriteAllText("$DIR\biblioteca.py", $BIBLIOTECA, $utf8)
[IO.File]::WriteAllText("$DIR\examen.py", $EXAMEN, $utf8)
New-Item -ItemType Directory -Force -Path "$DIR\conocimiento" | Out-Null
[IO.File]::WriteAllText("$DIR\conocimiento\programacion.md", $CONOC_PROG, $utf8)
[IO.File]::WriteAllText("$DIR\conocimiento\ingenieria_de_prompts.md", $CONOC_PROMPTS, $utf8)
[IO.File]::WriteAllText("$DIR\conocimiento\bucles_agenticos.md", $CONOC_BUCLES, $utf8)
[IO.File]::WriteAllText("$DIR\conocimiento\resolucion_de_problemas.md", $CONOC_RESOL, $utf8)
[IO.File]::WriteAllText("$DIR\preguntas_programacion.json", $BANCO_PROG, $utf8)
[IO.File]::WriteAllText("$DIR\preguntas_soluciones.json", $BANCO_SOL, $utf8)

# --------------------------------------------- 5. Descargar modelos y crear todo
Write-Host "[5/6] Descargando $BASE y creando los asistentes (puede tardar varios minutos)..."
ollama pull $BASE
ollama pull nomic-embed-text
ollama create casanostra -f "$DIR\Modelfile"
ollama create maestro    -f "$DIR\habilidades\maestro.Modelfile"
ollama create forjador   -f "$DIR\habilidades\forjador.Modelfile"
ollama create alquimista -f "$DIR\habilidades\alquimista.Modelfile"
ollama create resolutor  -f "$DIR\habilidades\resolutor.Modelfile"
if (Get-Command python -ErrorAction SilentlyContinue) {
  try { python "$DIR\biblioteca.py" indexar "$DIR\conocimiento" } catch { Write-Host "  AVISO: indexa luego con: python $DIR\biblioteca.py indexar $DIR\conocimiento" }
}

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
Write-Host "  ollama run resolutor     -> experto en resolver problemas"
if (Get-Command python -ErrorAction SilentlyContinue) {
  Write-Host "  python $DIR\chat_memoria.py            -> chat con memoria automatica"
  Write-Host "  python $DIR\cerebro.py `"objetivo`"      -> agente autonomo con equipo"
  Write-Host "  python $DIR\biblioteca.py indexar <carpeta>  -> indexar tus documentos"
  Write-Host "  python $DIR\biblioteca.py `"pregunta`"   -> preguntar a tus documentos"
  Write-Host "  python $DIR\examen.py <modelo1> <modelo2>    -> banco de pruebas con notas"
} else {
  Write-Host "  (Para los programas .py instala Python:"
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
