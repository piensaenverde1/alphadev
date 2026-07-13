# GUÍA MAESTRA DE CASANOSTRA

Tu sistema de IA local, gratuito y privado. Este es el mapa de TODO lo que
tienes y cómo usarlo. En Windows los comandos usan `python`; en Linux/Mac
usan `python3`. La carpeta del sistema es `~/casanostra` (en Windows
`C:\Users\jesus\casanostra`).

> Regla de oro: `>>>` = estás hablando con la IA (nada se ejecuta). `PS C:\>`
> o `$` = terminal (aquí van los comandos). Para salir de un chat: `/bye`.

---

## PRIMEROS AUXILIOS (empieza por aquí si algo falla)

| Quiero... | Comando |
|---|---|
| Poner todo el sistema al día | `powershell -File actualizar.ps1` |
| Revisar la salud del sistema | `powershell -File revision.ps1` |
| Copia de seguridad de mi trabajo | `powershell -File revision.ps1 -Copia` |
| Ver mis números (dashboard) | `python motor.py` |
| Que un experto me ayude con un error | `ollama run mecanico` |

---

## LOS 19 ASISTENTES (ollama run <nombre>)

**General y sistema**
- `casanostra` — asistente general (la base de todos).
- `mecanico` — técnico de mantenimiento del propio sistema.
- `alquimista` — fabrica nuevas habilidades a partir de un deseo tuyo.

**Aprender y crear**
- `maestro` — tutor personal (diagnostica, plan, lecciones, exámenes).
- `forjador` — programador senior con autocrítica.
- `escritor` — emails, informes y textos que consiguen su objetivo.
- `idiomas` — inglés con rol-play y correcciones.

**Resolver y organizar**
- `resolutor` — resuelve problemas y elige la solución él mismo.
- `organizador` — productividad, prioridades, anti-procrastinación.
- `analista` — de una tabla/Excel a una decisión, sin trampas estadísticas.
- `negociador` — prepara negociaciones (con rol-play de ensayo).

**Dinero (equipo financiero — todo educativo, no asesoramiento)**
- `inversor` — mentor de finanzas personales e indexados (anti-humo).
- `cazador` — busca oportunidades y negocios de coste 0 con fundamentos.
- `valorador` — analiza empresas con método value (Buffett/Graham).
- `emprendedor` — valida ideas de negocio antes de gastar.

**Vida cotidiana**
- `cocinero` — menús semanales, batch cooking, aprovechar sobras.
- `entrenador` — fuerza, cardio y hábitos (prudente, no médico).
- `guardian` — seguridad digital, phishing, qué hacer si te hackean.
- `gestor` — trámites y burocracia en España.

---

## LOS 9 PROGRAMAS (python <archivo>)

| Programa | Para qué | Ejemplo |
|---|---|---|
| `chat_memoria.py` | Chat con memoria automática entre sesiones | `python chat_memoria.py` |
| `biblioteca.py` | Preguntar a TUS documentos (RAG con citas) | `python biblioteca.py "tu pregunta"` |
| `internauta.py` | Internet si lo hay; si no, avisa y usa lo aprendido | `python internauta.py "noticias de hoy"` |
| `cerebro.py` | Agente autónomo con equipo (estratega→equipo→crítico) | `python cerebro.py "tu objetivo"` |
| `examen.py` | Examina modelos con cualquier banco de preguntas | `python examen.py preguntas_programacion.json casanostra` |
| `motor.py` | Dashboard: inventario, notas, ROI, velocidad | `python motor.py --bench` |
| `traductor.py` | Motor interno de HABLA (no se usa suelto) | (lo llama habla.ps1) |
| `segi_super_examen.py` | El súper examen SEGI (41 preguntas) | (lo usa segi_local.py) |
| `segi_local.py` | Ejecuta SEGI contra casanostra automáticamente | `python segi_local.py --rapido --juez llama3.2` |

---

## LOS 5 SCRIPTS DE POWERSHELL (powershell -File <archivo>)

| Script | Para qué |
|---|---|
| `instalar_todo.ps1` | Instalación base (histórico; usa actualizar.ps1) |
| `actualizar.ps1` | Sincroniza TODO el sistema desde GitHub y recrea los modelos |
| `revision.ps1` | Médico + copia de seguridad (`-Copia`) + podar memoria (`-Podar`) |
| `cadencia.ps1` | Tareas programadas (examen y reindexado semanal) |
| `habla.ps1` | Que PowerShell entienda castellano natural (`-Instalar`) |

---

## LA BIBLIOTECA DE CONOCIMIENTO (carpeta conocimiento/)

20 temarios maestros que el asistente CONSULTA al responder. Reindexa cuando
añadas notas: `python biblioteca.py indexar conocimiento`

Temas: programación, ingeniería de prompts, bucles agénticos, resolución de
problemas, inversiones, oportunidades, cerebro inversor, grandes inversores,
framework 5C, benchmarks de IA, negociación, escritura, productividad, salud,
cocina, emprendimiento, inglés, análisis de datos, seguridad digital, trámites.

Carpetas especiales:
- `cerebro_inversor/` — tu wiki de análisis de empresas (raw → wiki → REGLAS.md).
- `noticias/` y `conocimiento_web/` — material fresco que tú aportas o que guarda internauta.
- `cursos/` — el curso completo de grandes inversores en 6 módulos.

---

## LOS 18 EXÁMENES (python examen.py preguntas_<tema>.json casanostra)

Temas con banco propio: 5c, benchmark, cerebro_inversor, cocina, datos,
emprendimiento, escritura, grandes_inversores, ingles, inversiones,
negociacion, oportunidades, productividad, programacion, salud, seguridad,
soluciones, tramites. Más el súper examen SEGI (`segi_local.py`).

Truco: añade `--juez llama3.2` para que un modelo distinto corrija (más justo).
Los resultados se acumulan en `resultados.md`.

---

## RUTINA SEMANAL RECOMENDADA (5 minutos)

1. `powershell -File revision.ps1` — comprueba que todo está sano.
2. `powershell -File revision.ps1 -Copia` — respalda tu trabajo a un USB/nube.
3. Añade tus notas/noticias a `conocimiento/` o `noticias/` y reindexa.
4. Una vez al mes: mira ollama.com/library; si hay un modelo mejor, cambia la
   línea `FROM` del Modelfile y valida con un examen ANTES de adoptarlo.

Todo local, gratuito y sin fecha de caducidad. Educativo: las decisiones
(dinero, salud, legales) son siempre tuyas.
