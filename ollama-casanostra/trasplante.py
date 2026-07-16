#!/usr/bin/env python3
"""TRASPLANTE — empaqueta tu sistema Casanostra para llevarlo a otra IA (ChatGPT, Gemini...).

El framework 5C en acción: el modelo se alquila, el CONTEXTO es tuyo. Este
programa lee tus personalidades (habilidades/) y tu conocimiento (conocimiento/)
y genera una carpeta 'trasplante/' con:

  - INSTRUCCIONES_MAESTRAS.md  -> el "quién eres" para pegar como instrucción de
    sistema de un GPT personalizado o un Gem de Gemini.
  - especialistas/<nombre>.md  -> cada personalidad, lista para crear un GPT/Gem por rol.
  - CONOCIMIENTO_COMPLETO.md   -> todo tu saber en un archivo para SUBIR como base de conocimiento.
  - COMO_USAR.md               -> pasos exactos para ChatGPT y para Gemini.

Uso:
    python trasplante.py

No necesita internet ni Ollama: solo lee tus archivos locales.
"""

import re
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
SALIDA = BASE / "trasplante"


def extraer_system(modelfile: str) -> str:
    """Saca el prompt de sistema de un Modelfile (entre SYSTEM \"\"\" y \"\"\")."""
    m = re.search(r'SYSTEM\s+"""(.*?)"""', modelfile, re.S)
    return m.group(1).strip() if m else ""


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "especialistas").mkdir(exist_ok=True)

    # 1. Personalidades
    habilidades = sorted((BASE / "habilidades").glob("*.Modelfile"))
    personalidades = {}
    for hf in habilidades:
        nombre = hf.stem
        system = extraer_system(hf.read_text(encoding="utf-8"))
        if system:
            personalidades[nombre] = system
            (SALIDA / "especialistas" / f"{nombre}.md").write_text(
                f"# Instrucciones para el especialista: {nombre}\n\n"
                "Pega esto como instrucción de sistema de un GPT personalizado "
                "(ChatGPT) o un Gem (Gemini):\n\n---\n\n" + system + "\n",
                encoding="utf-8")

    # 2. Instrucción maestra (un solo asistente que sabe cambiar de rol)
    base_mf = (BASE / "Modelfile").read_text(encoding="utf-8") if (BASE / "Modelfile").exists() else ""
    base_system = extraer_system(base_mf) or "Eres un asistente útil, honesto y conciso."
    directorio = "\n".join(f"- **{n}**: {s.splitlines()[0][:90]}" for n, s in personalidades.items())
    maestra = (
        "# INSTRUCCIONES MAESTRAS — Asistente Casanostra (versión portable)\n\n"
        "Pega TODO esto como instrucción personalizada / de sistema en ChatGPT o Gemini.\n\n"
        "---\n\n" + base_system + "\n\n"
        "## Cambio de rol (especialistas)\n"
        "Cuando el usuario pida ayuda de un área, ADOPTA el rol correspondiente y "
        "sigue su método. Si el usuario escribe 'modo <nombre>', conviértete en ese "
        "especialista. Roles disponibles:\n\n" + directorio + "\n\n"
        "## Regla de honestidad (importante)\n"
        "No inventes datos, fechas ni fuentes. Si algo requiere información actual y no "
        "la tienes verificada, dilo. En temas de dinero, salud o legales: eres educación, "
        "no asesoramiento; las decisiones son del usuario. Si detectas una posible estafa "
        "(rentabilidad garantizada, urgencia, pagar para cobrar), avisa.\n")
    (SALIDA / "INSTRUCCIONES_MAESTRAS.md").write_text(maestra, encoding="utf-8")

    # 3. Conocimiento completo (para subir como archivo de base de conocimiento)
    partes = ["# BASE DE CONOCIMIENTO DE CASANOSTRA\n",
              f"Generado el {date.today()}. Súbelo como archivo de conocimiento en "
              "tu GPT personalizado o Gem, o pégalo por partes.\n"]
    for md in sorted((BASE / "conocimiento").glob("*.md")):
        partes.append(f"\n\n{'='*70}\n# TEMA: {md.stem}\n{'='*70}\n")
        partes.append(md.read_text(encoding="utf-8"))
    (SALIDA / "CONOCIMIENTO_COMPLETO.md").write_text("\n".join(partes), encoding="utf-8")

    # 4. Guía de uso
    guia = f"""# CÓMO LLEVAR TU CASANOSTRA A CHATGPT O GEMINI

Tu sistema no depende del modelo: el valor es TU contexto (personalidades +
conocimiento). Aquí lo trasplantas. Generado el {date.today()}.

Archivos de esta carpeta:
- INSTRUCCIONES_MAESTRAS.md  -> el "cerebro" completo en un asistente que cambia de rol.
- especialistas/*.md         -> {len(personalidades)} personalidades sueltas (una por rol).
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
"""
    (SALIDA / "COMO_USAR.md").write_text(guia, encoding="utf-8")

    print(f"Paquete de trasplante generado en: {SALIDA}")
    print(f"  - INSTRUCCIONES_MAESTRAS.md (el cerebro completo)")
    print(f"  - especialistas/ ({len(personalidades)} roles)")
    print(f"  - CONOCIMIENTO_COMPLETO.md (para subir)")
    print(f"  - COMO_USAR.md (pasos para ChatGPT y Gemini)")


if __name__ == "__main__":
    main()
