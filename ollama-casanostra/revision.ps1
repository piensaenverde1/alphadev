# REVISION.PS1 — el "medico" de casanostra + copia de seguridad de tu trabajo
# Uso:
#   powershell -ExecutionPolicy Bypass -File revision.ps1            (diagnostico)
#   powershell -ExecutionPolicy Bypass -File revision.ps1 -Copia     (copia de seguridad)
#   powershell -ExecutionPolicy Bypass -File revision.ps1 -Podar     (reduce memoria si es enorme)
param([switch]$Copia, [switch]$Podar)

$DIR = "$HOME\casanostra"
$script:ok = 0
$script:avisos = 0

function Check {
  param([string]$Nombre, [bool]$Condicion, [string]$Arreglo)
  if ($Condicion) {
    Write-Host "  [OK] $Nombre" -ForegroundColor Green
    $script:ok = $script:ok + 1
  } else {
    Write-Host "  [X]  $Nombre" -ForegroundColor Yellow
    Write-Host "       arreglo: $Arreglo" -ForegroundColor DarkGray
    $script:avisos = $script:avisos + 1
  }
}

# ---------------- COPIA DE SEGURIDAD ----------------
if ($Copia) {
  $sello = Get-Date -Format 'yyyy-MM-dd_HH-mm'
  $escritorio = [Environment]::GetFolderPath('Desktop')
  $destino = Join-Path $escritorio "casanostra-copia-$sello"
  New-Item -ItemType Directory -Force -Path $destino | Out-Null
  $tuyo = @('memoria.md', 'resultados.md', 'indice_biblioteca.json')
  foreach ($f in $tuyo) {
    $origen = Join-Path $DIR $f
    if (Test-Path $origen) { Copy-Item $origen $destino -Force }
  }
  foreach ($carpeta in @('cerebro_inversor', 'noticias', 'conocimiento_web', 'habilidades_generadas')) {
    $origen = Join-Path $DIR $carpeta
    if (Test-Path $origen) { Copy-Item $origen $destino -Recurse -Force }
  }
  $n = (Get-ChildItem $destino -Recurse -File).Count
  Write-Host "Copia de seguridad hecha: $n archivos" -ForegroundColor Green
  Write-Host "  $destino"
  Write-Host "Guardala en un USB o en la nube: es tu trabajo, el codigo ya esta en GitHub."
  exit 0
}

# ---------------- PODAR MEMORIA ----------------
if ($Podar) {
  $mem = Join-Path $DIR 'memoria.md'
  if (-not (Test-Path $mem)) { Write-Host "No hay memoria.md todavia."; exit 0 }
  $lineas = (Get-Content $mem).Count
  if ($lineas -le 200) {
    Write-Host "memoria.md tiene $lineas lineas: aun es pequena, no hace falta podar."
    exit 0
  }
  Copy-Item $mem "$mem.bak" -Force
  Get-Content $mem | Select-Object -Last 150 | Set-Content $mem
  Write-Host "Memoria podada de $lineas a 150 lineas (copia en memoria.md.bak)." -ForegroundColor Green
  exit 0
}

# ---------------- DIAGNOSTICO ----------------
Write-Host "=============================================="
Write-Host " REVISION DE SALUD - casanostra"
Write-Host "=============================================="
Write-Host ""

$tieneOllama = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
Check "Ollama instalado" $tieneOllama "Instala Ollama desde https://ollama.com/download"

$servidorOk = $false
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 | Out-Null; $servidorOk = $true } catch { $servidorOk = $false }
Check "Servidor Ollama respondiendo" $servidorOk "Abre la app de Ollama o ejecuta: ollama serve"

$tienePython = [bool](Get-Command python -ErrorAction SilentlyContinue)
Check "Python instalado" $tienePython "Instala Python de python.org marcando 'Add python.exe to PATH'"

$modelos = @()
try { $modelos = (Invoke-RestMethod http://localhost:11434/api/tags).models.name } catch { $modelos = @() }

$tieneCasanostra = [bool]($modelos -match 'casanostra')
Check "Modelo base casanostra existe" $tieneCasanostra "Ejecuta actualizar.ps1 para recrear los asistentes"

$tieneEmbed = [bool]($modelos -match 'nomic-embed')
Check "Modelo de busqueda nomic-embed-text" $tieneEmbed "Ejecuta: ollama pull nomic-embed-text"

$nEspecialistas = ($modelos | Where-Object { $_ -notmatch 'qwen' -and $_ -notmatch 'llama' -and $_ -notmatch 'nomic' }).Count
Check "Al menos 15 especialistas creados (tienes $nEspecialistas)" ($nEspecialistas -ge 15) "Ejecuta actualizar.ps1 para crear los que falten"

$hayIndice = Test-Path (Join-Path $DIR 'indice_biblioteca.json')
Check "Biblioteca indexada" $hayIndice "Ejecuta: python biblioteca.py indexar conocimiento"

$progrOk = (Test-Path (Join-Path $DIR 'examen.py')) -and (Test-Path (Join-Path $DIR 'internauta.py')) -and (Test-Path (Join-Path $DIR 'motor.py'))
Check "Programas del sistema presentes" $progrOk "Ejecuta actualizar.ps1 para sincronizar los archivos"

$libreGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
$etiquetaDisco = "Espacio libre en disco C: " + $libreGB + " GB"
Check $etiquetaDisco ($libreGB -ge 5) "Queda poco espacio; borra archivos grandes o modelos que no uses con: ollama rm nombre"

$memPath = Join-Path $DIR 'memoria.md'
if (Test-Path $memPath) {
  $lineasMem = (Get-Content $memPath).Count
  $etiquetaMem = "Memoria de tamano razonable (" + $lineasMem + " lineas)"
  Check $etiquetaMem ($lineasMem -le 400) "Reduce con: powershell -File revision.ps1 -Podar"
}

$escritorio = [Environment]::GetFolderPath('Desktop')
$copias = @(Get-ChildItem $escritorio -Directory -Filter 'casanostra-copia-*' -ErrorAction SilentlyContinue)
Check "Existe alguna copia de seguridad" ($copias.Count -gt 0) "Haz una con: powershell -File revision.ps1 -Copia"

Write-Host ""
$resumen = "RESULTADO: " + $script:ok + " correctos, " + $script:avisos + " avisos."
Write-Host $resumen -ForegroundColor Cyan
if ($script:avisos -eq 0) {
  Write-Host "Sistema sano. Todo en orden." -ForegroundColor Green
} else {
  Write-Host "Revisa los avisos [X] de arriba; cada uno trae su arreglo." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Dashboard con numeros:  python $DIR\motor.py"
Write-Host "Si algo falla y no sabes que hacer:  ollama run mecanico"
