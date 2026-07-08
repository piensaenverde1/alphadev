# Capa 1: RAW — tus fuentes brutas

Guarda aquí los documentos originales SIN tocar: cartas anuales de Buffett
(berkshirehathaway.com/letters), informes anuales (10-K), artículos.
Convención: carta_1989.md, 10k_empresa_2025.md (texto plano/markdown).

Flujo de ingesta (una fuente cada vez, como en el método):
1. Guarda el documento aquí.
2. ollama run casanostra → pega el documento y pide: "Según REGLAS.md, extrae
   los conceptos clave de esta fuente con citas textuales y dame el contenido
   de una nota wiki por concepto (plantilla en wiki/plantilla_concepto.md)".
3. Guarda/actualiza las notas en wiki/ y reindexa:
   python biblioteca.py indexar cerebro_inversor
