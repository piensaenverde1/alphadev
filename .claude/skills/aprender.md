# SKILL: aprender
**Trigger:** "aprende", "evalúa tus señales", "cómo has acertado", "win rate", "tus lecciones", "qué has aprendido"

## Qué hace esta skill

Activa el motor de auto-aprendizaje: evalúa señales pasadas y extrae lecciones.

## Protocolo

### 1. EVALUACIÓN DE SEÑALES PENDIENTES
- Buscar señales generadas hace 7+ días con estado "pending"
- Para cada señal: obtener precio actual y comparar con precio de entrada sugerido
- Calcular si fue correcta (precio fue en la dirección predicha)
- Marcar como "correct" o "wrong" en la base de datos

### 2. ESTADÍSTICAS DE RENDIMIENTO
```
Por agente:
  - Total señales evaluadas
  - Señales correctas
  - Win rate (%)
  - P&L promedio de señales correctas
  - P&L promedio de señales incorrectas

Sistema global:
  - Win rate total
  - Mejor agente del sistema
  - Peor agente del sistema
  - Tendencia: ¿está mejorando?
```

### 3. EXTRACCIÓN DE LECCIONES
Identificar patrones en errores:
- ¿Qué condiciones de mercado causaron más errores?
- ¿Qué indicadores dieron más falsas señales?
- ¿Hay algún activo donde el sistema falla sistemáticamente?
- ¿Las señales de alta confianza fueron más acertadas?

### OUTPUT ESPERADO

```
CICLO DE APRENDIZAJE — [FECHA]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEÑALES EVALUADAS HOY: [N]
  ✓ Correctas: [N] ([X]%)
  ✗ Incorrectas: [N] ([X]%)

RENDIMIENTO POR AGENTE:
  [Agente]: [X]% win rate ([N] señales)
  ...

MEJOR AGENTE: [nombre] ([X]% acierto)
PEOR AGENTE: [nombre] ([X]% acierto)

LECCIONES NUEVAS EXTRAÍDAS: [N]
  "[Lección 1]"
  "[Lección 2]"

TENDENCIA DEL SISTEMA: [Mejorando/Estable/Degradándose]
```

## Comando CLI equivalente
```bash
python main.py --learn
python main.py --status
```
