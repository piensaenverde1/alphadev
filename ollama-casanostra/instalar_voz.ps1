# INSTALAR_VOZ.PS1 — prepara todo para hablar con casanostra por voz (Windows)
# Uso:  powershell -ExecutionPolicy Bypass -File instalar_voz.ps1
#
# Instala las librerías de Python, descarga el modelo de reconocimiento de voz
# en español, y te explica cómo poner una voz de ESPAÑA (no latina).
$ErrorActionPreference = "Stop"
$DIR = "$HOME\casanostra"

Write-Host "=============================================="
Write-Host " INSTALADOR DE VOZ para Casanostra"
Write-Host "=============================================="

# 1. Comprobar Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Necesitas Python. Instalalo de https://python.org/downloads"
  Write-Host "y marca la casilla 'Add python.exe to PATH'. Luego repite."
  exit 1
}

# 2. Librerías de Python (reconocimiento + micrófono + voz del sistema)
Write-Host "[1/3] Instalando librerias de Python (vosk, sounddevice, pyttsx3)..."
python -m pip install --user --quiet vosk sounddevice pyttsx3
Write-Host "  OK"

# 3. Modelo de reconocimiento de voz en español (Vosk, gratuito, ~40 MB)
$modeloDir = "$DIR\modelo_voz_es"
if (Test-Path $modeloDir) {
  Write-Host "[2/3] Modelo de voz español ya presente. OK"
} else {
  Write-Host "[2/3] Descargando modelo de voz espanol (~40 MB)..."
  $zip = "$env:TEMP\vosk_es.zip"
  $url = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
  Invoke-WebRequest $url -OutFile $zip
  Expand-Archive $zip -DestinationPath "$env:TEMP\vosk_es" -Force
  $extraido = Get-ChildItem "$env:TEMP\vosk_es" -Directory | Select-Object -First 1
  Move-Item $extraido.FullName $modeloDir
  Remove-Item $zip -Force
  Write-Host "  Modelo instalado en $modeloDir"
}

# 4. Voz de España en el sistema
Write-Host "[3/3] Voz de salida (que suene de Espana)..."
Write-Host "  Windows trae voces, pero puede que la de espanol sea latina."
Write-Host "  Para anadir/activar una voz de ESPANA (Helena o Laura):"
Write-Host "    Configuracion > Hora e idioma > Idioma y region"
Write-Host "    > Anadir idioma > 'Espanol (Espana)' > Opciones > descargar Voz."
Write-Host "  Comprueba que voces tienes con:  python `"$DIR\voz.py`" --voces"
Write-Host ""
Write-Host "=============================================="
Write-Host " LISTO. Prueba la voz:"
Write-Host "   python `"$DIR\voz.py`" --voces      (ver voces y elegir una de Espana)"
Write-Host "   python `"$DIR\voz.py`"              (conversacion por voz)"
Write-Host "   python `"$DIR\voz.py`" --texto      (escribes tu, responde por voz)"
Write-Host "=============================================="
Write-Host ""
Write-Host "OPCIONAL - voz neuronal mucho mas natural (Piper):"
Write-Host "  1. Descarga Piper: https://github.com/rhasspy/piper/releases"
Write-Host "  2. Descarga una voz es_ES (p.ej. es_ES-sharvard o es_ES-davefx) y"
Write-Host "     pon el archivo .onnx en $DIR . voz.py la usara automaticamente."
