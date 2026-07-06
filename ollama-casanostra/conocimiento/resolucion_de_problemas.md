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
