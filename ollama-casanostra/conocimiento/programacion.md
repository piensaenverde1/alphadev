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
