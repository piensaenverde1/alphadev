#!/usr/bin/env bash
# Interfaz gráfica gratuita (Open WebUI) para tus modelos locales de Ollama.
# Te da un chat tipo web con historial, subida de documentos y selector de
# modelos (casanostra, maestro, forjador, alquimista...).
# Uso: bash interfaz.sh
set -e

if command -v docker >/dev/null 2>&1; then
  echo "Instalando Open WebUI con Docker..."
  docker rm -f open-webui >/dev/null 2>&1 || true
  docker run -d -p 3000:8080 \
    --add-host=host.docker.internal:host-gateway \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -v open-webui:/app/backend/data \
    --name open-webui --restart always \
    ghcr.io/open-webui/open-webui:main
  echo ""
  echo "✅ Listo. Abre en tu navegador:  http://localhost:3000"
  echo "   (la primera cuenta que crees será la de administrador; es local, no sale de tu PC)"
else
  echo "Docker no encontrado; instalando con pip (necesita Python 3.11 o superior)..."
  python3 -m pip install --user open-webui || pip3 install --user open-webui
  echo ""
  echo "✅ Instalado. Arranca la interfaz con:"
  echo "     open-webui serve"
  echo "   y abre en tu navegador:  http://localhost:8080"
fi
