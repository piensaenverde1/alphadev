# ACTUALIZAR.PS1 — autosuficiencia total: sincroniza TODO el sistema Casanostra
# desde GitHub en un solo comando. Arregla la deriva entre instalador y paquetes.
#
# Uso:  powershell -ExecutionPolicy Bypass -File actualizar.ps1
#
# Qué hace: descarga la última versión completa del repositorio, copia todos
# los archivos del sistema a $HOME\casanostra, recrea TODOS los asistentes en
# Ollama y reindexa la biblioteca. NO toca tus datos personales (memoria.md,
# resultados.md, tus fichas y notas propias no están en el repo y se conservan).
$ErrorActionPreference = "Stop"
$DIR = "$HOME\casanostra"
$RAMA = "claude/fable5-opus-comparison-7l97mz"
$ZIP = "https://codeload.github.com/piensaenverde1/alphadev/zip/refs/heads/$RAMA"
$TMP = Join-Path $env:TEMP "casanostra_update"

Write-Host "=============================================="
Write-Host " ACTUALIZADOR CASANOSTRA (sincroniza todo)"
Write-Host "=============================================="

# 1. Descargar el repo completo como ZIP
Write-Host "[1/4] Descargando la ultima version del sistema..."
if (Test-Path $TMP) { Remove-Item $TMP -Recurse -Force }
New-Item -ItemType Directory -Force -Path $TMP | Out-Null
Invoke-WebRequest $ZIP -OutFile "$TMP\repo.zip"
Expand-Archive "$TMP\repo.zip" -DestinationPath $TMP -Force
$ORIGEN = Get-ChildItem $TMP -Directory | Where-Object { $_.Name -like "alphadev-*" } | Select-Object -First 1
$ORIGEN = Join-Path $ORIGEN.FullName "ollama-casanostra"
if (-not (Test-Path $ORIGEN)) { Write-Host "ERROR: no encuentro ollama-casanostra en el ZIP"; exit 1 }

# 2. Copiar los archivos del sistema (tus datos personales no estan en el repo: intactos)
Write-Host "[2/4] Copiando archivos del sistema a $DIR ..."
New-Item -ItemType Directory -Force -Path $DIR | Out-Null
Copy-Item "$ORIGEN\*" $DIR -Recurse -Force
$n = (Get-ChildItem $ORIGEN -Recurse -File).Count
Write-Host "  $n archivos sincronizados"

# 3. Recrear TODOS los asistentes (base + cada Modelfile de habilidades/)
Write-Host "[3/4] Recreando asistentes en Ollama..."
ollama create casanostra -f "$DIR\Modelfile"
Write-Host "  casanostra OK"
foreach ($mf in Get-ChildItem "$DIR\habilidades\*.Modelfile") {
  $nombre = $mf.BaseName
  ollama create $nombre -f $mf.FullName
  Write-Host "  $nombre OK"
}

# 4. Reindexar la biblioteca con todo el conocimiento
Write-Host "[4/4] Reindexando la biblioteca..."
if (Get-Command python -ErrorAction SilentlyContinue) {
  python "$DIR\biblioteca.py" indexar "$DIR\conocimiento"
} else {
  Write-Host "  (Python no encontrado: reindexa luego con biblioteca.py)"
}
Remove-Item $TMP -Recurse -Force

Write-Host ""
Write-Host "SISTEMA COMPLETO Y AL DIA. Inventario:"
ollama list
Write-Host ""
Write-Host "Dashboard:  python $DIR\motor.py"
