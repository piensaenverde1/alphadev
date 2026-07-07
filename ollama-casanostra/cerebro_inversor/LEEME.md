# Carpeta del Cerebro Inversor

Tu bóveda de análisis de empresas (funciona como un Obsidian casero, en
markdown plano, y se indexa en tu biblioteca RAG).

Flujo de trabajo:
1. Copia plantilla_analisis_empresa.md → nombre de la empresa (p.ej. inditex_2026-07.md)
2. Pega en la ficha los datos de las cuentas anuales/informes oficiales.
3. Pide el análisis:  ollama run valorador   y pega la ficha con los datos.
4. Guarda la ficha completada aquí y reindexa:
       python biblioteca.py indexar cerebro_inversor
5. Consulta tu criterio acumulado:
       python biblioteca.py "¿qué tesis escribí sobre [empresa] y qué la invalidaría?"

También guarda aquí tu diario_decisiones.md (cada compra/venta: fecha, precio,
tesis en 3 frases, qué te haría cambiar de opinión) y tus autopsias de errores.
