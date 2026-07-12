#!/usr/bin/env python3
"""TRADUCTOR — convierte órdenes en español natural a comandos de PowerShell.

Es el cerebro del comando 'habla': recibe una frase coloquial ("crea una
carpeta en el escritorio que se llame facturas") y devuelve el comando
PowerShell equivalente, o una respuesta si era una pregunta, o un NO
razonado si es peligrosa. NUNCA ejecuta nada: eso lo decide el usuario.

Uso interno:  python traductor.py "frase en español"
"""

import json
import re
import sys
from urllib import request as urlreq

MODELO = "casanostra"
URL = "http://localhost:11434/api/chat"

SISTEMA = """Eres un traductor de órdenes habladas en español de España (coloquial, como se habla en Barcelona) a comandos de Windows PowerShell.

Responde SOLO en uno de estos tres formatos, sin markdown, sin ``` y sin explicaciones alrededor:

1. Si la frase pide UNA ACCIÓN sobre el ordenador (crear carpetas/archivos, mover, listar, abrir programas, guardar texto...): escribe el comando o comandos PowerShell, uno por línea, completos y ejecutables.
2. Si la frase es una PREGUNTA o conversación (no una acción sobre el sistema): responde con una sola línea que empiece exactamente por "ECHO: " seguida de la respuesta breve.
3. Si la acción es PELIGROSA (borrar cosas que el usuario no ha pedido borrar explícitamente, formatear, tocar carpetas del sistema, desactivar seguridad) o imposible desde PowerShell: responde una sola línea que empiece exactamente por "NO: " y el motivo en una frase.

Reglas de traducción:
- Escritorio = [Environment]::GetFolderPath('Desktop'). Carpeta personal = $HOME. Documentos = [Environment]::GetFolderPath('MyDocuments').
- "carpeta" = New-Item -ItemType Directory -Force. "archivo/nota/apunta" = crear o añadir con Set-Content/Add-Content.
- Fechas y horas: usa Get-Date -Format 'yyyy-MM-dd_HH-mm' cuando pidan "con fecha y hora".
- Entiende coloquialismos: "ves guardando ahí" = guardar en esa carpeta; "hazme/móntame/prepárame X" = crear X; "enséñame/muestra" = listar o mostrar; "tira/lanza" = ejecutar.
- Si la frase encadena varias acciones, un comando por línea en orden.
- Si pide programar algo repetido (cada X horas/días), usa Register-ScheduledTask correctamente o, si es complejo, responde NO: y sugiere usar cadencia.ps1.
- Nunca borres, sobrescribas ni muevas nada que la orden no pida explícitamente. Ante ambigüedad de borrado: NO:.
- Comandos simples y estándar; nada de descargar ni ejecutar código de internet salvo que lo pidan explícitamente con la URL.
"""


def main() -> None:
    frase = " ".join(sys.argv[1:]).strip()
    if not frase:
        print("NO: no he recibido ninguna frase")
        return
    datos = json.dumps({
        "model": MODELO, "stream": False,
        "messages": [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": frase},
        ],
    }).encode()
    req = urlreq.Request(URL, data=datos, headers={"Content-Type": "application/json"})
    try:
        with urlreq.urlopen(req, timeout=300) as r:
            texto = json.loads(r.read())["message"]["content"]
    except OSError:
        print("NO: no conecto con Ollama (arranca 'ollama serve')")
        return
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()
    # Quitar cercas de código si el modelo desobedece
    texto = re.sub(r"^```\w*\n?|```$", "", texto, flags=re.M).strip()
    print(texto)


if __name__ == "__main__":
    main()
