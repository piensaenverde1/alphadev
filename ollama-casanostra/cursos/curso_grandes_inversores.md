# CURSO COMPLETO: Los Grandes Inversores y tu Cerebro Inversor
# (6 módulos · estudia con MAESTRO · examina con examen.py · aplica con VALORADOR)

## Cómo estudiar este curso con tu sistema
- Cada módulo: lee el material → clase con MAESTRO → ejercicio práctico →
  no avances si fallas el repaso.
- Comando para cada clase (ejemplo módulo 1):
  ollama run maestro "Estudiemos el módulo 1 del curso de grandes inversores: Benjamin Graham. Ya leí el material; hazme el diagnóstico y empecemos."
- Consultas al material:  python biblioteca.py "¿qué es el margen de seguridad según Graham?"
- Examen final:           python examen.py preguntas_grandes_inversores.json casanostra

## MÓDULO 1 — Benjamin Graham: los cimientos (semana 1)
Objetivo: dominar los 3 conceptos que sostienen todo lo demás.
Lecciones: inversión vs especulación · Mr. Market · margen de seguridad ·
la lección del crac de 1929.
Ejercicio: escribe con tus palabras qué haría Mr. Market en una caída del 30%
y qué harías tú; guárdalo con /recordar en chat_memoria.
Lectura: "El inversor inteligente", capítulos 8 y 20 (los que Buffett señala).

## MÓDULO 2 — Warren Buffett: el compuesto y el foso (semana 2)
Objetivo: entender POR QUÉ ganó: tiempo + calidad + temperamento.
Lecciones: la trayectoria (partnership → Berkshire) · el giro See's Candies ·
foso defensivo y poder de precio · el float de los seguros · círculo de
competencia · Apple y Japón: ampliar el círculo sin traicionarlo.
Ejercicio: elige una empresa que uses a diario y descríbela con el test del
niño + identifica su foso (o su ausencia). Pásala por VALORADOR.
Lectura: una carta anual de Berkshire (empieza por la de 1989 o 2014).

## MÓDULO 3 — Charlie Munger: pensar mejor (semana 3)
Objetivo: incorporar los modelos mentales y la inversión del problema.
Lecciones: malla de modelos mentales · "invierte, siempre invierte" ·
psicología de los errores (incentivos, prueba social, exceso de confianza) ·
calidad sobre ganga.
Ejercicio: aplica la inversión a tus finanzas: lista 5 cosas que te
garantizarían arruinarte e invierte la lista en 5 reglas personales.
Lectura: "El almanaque del pobre Charlie" (o su charla de las 25 causas
del juicio erróneo).

## MÓDULO 4 — Peter Lynch: el inversor de a pie (semana 4)
Objetivo: usar tu vida diaria como radar (bien entendido) y clasificar empresas.
Lecciones: invierte en lo que conoces COMO PUNTO DE PARTIDA · tenbaggers y
dejar correr ganadoras · las 6 categorías de empresa · ratio PEG ·
"más dinero perdido preparándose para correcciones que en las correcciones".
Ejercicio: haz una lista de 5 productos/servicios que tú y tu entorno usáis
cada vez más; investiga qué empresas hay detrás (solo como candidatas a análisis).
Lectura: "Un paso por delante de Wall Street".

## MÓDULO 5 — John Bogle: la base de todo (semana 5)
Objetivo: entender por qué la indexación barata es el estándar y los costes
la única ventaja garantizada.
Lecciones: la aritmética implacable · historia del primer fondo indexado ·
comprar el pajar entero · tiempo EN el mercado vs adivinar el mercado ·
los gráficos que todo inversor debe conocer (brecha inversor medio vs índice,
impacto de perderse los mejores días, DCA vs golpe, coste de comisiones,
probabilidad de pérdida según plazo).
Ejercicio: calcula con la regla del 72 y con el ejemplo del TER (0,2% vs 2%)
cuánto te costarían 30 años de comisiones altas sobre tu aportación mensual.
Lectura: "El pequeño libro para invertir con sentido común".

## MÓDULO 6 — Síntesis + tu Cerebro Inversor (semana 6)
Objetivo: convertir el estudio en sistema propio y conectarlo con la
actualidad económica.
Lecciones: lo que los 5 tienen en común (método escrito, décadas, círculo,
costes, temperamento) · lectura de la economía actual con sus ojos (tipos
como gravedad de las valoraciones; snapshot julio 2026 en el material) ·
el patrón LLM-Wiki de 3 capas: brutos → wiki con citas → tus reglas.
Ejercicio final (proyecto):
1. Descarga 2-3 cartas de Buffett (berkshirehathaway.com/letters) y guárdalas
   en cerebro_inversor/raw/.
2. Pide a casanostra que extraiga los conceptos con cita de origen y crea
   una nota por concepto en cerebro_inversor/wiki/.
3. Escribe tu filosofía en cerebro_inversor/REGLAS.md (qué compras, qué no,
   qué te haría vender: tus reglas en frío).
4. Indexa todo:  python biblioteca.py indexar cerebro_inversor
5. Examínate:    python examen.py preguntas_grandes_inversores.json casanostra
   (aprobado = media ≥ 7; si no, repasa el módulo que falle).

## Diploma casero
Cuando apruebes el examen final y tengas tu REGLAS.md escrito, el curso está
completado: tendrás lo que el 90% no tiene — un método escrito ANTES de
invertir. Educativo, no asesoramiento; las decisiones son tuyas.
