# HABLA — habla a PowerShell en castellano natural (via casanostra)
# Instalar (una vez):  powershell -ExecutionPolicy Bypass -File habla.ps1 -Instalar
# Despues, en CUALQUIER PowerShell nuevo podras escribir:
#   crea una carpeta en el escritorio que se llame facturas
#   dime cuanto espacio libre queda en el disco
#   guarda una nota con la fecha de hoy que diga revisar el examen
# CANDADO: la IA solo PROPONE los comandos; tu confirmas con s/n antes de ejecutar.
param([switch]$Instalar)

$script:TRADUCTOR = "$HOME\casanostra\traductor.py"

# Ordenes que jamas se ejecutan aunque el traductor las proponga (candado duro)
$script:PROHIBIDO = @(
  'Remove-Item.*-Recurse.*(C:\\(Windows|Program|Users)?\s|\$env:SystemRoot|\$HOME\s*$)',
  'format-volume', 'diskpart', 'Clear-Disk', 'Remove-Partition',
  'Stop-Computer', 'Restart-Computer',
  'Set-MpPreference', 'Disable-', 'reg\s+delete', 'rd\s+/s\s+[A-Za-z]:\\\s*$',
  'Invoke-Expression.*Invoke-WebRequest', 'iex.*iwr', 'curl.*\|\s*iex'
)

function Invoke-Casanostra {
  param([string]$Frase)
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Necesitas Python instalado (python.org, marca 'Add to PATH')."; return
  }
  Write-Host "[casanostra esta pensando...]" -ForegroundColor DarkGray
  $salida = (python $script:TRADUCTOR $Frase) -join "`n"
  if (-not $salida) { Write-Host "No he obtenido respuesta del traductor."; return }

  if ($salida -match '^NO:\s*(.*)') {
    Write-Host ("No lo hago: " + $Matches[1]) -ForegroundColor Yellow; return
  }
  if ($salida -match '^ECHO:\s*(.*)') {
    Write-Host $Matches[1] -ForegroundColor Cyan; return
  }

  $comandos = $salida -split "`n" | Where-Object { $_.Trim() }
  Write-Host ""
  Write-Host "Esto es lo que propongo ejecutar:" -ForegroundColor Green
  $i = 1
  foreach ($c in $comandos) { Write-Host ("  {0}. {1}" -f $i, $c.Trim()); $i++ }

  foreach ($patron in $script:PROHIBIDO) {
    foreach ($c in $comandos) {
      if ($c -match $patron) {
        Write-Host "BLOQUEADO por el candado de seguridad (patron: $patron)." -ForegroundColor Red
        Write-Host "Si de verdad quieres eso, hazlo a mano y con cuidado."; return
      }
    }
  }

  $ok = Read-Host "Ejecutar? (s/n)"
  if ($ok -ne 's') { Write-Host "Cancelado. No se ha tocado nada."; return }
  foreach ($c in $comandos) {
    try { Invoke-Expression $c.Trim() }
    catch { Write-Host ("Error en: " + $c.Trim() + " -> " + $_.Exception.Message) -ForegroundColor Red }
  }
  Write-Host "Hecho." -ForegroundColor Green
}

# El comando comodin: pide "lo que sea entre comillas"
function global:pide { Invoke-Casanostra ($args -join ' ') }

# Verbos naturales: cada uno reenvia la frase completa a casanostra
$verbos = "crea","crear","empieza","construye","haz","hazme","dime","dame","busca",
          "muestra","abre","guarda","apunta","ordena","limpia","explica","arregla",
          "prepara","montame","monta","genera","escribe","revisa","lista","pon"
foreach ($v in $verbos) {
  Set-Item -Path "function:global:$v" -Value (
    [scriptblock]::Create("Invoke-Casanostra ('$v ' + (`$args -join ' '))")
  )
}

if ($Instalar) {
  # Cargar HABLA automaticamente en cada PowerShell nuevo (perfil de usuario)
  if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Force -Path $PROFILE | Out-Null }
  $linea = ". `"$HOME\casanostra\habla.ps1`""
  if (-not (Select-String -Path $PROFILE -Pattern "habla.ps1" -Quiet -ErrorAction SilentlyContinue)) {
    Add-Content -Path $PROFILE -Value $linea
    Write-Host "HABLA instalado en tu perfil de PowerShell." -ForegroundColor Green
  } else { Write-Host "HABLA ya estaba en tu perfil." }
  try { Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force } catch {}
  Write-Host ""
  Write-Host "Cierra esta ventana, abre PowerShell NUEVO y prueba:"
  Write-Host '  crea una carpeta en el escritorio que se llame estudio-cripto'
  Write-Host '  dime cuanto espacio libre queda en el disco'
  Write-Host '  pide "guarda una nota en el escritorio con la fecha de hoy"'
}
