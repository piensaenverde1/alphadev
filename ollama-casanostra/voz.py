#!/usr/bin/env python3
"""VOZ — habla con casanostra por micrófono y que te responda en voz alta.

Español de España (castellano), no latino. Escucha con Vosk (reconocimiento de
voz local y gratuito), piensa con casanostra (Ollama) y responde con voz.

Motores de voz (elige según lo que tengas instalado; se detecta solo):
  - Windows: usa las voces del sistema (SAPI5). Elige una voz de ESPAÑA
    (Helena/Laura son de España; Sabina/Pablo suelen ser de México — evítalas).
  - Multiplataforma: Piper TTS si está instalado (voz neuronal, muy natural).

Uso:
    python voz.py                 # conversación por voz
    python voz.py --voces         # lista las voces instaladas y su idioma
    python voz.py --texto         # habla tú por teclado, responde por voz

Requisitos (los instala instalar_voz.ps1):
    pip install vosk sounddevice pyttsx3
    + un modelo de voz español de Vosk (el instalador lo descarga).
"""

import argparse
import json
import queue
import re
import sys
from pathlib import Path
from urllib import request as urlreq

OLLAMA = "http://localhost:11434/api/chat"
MODELO = "casanostra"
CARPETA = Path(__file__).parent
MODELO_VOSK = CARPETA / "modelo_voz_es"  # carpeta del modelo de reconocimiento


def limpiar(texto: str) -> str:
    # quita razonamiento interno y adorna para que la voz suene natural
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S)
    texto = re.sub(r"[*_`#>]", "", texto)          # marcas de markdown
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def pensar(mensajes: list) -> str:
    datos = json.dumps({"model": MODELO, "stream": False, "messages": mensajes}).encode()
    req = urlreq.Request(OLLAMA, data=datos, headers={"Content-Type": "application/json"})
    with urlreq.urlopen(req, timeout=600) as r:
        return limpiar(json.loads(r.read())["message"]["content"])


# ----------------------------------------------------------- SÍNTESIS DE VOZ
def crear_voz():
    """Devuelve una función hablar(texto). Prefiere Piper; si no, pyttsx3 (SAPI5)."""
    # Opción A: Piper (voz neuronal española, muy natural) si está disponible
    piper = CARPETA / "piper"
    modelo_piper = next(CARPETA.glob("es_ES-*.onnx"), None)
    if (piper.exists() or _cmd_existe("piper")) and modelo_piper:
        import shutil
        import subprocess
        exe = str(piper) if piper.exists() else "piper"

        def hablar(texto):
            wav = CARPETA / "_voz_tmp.wav"
            subprocess.run([exe, "--model", str(modelo_piper), "--output_file", str(wav)],
                           input=texto.encode("utf-8"), check=True)
            _reproducir(wav)
        print("Voz: Piper (neuronal, es_ES)")
        return hablar

    # Opción B: pyttsx3 con una voz de ESPAÑA del sistema
    import pyttsx3
    motor = pyttsx3.init()
    voz_es = _elegir_voz_espana(motor)
    if voz_es:
        motor.setProperty("voice", voz_es.id)
        print(f"Voz: {voz_es.name} (sistema)")
    else:
        print("AVISO: no encontré voz de España instalada; usando la voz por "
              "defecto. Instala una voz española (ver instalar_voz.ps1).")
    motor.setProperty("rate", 175)  # velocidad natural

    def hablar(texto):
        motor.say(texto)
        motor.runAndWait()
    return hablar


def _elegir_voz_espana(motor):
    """Busca una voz de España (es-ES), evitando las latinas (es-MX, es-US...)."""
    preferidas = ("helena", "laura", "elvira", "es-es", "spain", "españa", "castilian")
    latinas = ("mexico", "es-mx", "es-us", "sabina", "pablo", "es-419", "latin")
    voces = motor.getProperty("voices")
    # 1) coincidencia clara con España
    for v in voces:
        etiqueta = (v.name + " " + getattr(v, "id", "")).lower()
        idiomas = " ".join(str(x) for x in getattr(v, "languages", [])).lower()
        if any(p in etiqueta or p in idiomas for p in preferidas) and \
           not any(l in etiqueta for l in latinas):
            return v
    # 2) cualquier voz española que NO sea claramente latina
    for v in voces:
        etiqueta = (v.name + " " + getattr(v, "id", "")).lower()
        if ("spanish" in etiqueta or "español" in etiqueta or "es_" in etiqueta) and \
           not any(l in etiqueta for l in latinas):
            return v
    return None


