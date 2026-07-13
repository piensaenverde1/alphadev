#!/usr/bin/env python3
"""VIGIA — detector de modelos mejores disponibles (mejora 8).

Comprueba qué modelos tienes y, si hay internet, mira el catálogo público de
Ollama en busca de modelos recientes recomendados que podrían mejorar tu base.
NO instala nada: solo te avisa y te da el comando. Tú decides y validas con un
examen ANTES de adoptar (nunca cambies a ciegas).

Uso:
    python vigia_modelos.py

Sin dependencias externas.
"""

import json
import re
import sys
from urllib import request as urlreq

# Modelos abiertos de referencia buenos para uso general en local (2026).
# La lista es orientativa; el veredicto real lo da tu examen.py.
RECOMENDADOS = {
    "qwen3": "Qwen3 — referencia general recomendada (Apache 2.0).",
    "gemma3": "Gemma 3 (Google) — muy buena en español.",
    "qwen2.5-coder": "Qwen2.5-Coder — especializada en programación.",
    "deepseek-r1": "DeepSeek-R1 — razonamiento.",
    "llama3.3": "Llama 3.3 (Meta) — general.",
}


def instalados() -> list:
    try:
        with urlreq.urlopen("http://localhost:11434/api/tags", timeout=10) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except OSError:
        return []


def hay_internet() -> bool:
    try:
        urlreq.urlopen("https://ollama.com", timeout=5)
        return True
    except OSError:
        return False


def main():
    print("=== VIGÍA DE MODELOS ===\n")
    tengo = instalados()
    if not tengo:
        sys.exit("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")
    print("Modelos que ya tienes:")
    for m in tengo:
        print(f"  - {m}")

    base = [m for m in tengo if m.startswith(("qwen3", "gemma", "llama", "deepseek"))]
    print(f"\nTu modelo base parece: {base[0] if base else '(no detectado)'}")

    print("\nRecomendados de referencia para uso general en local:")
    for clave, desc in RECOMENDADOS.items():
        tiene = any(m.startswith(clave) for m in tengo)
        marca = "✓ ya lo tienes" if tiene else "→ probar: ollama pull " + clave
        print(f"  {desc}\n      {marca}")

    print("\nCómo actualizar tu base con criterio (nunca a ciegas):")
    print("  1. ollama pull <modelo-nuevo>")
    print("  2. Edita la línea FROM del Modelfile y ejecuta actualizar.ps1")
    print("  3. VALIDA con un examen antes de adoptar:")
    print("     python examen.py preguntas_programacion.json <modelo-nuevo> --juez llama3.2")
    print("  4. Compara la nota en resultados.md. Solo adopta si mejora.")

    if hay_internet():
        print("\n(Tienes internet: mira ollama.com/library para novedades recientes.)")
    else:
        print("\n(Sin internet ahora: consulta ollama.com/library cuando tengas conexión.)")


if __name__ == "__main__":
    main()
