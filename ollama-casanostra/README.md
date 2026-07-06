# Casanostra — asistente local gratuito para Ollama

Un asistente de IA que corre 100% en tu ordenador, sin cuotas, sin límites de
tokens y sin conexión a internet una vez descargado. Usa un modelo de pesos
abiertos (Qwen3, licencia Apache 2.0) con una configuración y un prompt de
sistema que imitan el estilo de trabajo de los mejores asistentes comerciales.

**Importante y honesto:** esto NO es una copia de Claude Fable 5 ni de ningún
modelo de Anthropic. Los pesos de esos modelos son propietarios y no existen en
GitHub ni en ningún sitio; cualquier repositorio que diga ofrecerlos es falso o
malware. Lo que sí puedes tener gratis es el mejor modelo abierto que quepa en
tu máquina, bien configurado — y eso es esto.

## Instalación (3 pasos)

1. Instala Ollama: https://ollama.com/download
2. Descarga esta carpeta a tu ordenador
3. Ejecuta:

```bash
bash instalar.sh
```

El script detecta tu RAM, descarga el modelo base adecuado y crea el asistente.

## Uso

```bash
ollama run casanostra          # chat normal en la terminal
python3 chat_memoria.py        # chat con memoria persistente entre sesiones
```

## Qué modelo base te toca según tu hardware

| RAM disponible | Modelo base | Calidad aproximada |
|---|---|---|
| 32 GB o más | `qwen3:30b-a3b` | La mejor calidad local en hardware de consumo |
| 16 GB | `qwen3:8b` | Muy buena para uso general y código |
| 8 GB | `qwen3:4b` | Correcta para tareas cotidianas |
| menos de 8 GB | `qwen3:1.7b` | Básica, pero funcional |

Alternativas que puedes poner en la línea `FROM` del Modelfile:
`gemma3` (Google, muy buena en español), `qwen2.5-coder:14b` (especializada en
código), `deepseek-r1` (razonamiento). Catálogo completo: https://ollama.com/library

## Cómo "incrementar" el asistente

- **Más contexto:** sube `num_ctx` en el Modelfile (consume más RAM).
- **Cambiar personalidad:** edita el bloque `SYSTEM` y ejecuta de nuevo
  `ollama create casanostra -f Modelfile`.
- **Memoria:** usa `/recordar <dato>` dentro de `chat_memoria.py`; se guarda en
  `memoria.md` y se carga automáticamente en cada sesión.
- **Modelo más nuevo:** cambia el `FROM` cuando salga algo mejor en
  ollama.com/library — el resto de la configuración se conserva.

Todo lo anterior es gratuito y corre en local: no gasta tokens de ninguna
suscripción y nadie puede bloquearlo.

## Habilidades incluidas (carpeta `habilidades/`)

```bash
ollama create maestro    -f habilidades/maestro.Modelfile     # tutor personal
ollama create forjador   -f habilidades/forjador.Modelfile    # programador senior
ollama create alquimista -f habilidades/alquimista.Modelfile  # crea nuevas habilidades
```

Luego: `ollama run maestro`, `ollama run forjador`, etc.

## Agente autónomo "cerebro" (super cerebro con equipo)

`cerebro.py` es un agente que, dado un objetivo, monta automáticamente un
equipo de especialistas (estratega → alquimista → equipo → crítico), genera
sus prompts, itera hasta que el crítico aprueba, y guarda el resultado más
las habilidades nuevas en `habilidades_generadas/`:

```bash
python3 cerebro.py "quiero aprender a invertir en fondos indexados"
```

Por seguridad, el agente solo genera texto (planes, prompts, código como
texto): nunca ejecuta comandos por sí mismo — tú revisas e instalas.

## Biblioteca (RAG local): pregunta a TUS documentos

`biblioteca.py` indexa tus apuntes (.txt y .md) y hace que el asistente
responda citando tus propios archivos en vez de solo su memoria:

```bash
ollama pull nomic-embed-text                        # solo la primera vez
python3 biblioteca.py indexar ~/Documentos/apuntes  # crea el índice
python3 biblioteca.py "¿qué dicen mis apuntes sobre fondos indexados?"
```

Sin dependencias externas y 100% local: tus documentos nunca salen de tu
ordenador.

## Interfaz gráfica web (Open WebUI)

```bash
bash interfaz.sh
```

Instala Open WebUI (con Docker si lo tienes; si no, con pip) y te da un chat
tipo web en http://localhost:3000 con historial, subida de documentos y
selector de modelos. Todo local.

## Memoria automática

`chat_memoria.py` ahora guarda memoria él solo: al salir de cada sesión, el
propio modelo resume la conversación (decisiones, datos, tareas pendientes) y
lo añade a `memoria.md`, que se carga automáticamente la próxima vez. El
comando `/recordar` sigue disponible para guardar cosas a mano.

## Banco de pruebas: notas objetivas para tus modelos

```bash
python examen.py casanostra llama3.2      # examina y compara modelos
```

Pasa un examen de 10 preguntas (matemáticas, lógica, trampas de invención,
código, seguimiento de instrucciones...) y un modelo juez pone nota 0-10 a
cada respuesta. La primera vez crea `preguntas.json` — edítalo con preguntas
de lo que TÚ uses. El historial queda en `resultados.md` para comparar
modelos y prompts en el tiempo antes de cambiar nada a ciegas.

## Instalador todo-en-uno

`instalar_todo.sh` es auto-contenido (incluye dentro todos los archivos de
esta carpeta): instala Ollama + Claude Code, elige modelo según tu RAM y crea
los 4 asistentes de una sola vez. Es el único archivo que necesitas llevarte.
