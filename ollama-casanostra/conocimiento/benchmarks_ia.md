# Los benchmarks de la IA: qué miden y cuáles se pueden probar en local

Un benchmark es un examen estandarizado para comparar modelos de IA. Saber
qué mide cada uno te permite leer las "notas" de los modelos con criterio en
vez de tragarte el marketing.

## Agrupados por capacidad

### Conocimiento y cultura
- MMLU: conocimientos generales, 57 materias. MMLU-Pro: versión mucho más dura.
- GPQA Diamond: ciencia nivel doctorado (física, química, biología).
- TriviaQA / SimpleQA: cultura general y precisión factual.
- Scale SEAL: tareas profesionales (legal, finanzas).

### Razonamiento
- HLE (Humanity's Last Exam): preguntas extremadamente difíciles multidisciplina.
- ARC-AGI: razonamiento abstracto / inteligencia general.
- BBH (Big Bench Hard): razonamiento complejo.
- HellaSwag: sentido común. Winogrande: lenguaje y referencias (correferencia).
- DROP: comprensión lectora con cálculos.

### Matemáticas (de menor a mayor dificultad)
- GSM8K: matemáticas escolares. MGSM: lo mismo en varios idiomas.
- MATH / MATH-500: matemáticas avanzadas y selección difícil.
- AIME 2024/2025: olimpiadas. FrontierMath: matemáticas de investigación (brutal).

### Programación
- HumanEval / MBPP: escribir funciones en Python.
- LiveCodeBench: problemas recientes (evita memorización).
- Aider Polyglot: editar código en varios lenguajes. SciCode: programación científica.
- SWE-bench Verified / Pro: arreglar bugs REALES de repositorios de GitHub.

### Agentes y uso de herramientas
- BFCL: llamadas a funciones correctas. TAU-bench: agentes que usan herramientas.
- Terminal Bench: uso de terminal Linux.
- OSWorld: manejar un ordenador completo. WebArena: tareas en la web.
- BrowseComp: buscar información en internet.

### Multimodal (texto + imágenes)
- MMMU / MMMU-Pro / MMMU-Val: comprensión de texto e imágenes.

### Veracidad y seguridad
- TruthfulQA / HHEM: evitar alucinaciones (inventarse cosas).
- HealthBench: medicina y salud. CyberGym: ciberseguridad.
- IFEval: seguir instrucciones al pie de la letra.

### Conversación y preferencia humana
- Chatbot Arena (Arena Elo): votos de usuarios reales entre modelos.
- Arena-Hard: conversaciones difíciles. MT-Bench / WildBench: calidad conversacional.
- LiveBench: evaluación continua con preguntas nuevas. GDPval: tareas complejas generales.

## Cuáles NO se pueden replicar en tu sistema local (y por qué)
Tu examen local juzga RESPUESTAS DE TEXTO con un modelo-juez. Por eso NO se
pueden reproducir de verdad:
- MMMU/MMMU-Pro/Val: necesitan que el modelo VEA imágenes (el tuyo no ve).
- OSWorld / WebArena: necesitan controlar un ordenador o navegador real.
- SWE-bench (Verified/Pro): necesitan clonar repos y EJECUTAR sus tests.
- TAU-bench / BFCL (completo): necesitan ejecutar herramientas de verdad.
- BrowseComp: necesita internet en vivo (lo cubre internauta.py, no el examen).
- LiveBench / Arena Elo: preguntas nuevas cada semana o votos humanos.

En el mega examen (preguntas_benchmark.json) estos aparecen como PREGUNTAS DE
HONESTIDAD: comprueban si el modelo reconoce que NO puede ver una imagen,
navegar o ejecutar tests sin inventárselo. Reconocer los propios límites es,
en un sistema local, tan valioso como acertar.

## Cómo leer las notas de tu modelo local
- Un modelo de 8B NO puntúa como un modelo frontera (Fable 5, etc.): sacará
  bien en conocimiento, sentido común, código básico y honestidad; flojo en
  matemáticas de olimpiada (AIME), ciencia de doctorado (GPQA) y matemática
  de investigación (FrontierMath). Eso es lo esperado y correcto.
- El valor no es la nota absoluta: es el DIAGNÓSTICO de en qué categoría
  flojea, para reforzar esa área con conocimiento en la biblioteca o para
  saber cuándo NO fiarte de su respuesta.
