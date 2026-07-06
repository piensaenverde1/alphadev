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
