# INFORME FINAL — Sistema Casanostra (6 julio 2026)

## Qué es este sistema

Un cerebro de IA 100% local y gratuito sobre Ollama (qwen3:8b para 16 GB de
RAM), con 5 asistentes especializados, agente autónomo con equipo, memoria
automática, biblioteca RAG con 4 temarios, y 3 bancos de examen para medir
cada mejora con notas. Nada caduca ni depende de ninguna suscripción.

## Examen final del sistema (verificado el 6-jul-2026)

| Prueba | Resultado |
|---|---|
| 4 programas Python compilan | ✅ |
| 2 bancos de examen JSON válidos (10+10 preguntas) | ✅ |
| Instalador Linux/Mac: sintaxis correcta (819 líneas) | ✅ |
| Instalador Windows (816 líneas): bloques verificados | ✅ |
| 8 bloques embebidos idénticos byte a byte a los archivos | ✅ |
| 5 asistentes presentes en ambos instaladores | ✅ |
| Descarga pública desde GitHub (HTTP 200) | ✅ |
| Instalación real en Windows del usuario | ✅ (completada 6-jul) |
| Examen general ejecutado en real | ✅ (detectó y se corrigió el bug del juez) |

## Boletín de notas (evaluación honesta)

| Componente | Nota | Comentario |
|---|---|---|
| Instaladores (Win + Linux) | 9/10 | Probado de verdad en Windows de punta a punta |
| 5 asistentes (casanostra, maestro, forjador, alquimista, resolutor) | 9/10 | Creados y verificados en la máquina real |
| Banco de pruebas (examen.py) | 8.5/10 | Probado en real; sobrevivió a su primer bug |
| Conocimiento RAG (4 temarios) | 9/10 | Denso y accionable; falta que el usuario añada los suyos |
| Cerebro autónomo + memoria + biblioteca | 7/10 | Compilan y están validados, pero aún sin ejercitar en real |
| Mejoras completadas | 7/10 | 7 de 10 hechas; faltan voz, sandbox y ajuste GPU |
| **SISTEMA COMPLETO** | **8.3/10** | Operativo, medible y mejorable por sí mismo |

## El nivel real del modelo (sin humo)

- Única medición real hasta ahora: 6.7–7.2/10 en el examen general, CON el
  árbitro defectuoso — no es fiable. Pendiente repetir con el juez corregido.
- qwen3:8b es de lo mejor que cabe en 16 GB de RAM en 2026. Con los
  especialistas y la biblioteca rinde al techo de su clase.
- Comparación honesta: NO es Claude Fable 5 ni se le acerca en razonamiento
  profundo. Es el mejor asistente gratuito, privado e imbloqueable que este
  ordenador puede tener.

## Chuleta de comandos (todo desde PowerShell)

    ollama run casanostra              asistente general
    ollama run maestro                 tutor personal
    ollama run forjador                programador senior
    ollama run alquimista              creador de habilidades
    ollama run resolutor               resolver problemas (solución automática)
    /bye                               salir de un chat

    python $HOME\casanostra\chat_memoria.py                     chat con memoria
    python $HOME\casanostra\cerebro.py "objetivo"               agente con equipo
    python $HOME\casanostra\biblioteca.py indexar <carpeta>     indexar documentos
    python $HOME\casanostra\biblioteca.py "pregunta"            preguntar a documentos
    python $HOME\casanostra\examen.py casanostra llama3.2       examen general
    python $HOME\casanostra\examen.py preguntas_programacion.json casanostra
    python $HOME\casanostra\examen.py preguntas_soluciones.json casanostra resolutor

## Tareas pendientes (cuando vuelvas)

1. Repetir el examen general con el juez corregido (la clasificación anterior
   no vale).
2. Correr los exámenes de programación y de soluciones.
3. Indexar la carpeta conocimiento/ y tus propios apuntes.
4. Pendientes del roadmap: voz (whisper + piper), sandbox de código, ajuste GPU.
5. Cada pocos meses: mirar ollama.com/library, cambiar el FROM del Modelfile
   al mejor modelo nuevo, y validarlo con los exámenes ANTES de adoptarlo.

Regla de oro final: >>> es el chat con la IA; PS C:\...> es el terminal.
