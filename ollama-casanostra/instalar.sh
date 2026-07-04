#!/usr/bin/env bash
# Instalador del asistente local "casanostra" para Ollama
# Uso: bash instalar.sh
set -e

echo "=== Casanostra: asistente local gratuito para Ollama ==="

# 1. Comprobar que Ollama está instalado
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama no está instalado."
  echo "Instálalo desde https://ollama.com/download y vuelve a ejecutar este script."
  exit 1
fi

# 2. Detectar RAM y elegir el modelo base adecuado
if [[ "$(uname)" == "Darwin" ]]; then
  RAM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
else
  RAM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 ))
fi
echo "RAM detectada: ${RAM_GB} GB"

if   (( RAM_GB >= 32 )); then BASE="qwen3:30b-a3b"   # MoE: calidad alta, activa pocos parámetros
elif (( RAM_GB >= 16 )); then BASE="qwen3:8b"
elif (( RAM_GB >= 8  )); then BASE="qwen3:4b"
else BASE="qwen3:1.7b"
fi
echo "Modelo base elegido: ${BASE}"
echo "(Puedes cambiarlo editando la línea FROM del Modelfile — mira ollama.com/library)"

# 3. Descargar el modelo base (gratuito, licencia Apache 2.0)
ollama pull "${BASE}"

# 4. Ajustar el Modelfile al modelo elegido y crear el asistente
sed "s|^FROM .*|FROM ${BASE}|" Modelfile > Modelfile.local
ollama create casanostra -f Modelfile.local
rm Modelfile.local

echo ""
echo "Listo. Ejecuta tu asistente con:"
echo "    ollama run casanostra"
echo ""
echo "O con memoria persistente entre sesiones:"
echo "    python3 chat_memoria.py"
