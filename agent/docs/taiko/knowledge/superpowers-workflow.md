# Workflow Superpowers en FileMaker (Taiko)

> Detalle del proceso de desarrollo para tareas de **alcance estructural** (ver el umbral en `.claude/CLAUDE.md` → "Metodología de desarrollo — Superpowers"). Para tareas directas, ignora este documento. El proceso lo aporta Superpowers; las convenciones de código las aporta `CODING_CONVENTIONS.md`.

## Las 5 fases

### 1. Explorar y entender (brainstorming)

- Si trabajas sobre una solución existente, audítala primero con el skill `Solution-Analysis`.
- Aclara con preguntas: qué debe hacer, casos límite, dónde se invoca, qué pasa en error.
- No generes XML todavía.

### 2. Diseñar el spec

- Redacta un spec corto: objetivo, piezas FM implicadas, y los **casos de aceptación** (entrada → salida esperada).
- Guárdalo en el vault: `Proyectos/.../[proyecto]/00-Especificacion.md`.

### 3. Planificar (writing-plans)

- Lista ordenada de las piezas a crear: custom functions, scripts (Controller / Transaccional), triggers. Indica dependencias y orden de pegado (ver `Orden-Pegado`).
- Una pieza = una unidad verificable.

### 4. Implementar y verificar (por cada pieza)

1. Escribe los **casos de aceptación** de la pieza (si no estaban ya en el spec).
2. Genera el XML siguiendo las convenciones Taiko y los patrones aplicables (Clew, 3 capas, transaccional…).
3. Impórtalo en FileMaker y **verifica los casos**. Usa el skill `script-test` para generar el script de verificación con esos inputs/outputs.
4. Un caso que falla = no está hecho. Corrige y reverifica.
5. **Review** (requesting-code-review): el XML contra el spec y contra `CODING_CONVENTIONS.md`. Las desviaciones se corrigen antes de pasar a la siguiente pieza.

### 5. Cerrar

- Registra la tarea en `Changelog-Agentic.md` del proyecto (en el vault).
- Anota decisiones técnicas relevantes en `01-Decisiones-Tomadas.md`.

## Si algo falla (systematic-debugging)

Aplica las 4 fases de `systematic-debugging` (causa raíz antes de tocar nada). **La técnica FM es el skill `Skill-Debug`**: instrumentar el script → companion `/debug` → analizar `output.json`. No parchees por síntoma.

## Mapeo fase → artefacto

| Fase | Artefacto | Dónde |
|------|-----------|-------|
| 2. Spec       | `00-Especificacion.md`     | Vault |
| 2/4. Casos    | dentro del spec            | Vault |
| 3. Plan       | `02-Plan-<tema>.md`        | Vault |
| 5. Registro   | `Changelog-Agentic.md`     | Vault |
| 5. Decisiones | `01-Decisiones-Tomadas.md` | Vault |

## Qué NO se hace en FileMaker

- TDD red-green ni "borrar código escrito antes del test" (no hay tests unitarios de XML).
- Git worktrees (entorno pesado: companion, CONTEXT, bind IP).
- Subagentes paralelos por tarea (cada uno necesitaría todo el contexto del repo).
