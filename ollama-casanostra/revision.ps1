# REVISION.PS1 — el "médico" de casanostra + copia de seguridad de tu trabajo
# Uso:
#   powershell -ExecutionPolicy Bypass -File revision.ps1            (diagnostico)
#   powershell -ExecutionPolicy Bypass -File revision.ps1 -Copia     (copia de seguridad)
#   powershell -ExecutionPolicy Bypass -File revision.ps1 -Podar     (reduce memoria si es enorme)
param([switch]$Copia, [switch]$Podar)

$DIR = "$HOME\casanostra"
$ok = 0; $avisos = 0

function Check($nombre, $condicion, $arreglo) {
  if ($condicion) { Write-Host "  [OK] $nombre" -ForegroundColor Green; $script:ok++ }
  else { Write-Host "  [X]  $nombre" -ForegroundColor Yellow; Write-Host "       -> $arreglo" -ForegroundColor DarkGray; $script:avisos++ }
}

# ---------------- COPIA DE SEGURIDAD ----------------
if ($Copia) {
  $sello = Get-Date -Format 'yyyy-MM-dd_HH-mm'
  $destino = "$([Environment]::GetFolderPath('Desktop'))\casanostra-copia-$sello"
  New-Item -ItemType Directory -Force -Path $destino | Out-Null
  # Solo tus DATOS personales (lo generado por ti; el codigo se recupera del repo)
  $tuyo = @("memoria.md","resultados.md","indice_biblioteca.json")
  foreach ($f in $tuyo) { if (Test-Path "$DIR\$f") { Copy-Item "$DIR\$f" $destino -Force } }
  foreach ($carpeta in @("cerebro_inversor","noticias","conocimiento_web","habilidades_generadas")) {
    if (Test-Path "$DIR\$carpeta") { Copy-Item "$DIR\$carpeta" $destino -Recurse -Force }
  }
  $n = (Get-ChildItem $destino -Recurse -File).Count
  Write-Host "Copia de seguridad hecha: $n archivos en" -ForegroundColor Green
  Write-Host "  $destino"
  Write-Host "Guardala en un USB o en la nube: es tu trabajo, el codigo ya esta en GitHub."
  exit 0
}

# ---------------- PODAR MEMORIA ----------------
if ($Podar) {
  $mem = "$DIR\memoria.md"
  if (-not (Test-Path $mem)) { Write-Host "No hay memoria.md todavia."; exit 0 }
  $lineas = (Get-Content $mem).Count
  if ($lineas -le 200) { Write-Host "memoria.md tiene $lineas lineas: aun es pequena, no hace falta podar."; exit 0 }
  Copy-Item $mem "$mem.bak" -Force
  Get-Content $mem | Select-Object -Last 150 | Set-Content $mem
  Write-Host "Memoria podada de $lineas a 150 lineas (copia en memoria.md.bak)." -ForegroundColor Green
  exit 0
}

# ---------------- DIAGNOSTICO ----------------
Write-Host "=============================================="
Write-Host " REVISION DE SALUD — casanostra"
Write-Host "=============================================="
Write-Host ""

Check "Ollama instalado" (Get-Command ollama -ErrorAction SilentlyContinue) `
  "Instala Ollama desde https://ollama.com/download"
Check "Servidor Ollama respondiendo" `
  ([bool](try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 } catch { $null })) `
  "Arranca Ollama (abre la app) o ejecuta: ollama serve"
Check "Python instalado" (Get-Command python -ErrorAction SilentlyContinue) `
  "Instala Python de python.org marcando 'Add python.exe to PATH'"

$modelos = @()
try { $modelos = (Invoke-RestMethod http://localhost:11434/api/tags).models.name } catch {}
Check "Modelo base casanostra existe" ($modelos -match "casanostra") `
  "Ejecuta actualizar.ps1 para recrear todos los asistentes"
Check "Modelo de busqueda nomic-embed-text" ($modelos -match "nomic-embed") `
  "Ejecuta: ollama pull nomic-embed-text"
$nEspecialistas = ($modelos | Where-Object { $_ -notmatch "qwen|llama|nomic" }).Count
Check "Al menos 15 especialistas creados (tienes $nEspecialistas)" ($nEspecialistas -ge 15) `
  "Ejecuta actualizar.ps1 para crear los que falten"

Check "Biblioteca indexada" (Test-Path "$DIR\indice_biblioteca.json") `
  "Ejecuta: python `"$DIR\biblioteca.py`" indexar `"$DIR\conocimiento`""
Check "Programas del sistema presentes" `
  ((Test-Path "$DIR\examen.py") -and (Test-Path "$DIR\internauta.py") -and (Test-Path "$DIR\motor.py")) `
  "Ejecuta actualizar.ps1 para sincronizar todos los archivos"

# Espacio en disco
$libreGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Check "Espacio libre en disco C: ($libreGB GB)" ($libreGB -ge 5) `
  "Queda poco espacio; borra archivos grandes o modelos que no uses (ollama rm <modelo>)"

# Memoria no descontrolada
if (Test-Path "$DIR\memoria.md") {
  $lineasMem = (Get-Content "$DIR\memoria.md").Count
  Check "Memoria de tamano razonable ($lineasMem lineas)" ($lineasMem -le 400) `
    "Reduce con: powershell -File revision.ps1 -Podar"
}

# Copia de seguridad reciente en el escritorio
$copias = Get-ChildItem "$([Environment]::GetFolderPath('Desktop'))" -Directory -Filter "casanostra-copia-*" -ErrorAction SilentlyContinue
Check "Existe alguna copia de seguridad" ($copias.Count -gt 0) `
  "Haz una con: powershell -File revision.ps1 -Copia"

Write-Host ""
Write-Host "RESULTADO: $ok correctos, $avisos avisos." -ForegroundColor Cyan
if ($avisos -eq 0) { Write-Host "Sistema sano. Todo en orden." -ForegroundColor Green }
else { Write-Host "Revisa los avisos [X] de arriba; cada uno trae su arreglo." -ForegroundColor Yellow }
Write-Host ""
Write-Host "Dashboard con numeros:  python `"$DIR\motor.py`""
Write-Host "Si algo falla y no sabes que hacer:  ollama run mecanico"
