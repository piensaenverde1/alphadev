# Carpeta de noticias frescas

Guarda aquí las noticias y datos económicos del día/semana como archivos .md
(copia y pega el texto de la fuente primaria + fecha + enlace). Después:

    python biblioteca.py indexar noticias

Y pregunta al cazador con material fresco ya indexado:

    python biblioteca.py "según las noticias de esta semana, ¿qué cambió y quién gana?"

O directamente pega la noticia en el chat:

    ollama run cazador
    >>> Analiza esta noticia con tu método: [pega aquí el texto]

Recuerda: el modelo NO conoce la actualidad por sí mismo. Sin material fresco
tuyo, solo puede aplicar fundamentos — que es mucho, pero no es "hoy".
