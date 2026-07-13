# CADENCIA (C4) — tareas programadas de Windows para que tu sistema trabaje sin ti
# Uso:   powershell -ExecutionPolicy Bypass -File cadencia.ps1          (crear tareas)
#        powershell -ExecutionPolicy Bypass -File cadencia.ps1 -Estado  (ver estado)
#        powershell -ExecutionPolicy Bypass -File cadencia.ps1 -Quitar  (eliminarlas)
param([switch]$Estado, [switch]$Quitar)

$DIR = "$HOME\casanostra"
$TAREAS = @(
  @{ Nombre = "Casanostra-ExamenSemanal";
     Descripcion = "Examen de control semanal del modelo (queda en resultados.md)";
     Comando = "python `"$DIR\examen.py`" casanostra";
     Tipo = "Semanal"; Dia = "Sunday"; Hora = "10:00" },
  @{ Nombre = "Casanostra-ReindexarBiblioteca";
     Descripcion = "Reindexa (incremental) conocimiento y cerebro_inversor";
     Comando = "python `"$DIR\biblioteca.py`" indexar `"$DIR\conocimiento`" --nuevo";
     Tipo = "Semanal"; Dia = "Sunday"; Hora = "09:30" },
  @{ Nombre = "Casanostra-EstudioCripto";
     Descripcion = "Informe automatico del mercado cripto cada 12 horas (mejora 3)";
     Comando = "python `"$DIR\estudio_cripto.py`"";
     Tipo = "Cada12h"; Hora = "08:00" }
)

if ($Estado) {
  foreach ($t in $TAREAS) {
    $tarea = Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue
    if ($tarea) {
      $info = Get-ScheduledTaskInfo -TaskName $t.Nombre
      Write-Host "$($t.Nombre): $($tarea.State) | Ultima: $($info.LastRunTime) | Proxima: $($info.NextRunTime)"
    } else { Write-Host "$($t.Nombre): NO CREADA" }
  }
  exit 0
}

if ($Quitar) {
  foreach ($t in $TAREAS) {
    Unregister-ScheduledTask -TaskName $t.Nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Eliminada: $($t.Nombre)"
  }
  exit 0
}

Write-Host "Creando la cadencia (con el PC encendido)..."
foreach ($t in $TAREAS) {
  $arg = "-WindowStyle Hidden -Command `"& { $($t.Comando) }`""
  $accion = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
  if ($t.Tipo -eq "Cada12h") {
    # Repite cada 12 horas indefinidamente, empezando hoy a la hora indicada
    $disparo = New-ScheduledTaskTrigger -Once -At $t.Hora -RepetitionInterval (New-TimeSpan -Hours 12)
    $cuando = "cada 12h"
  } else {
    $disparo = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $t.Dia -At $t.Hora
    $cuando = "$($t.Dia) $($t.Hora)"
  }
  $ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $t.Nombre -Action $accion -Trigger $disparo -Settings $ajustes -Description $t.Descripcion -Force | Out-Null
  Write-Host "  OK  $($t.Nombre)  ($cuando)"
}
Write-Host ""
Write-Host "Cadencia activa. Comprobar:  powershell -File cadencia.ps1 -Estado"
Write-Host "CANDADO (C5): estas tareas solo LEEN y escriben en tu carpeta casanostra;"
Write-Host "revisa resultados.md tras los primeros ciclos, como manda el framework."
