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
