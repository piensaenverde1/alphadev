# SKILL: evaluar-agente
**Trigger:** "/evaluar-agente", "evalúa el prompt de", "puntúa a", "qué tan bueno está el prompt de"

## Qué hace esta skill

Evalúa el prompt de un agente concreto usando la rúbrica de calidad de CasaNostraAuto.
Devuelve el score detallado y las 3 mejoras más importantes a aplicar.
No modifica nada — solo analiza. Para modificar, usa `/loop-prompts`.

---

## PROTOCOLO

### Paso 1 — Leer el archivo del agente
```
Lee: .claude/agents/[nombre].md
Extrae: prompt activo, versión actual, historial
```

### Paso 2 — Aplicar rúbrica (10 puntos por dimensión)

**1. CLARIDAD DE ROL (0-10)**
- 10: El agente sabe quién es, qué hace, en qué módulo opera y a quién reporta.
- 5: Rol claro pero le falta contexto de sistema (módulo, relación con DEXI).
- 0: Rol ambiguo o genérico.

**2. LÍMITES HONESTOS (0-10)**
- 10: Dice explícitamente lo que NO hace, cuándo derivar, y a quién.
- 5: Implica sus límites pero no los dice directamente.
- 0: No hay límites definidos — el agente puede intentar hacer de todo.

**3. PROTOCOLO DE RESPUESTA (0-10)**
- 10: Tono, longitud, formato y estilo definidos con ejemplos concretos.
- 5: Tono definido pero sin formato o sin ejemplos.
- 0: Sin protocolo — el agente improvisa cada respuesta.

**4. GESTIÓN DE BORDES (0-10)**
- 10: Define qué hacer ante situaciones urgentes, peligrosas o fuera de scope.
- 5: Menciona algunos casos borde pero no tiene protocolo claro.
- 0: Ninguna gestión de casos extremos.

**5. INTEGRACIÓN CON NEXUS (0-10)**
- 10: Reporta a DEXI, sabe cuándo escalar, conoce el ecosistema de módulos.
- 5: Menciona el sistema pero sin protocolo de escalado.
- 0: Actúa como agente aislado sin conexión al sistema.

### Paso 3 — Generar informe

```
════════════════════════════════════════
  EVALUACIÓN DE AGENTE: [NOMBRE]
  Módulo: [P1-P5] | Versión: [X.X]
════════════════════════════════════════

SCORE TOTAL: XX/50

  Claridad de rol      → [X]/10  [████████░░]
  Límites honestos     → [X]/10  [███████░░░]
  Protocolo respuesta  → [X]/10  [██████░░░░]
  Gestión de bordes    → [X]/10  [█████░░░░░]
  Integración NEXUS    → [X]/10  [████░░░░░░]

DIAGNÓSTICO: [ESTABLE / MEJORA MENOR / MEJORA MAYOR]

TOP 3 MEJORAS A APLICAR:
  1. [Dimensión más baja]: [qué añadir/cambiar exactamente]
  2. [Segunda más baja]: [qué añadir/cambiar exactamente]
  3. [Tercera]: [qué añadir/cambiar exactamente]

Para aplicar las mejoras: /loop-prompts [NOMBRE]
════════════════════════════════════════
```

---

## Ejemplo de uso

```
/evaluar-agente TITAN
/evaluar-agente ARES
/evaluar-agente todos    → Ejecuta evaluación completa sin modificar (igual que /loop-prompts --ver)
```
