# SKILL: loop-prompts
**Trigger:** "/loop-prompts", "mejora los agentes", "optimiza los prompts", "ciclo de mejora", "auto-mejora de agentes"

## Qué hace esta skill

Ejecuta un ciclo de auto-mejora sobre todos los prompts de los agentes de CasaNostraAuto.
Lee cada archivo en `.claude/agents/`, evalúa la calidad del prompt, genera una versión mejorada
y registra los cambios. Repite hasta que todos los agentes tengan score >= 45/50.

---

## PROTOCOLO DE EJECUCIÓN

### FASE 0 — Inicialización
```
Lee los 5 archivos de agentes:
- .claude/agents/dexi.md
- .claude/agents/ares.md
- .claude/agents/atlas.md
- .claude/agents/titan.md
- .claude/agents/flora.md

Muestra tabla de estado inicial:
| Agente | Versión actual | Score estimado | Estado |
```

### FASE 1 — Evaluación (por cada agente)

Aplica la RÚBRICA DE CALIDAD (0-10 por dimensión, total /50):

| Dimensión | Pregunta clave |
|-----------|---------------|
| **Claridad de rol** | ¿El agente sabe EXACTAMENTE quién es y qué hace? |
| **Límites honestos** | ¿Dice claramente lo que NO hace / NO puede? |
| **Protocolo de respuesta** | ¿Tiene tono, formato y longitud definidos? |
| **Gestión de bordes** | ¿Qué hace cuando algo sale de su scope o es urgente/peligroso? |
| **Integración con NEXUS** | ¿Reporta a DEXI? ¿Sabe cuándo escalar? |

**Umbral:**
- Score >= 45 → ESTABLE (no necesita mejora en este ciclo)
- Score 35-44 → MEJORA MENOR (ajustes de tono/formato/límites)
- Score < 35 → MEJORA MAYOR (reestructuración del prompt)

### FASE 2 — Mejora automática

Para cada agente con score < 45:

1. **Identifica los 2-3 puntos más débiles** (los que bajaron más puntos)
2. **Genera el prompt mejorado** con estos principios:
   - Añade lo que falta sin eliminar lo que funciona
   - Mantiene la esencia del agente y su módulo
   - Mejora los límites y el protocolo de escalado a DEXI
   - Incluye ejemplos concretos si ayudan a la claridad
3. **Actualiza el archivo** con:
   - Versión incrementada (1.0 → 1.1 → 2.0 para cambios mayores)
   - Score nuevo en el header
   - Entrada en el historial de versiones con los cambios

### FASE 3 — Verificación del ciclo

```
¿Todos los agentes tienen score >= 45?
  SÍ → Loop terminado. Muestra resumen final.
  NO → Vuelve a FASE 1 con los agentes pendientes.

Máximo 3 iteraciones por sesión para no sobreoptimizar.
```

### FASE 4 — Informe final

```
════════════════════════════════════════
  CICLO DE MEJORA COMPLETADO
  CasaNostraAuto — Loop de Prompts
════════════════════════════════════════

RESUMEN:
  Agentes evaluados: 5
  Agentes mejorados: X
  Iteraciones realizadas: X

RESULTADOS POR AGENTE:
  ⚡ DEXI   → Score: XX/50 | Versión: X.X | Estado: [ESTABLE/MEJORADO]
  📈 ARES   → Score: XX/50 | Versión: X.X | Estado: [ESTABLE/MEJORADO]
  🏋️ ATLAS  → Score: XX/50 | Versión: X.X | Estado: [ESTABLE/MEJORADO]
  🐕 TITAN  → Score: XX/50 | Versión: X.X | Estado: [ESTABLE/MEJORADO]
  🌿 FLORA  → Score: XX/50 | Versión: X.X | Estado: [ESTABLE/MEJORADO]

PRINCIPALES MEJORAS APLICADAS:
  [Lista de los cambios más importantes por agente]

PRÓXIMO CICLO RECOMENDADO: [fecha]
════════════════════════════════════════
⚡ Prompts actualizados en .claude/agents/
   Copia el PROMPT ACTIVO de cada archivo a su Claude Project correspondiente.
```

---

## Opciones de uso

```
/loop-prompts              → Ciclo completo (todos los agentes)
/loop-prompts ARES         → Solo el agente ARES
/loop-prompts --forzar     → Mejora aunque score >= 45 (útil para refrescar)
/loop-prompts --ver        → Solo muestra scores sin modificar nada
```

---

## Notas de diseño

- El ciclo es **conservador**: preserva la identidad del agente, solo refuerza lo débil.
- Las mejoras son **trazables**: cada versión queda registrada con fecha y cambio.
- El sistema **converge**: a las 2-3 iteraciones, los prompts se estabilizan.
- Los archivos en `.claude/agents/` son la **fuente de verdad**. Después copias el PROMPT ACTIVO a Claude Projects.
