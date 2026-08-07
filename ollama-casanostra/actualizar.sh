#!/usr/bin/env bash
# ACTUALIZAR.SH — instala/sincroniza TODO el sistema Casanostra en Ubuntu/Linux.
# Descarga la version completa desde GitHub, detecta tu RAM, crea todos los
# asistentes y reindexa. NO toca tus datos personales (memoria, resultados,
# tus notas) si ya existen.
#
# Uso:   bash actualizar.sh
set -e

DIR="$HOME/casanostra"
RAMA="claude/fable5-opus-comparison-7l97mz"
ZIP="https://codeload.github.com/piensaenverde1/alphadev/zip/refs/heads/$RAMA"
TMP="/tmp/casanostra_update"

echo "=============================================="
echo " ACTUALIZADOR CASANOSTRA (Ubuntu/Linux)"
echo "=============================================="

# 0. Dependencias basicas (curl, unzip, python3, pip) via apt si estan
echo "[1/6] Comprobando dependencias..."
faltan=""
for cmd in curl unzip python3; do command -v "$cmd" >/dev/null 2>&1 || faltan="$faltan $cmd"; done
command -v pip3 >/dev/null 2>&1 || faltan="$faltan python3-pip"
if [ -n "$faltan" ] && command -v apt-get >/dev/null 2>&1; then
  echo "  Instalando:$faltan (te pedira la contrasena)"
  sudo apt-get update -y && sudo apt-get install -y $faltan
fi

# 1. Ollama
echo "[2/6] Ollama..."
if command -v ollama >/dev/null 2>&1; then
  echo "  Ya instalado."
else
  echo "  Instalando Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi
# Arrancar el servidor si no esta corriendo
pgrep -f "ollama" >/dev/null 2>&1 || (nohup ollama serve >/dev/null 2>&1 & sleep 3)

# 2. Detectar RAM y elegir modelo base
echo "[3/6] Detectando hardware..."
RAM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1048576 ))
if   (( RAM_GB >= 32 )); then BASE="qwen3:30b-a3b"
elif (( RAM_GB >= 16 )); then BASE="qwen3:8b"
elif (( RAM_GB >= 8  )); then BASE="qwen3:4b"
else BASE="qwen3:1.7b"; fi
echo "  RAM: ${RAM_GB} GB -> modelo base: ${BASE}"

# 3. Descargar el repositorio completo
echo "[4/6] Descargando la ultima version del sistema..."
rm -rf "$TMP"; mkdir -p "$TMP"
curl -fsSL "$ZIP" -o "$TMP/repo.zip"
unzip -q "$TMP/repo.zip" -d "$TMP"
ORIGEN=$(find "$TMP" -maxdepth 2 -type d -name "ollama-casanostra" | head -1)
if [ -z "$ORIGEN" ]; then echo "ERROR: no encuentro ollama-casanostra en el ZIP"; exit 1; fi

# 4. Copiar archivos del sistema (respeta tus datos personales existentes)
echo "[5/6] Copiando a $DIR ..."
mkdir -p "$DIR"
cp -r "$ORIGEN/." "$DIR/"
# Ajustar la linea FROM del Modelfile al modelo elegido segun la RAM
sed -i "s|^FROM .*|FROM ${BASE}|" "$DIR/Modelfile"

# 5. Descargar modelos y crear todos los asistentes
echo "[6/6] Descargando ${BASE} + embeddings y creando asistentes..."
ollama pull "${BASE}"
ollama pull nomic-embed-text
ollama create casanostra -f "$DIR/Modelfile"
echo "  casanostra OK"
for mf in "$DIR"/habilidades/*.Modelfile; do
  nombre=$(basename "$mf" .Modelfile)
  ollama create "$nombre" -f "$mf" && echo "  $nombre OK"
done

# Indexar todo el conocimiento (incremental si ya existia)
if command -v python3 >/dev/null 2>&1; then
  carpetas="$DIR/conocimiento"
  [ -d "$DIR/cerebro_inversor" ] && carpetas="$carpetas $DIR/cerebro_inversor"
  [ -d "$DIR/conocimiento_web" ] && carpetas="$carpetas $DIR/conocimiento_web"
  (cd "$DIR" && python3 biblioteca.py indexar $carpetas --nuevo) || \
    echo "  (indexa luego con: python3 $DIR/biblioteca.py indexar $DIR/conocimiento)"
fi
rm -rf "$TMP"

echo ""
echo "=============================================="
echo " SISTEMA COMPLETO Y AL DIA (Ubuntu)"
echo "=============================================="
ollama list
echo ""
echo "En Linux usa 'python3' (no 'python'). Empieza por la guia:"
echo "   cat $DIR/GUIA.md | less"
echo "Comandos rapidos:"
echo "   ollama run casanostra                         (asistente general)"
echo "   python3 $DIR/motor.py                          (dashboard)"
echo "   python3 $DIR/chat_memoria.py                   (chat con memoria)"
echo "   python3 $DIR/biblioteca.py \"tu pregunta\"       (preguntar a tus documentos)"