def listar_voces():
    import pyttsx3
    motor = pyttsx3.init()
    print("Voces instaladas en tu sistema:\n")
    for v in motor.getProperty("voices"):
        idiomas = ", ".join(str(x) for x in getattr(v, "languages", [])) or "?"
        print(f"  - {v.name}  [{idiomas}]  id={v.id}")
    print("\nPara castellano de España elige Helena, Laura o Elvira.")
    print("Evita Sabina o Pablo (México). En Windows se añaden en:")
    print("  Configuracion > Hora e idioma > Idioma > Español (España) > Voz.")


def _cmd_existe(cmd):
    import shutil
    return shutil.which(cmd) is not None


def _reproducir(wav: Path):
    import wave
    import sounddevice as sd
    with wave.open(str(wav), "rb") as w:
        import numpy as np
        datos = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        sd.play(datos, w.getframerate())
        sd.wait()


# ----------------------------------------------------- RECONOCIMIENTO DE VOZ
def escuchar_una_frase():
    """Escucha del micrófono hasta una pausa y devuelve el texto (Vosk, es)."""
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd

    if not MODELO_VOSK.exists():
        sys.exit("Falta el modelo de voz español. Ejecuta instalar_voz.ps1 "
                 "o descarga el modelo de Vosk (ver ese script).")
    modelo = Model(str(MODELO_VOSK))
    rec = KaldiRecognizer(modelo, 16000)
    cola = queue.Queue()

    def callback(indata, frames, tiempo, estado):
        cola.put(bytes(indata))

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                           channels=1, callback=callback):
        print("🎤 Escuchando... (habla y haz una pausa)")
        while True:
            datos = cola.get()
            if rec.AcceptWaveform(datos):
                texto = json.loads(rec.Result()).get("text", "").strip()
                if texto:
                    return texto


# ------------------------------------------------------------------- BUCLE
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voces", action="store_true", help="lista las voces y su idioma")
    ap.add_argument("--texto", action="store_true", help="escribe tú, responde por voz")
    args = ap.parse_args()

    if args.voces:
        listar_voces()
        return

    try:
        hablar = crear_voz()
    except ImportError:
        sys.exit("Falta un motor de voz. Ejecuta instalar_voz.ps1 (instala pyttsx3).")

    sistema = ("Eres Casanostra y respondes por voz en español de España. Sé "
               "natural y conversacional, como si hablaras en persona. Respuestas "
               "BREVES (2-4 frases salvo que se pida más), sin listas ni markdown, "
               "sin emojis: se van a leer en voz alta. Sé honesto: si no sabes algo, dilo.")
    mensajes = [{"role": "system", "content": sistema}]

    print("\nCasanostra por voz. Di 'adiós' o pulsa Ctrl+C para salir.\n")
    hablar("Hola, soy Casanostra. ¿En qué puedo ayudarte?")

    try:
        while True:
            if args.texto:
                entrada = input("Tú> ").strip()
            else:
                entrada = escuchar_una_frase()
                print(f"Tú> {entrada}")
            if not entrada:
                continue
            if re.search(r"\b(adiós|adios|hasta luego|apágate|apagate|cierra)\b", entrada.lower()):
                hablar("Hasta luego. Aquí estaré cuando me necesites.")
                break
            mensajes.append({"role": "user", "content": entrada})
            try:
                respuesta = pensar(mensajes)
            except OSError:
                print("No conecto con Ollama. ¿Está corriendo 'ollama serve'?")
                continue
            mensajes.append({"role": "assistant", "content": respuesta})
            print(f"Casanostra> {respuesta}")
            hablar(respuesta)
    except KeyboardInterrupt:
        print("\nHasta luego.")


if __name__ == "__main__":
    main()
