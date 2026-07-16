# CÓMO LLEVAR TU CASANOSTRA A CHATGPT O GEMINI

Tu sistema no depende del modelo: el valor es TU contexto (personalidades +
conocimiento). Aquí lo trasplantas. Generado el 2026-07-16.

Archivos de esta carpeta:
- INSTRUCCIONES_MAESTRAS.md  -> el "cerebro" completo en un asistente que cambia de rol.
- especialistas/*.md         -> 18 personalidades sueltas (una por rol).
- CONOCIMIENTO_COMPLETO.md   -> todo tu saber para subir como base de conocimiento.

═══════════════════════════════════════════════════════════════
CHATGPT (Plus) — crear un "GPT personalizado"
═══════════════════════════════════════════════════════════════
1. Ve a chatgpt.com -> "Explorar GPT" -> "Crear".
2. En la pestaña "Configurar", pega el contenido de INSTRUCCIONES_MAESTRAS.md
   en el campo "Instrucciones".
3. En "Conocimiento" -> "Subir archivos", sube CONOCIMIENTO_COMPLETO.md
   (si es muy grande, sube los .md de la carpeta conocimiento/ por separado).
4. Ponle nombre "Casanostra", guarda, y ya puedes hablar con él.
   Prueba: "modo inversor: quiero empezar a invertir".

Sin Plus (gratis): abre un chat nuevo, pega INSTRUCCIONES_MAESTRAS.md como
primer mensaje diciendo "Actúa según estas instrucciones a partir de ahora",
y pega el conocimiento que necesites cuando lo necesites.

═══════════════════════════════════════════════════════════════
GEMINI — crear un "Gem"
═══════════════════════════════════════════════════════════════
1. Ve a gemini.google.com -> menú lateral -> "Gems" -> "Nuevo Gem".
2. Pega INSTRUCCIONES_MAESTRAS.md en las instrucciones del Gem.
3. Sube CONOCIMIENTO_COMPLETO.md como archivo de conocimiento (o los .md sueltos).
4. Guárdalo como "Casanostra" y úsalo.

Sin Gems: pega INSTRUCCIONES_MAESTRAS.md al inicio de una conversación.

═══════════════════════════════════════════════════════════════
UN ESPECIALISTA CONCRETO (recomendado para empezar)
═══════════════════════════════════════════════════════════════
En vez del asistente completo, crea un GPT/Gem por rol usando los archivos de
especialistas/. Ej: para inversión, usa especialistas/inversor.md como
instrucción y sube solo conocimiento/inversiones.md y grandes_inversores.md.
Más enfocado = mejores respuestas.

═══════════════════════════════════════════════════════════════
QUÉ GANAS Y QUÉ NO
═══════════════════════════════════════════════════════════════
GANAS: la potencia de modelos más grandes (mejor razonamiento, imágenes, voz,
internet real) con TU forma de trabajar y TU conocimiento.
NO SE TRASLADA: los programas Python (examen, cerebro, biblioteca...) son de
tu sistema local con Ollama; en ChatGPT/Gemini el equivalente lo hacen sus
propias funciones. Y OJO: en la nube tus datos SÍ salen de tu ordenador
(privacidad distinta a la de casanostra local). Para lo sensible, usa el local.

Regla de oro del framework 5C: el modelo se alquila, el contexto es tuyo.
Ahora tu contexto vive en cualquier IA que elijas.
