# Metodología combinada — agentic-fm + Superpowers + ProofKit (Taiko)

> Cómo las tres herramientas funcionan **como un todo**. Cada una responde una cosa distinta; solapan poco y se coordinan bajo un único proceso.

## El reparto (mapa mental)

| Herramienta | Responde | Rol |
|---|---|---|
| **Superpowers** | *¿CÓMO se ejecuta el trabajo?* | Proceso: brainstorm → plan → casos de aceptación → verificar → review. Umbral en `.claude/CLAUDE.md` → "Metodología de desarrollo — Superpowers". Detalle en [superpowers-workflow.md](superpowers-workflow.md). |
| **agentic-fm** | *¿Cómo AUTORO lógica y esquema?* | Crea scripts, cálculos, custom functions, menús (fmxmlsnippet) y esquema (OData: `schema-build`/`data-migrate`/`data-seed`). Es el músculo de autoría. |
| **ProofKit** | *¿Qué hay AHORA?* y *¿cómo construyo UI web?* | Vía 1 (MCP) = ver en vivo / verificar; Vía 3 (Web Viewer) = interfaces web (motor por defecto). Mapa en [../fm-access.md](../fm-access.md). |

Regla de oro: **agentic-fm autora, ProofKit ve y construye UI, Superpowers ordena el proceso.** ProofKit v2 **no** edita scripts/esquema (eso es agentic-fm); agentic-fm **no** da datos en vivo ni React (eso es ProofKit).

## El bucle unificado (tarea de alcance estructural)

### 1 · Entender
- Estructura base → **explode/sanitized** (`agent/xml_parsed/`, `context/*.index`); skills `solution-analysis`, `extract-erd`, `trace`.
- Frescura/verificación puntual → **ProofKit MCP** (`execute_filemaker_sql`, `layout_metadata`, `display_erd_diagram`) — *si `connectedFiles` responde*.
- Nunca vuelques estructura masiva por MCP (timeout). Reparto en [../fm-access.md](../fm-access.md).

### 2 · Diseñar y planificar (Superpowers)
- Spec + **casos de aceptación** (entrada → salida esperada) al vault.
- **Decisión de UI:** ¿esta funcionalidad se sirve mejor con una **interfaz web ProofKit**? Si encaja (listados, dashboards, interacciones ricas), **propónlo** con sus guardarraíles ([../proofkit/webviewer-build.md](../proofkit/webviewer-build.md)).

### 3 · Implementar
- Lógica / cálculos / esquema / menús → **agentic-fm** (convenciones Taiko, patrones Clew / 3 capas / transaccional).
- Interfaz web → **ProofKit** (motor por defecto; skill `webviewer-build` solo como excepción).
- Ambas partes pueden convivir en una misma funcionalidad: el script Controller (agentic-fm) + la vista (ProofKit) hablando por Data API/bridge.

### 4 · Verificar
- Casos de aceptación → skill `script-test`. Un caso que falla = no está hecho.
- Cálculos → **fmlint** (Tier 3 valida contra el motor FM en vivo vía `AGFMEvaluation`; ojo al `"?"` = fallo).
- Datos/estado en vivo → **ProofKit MCP** (`execute_filemaker_sql`) para confirmar el resultado real.
- Interfaz web → preview local + escalera de diagnóstico ([../proofkit/troubleshooting.md](../proofkit/troubleshooting.md)).

### 5 · Cerrar
- `Changelog-Agentic.md` y `01-Decisiones-Tomadas.md` en el vault. Actualiza guías Obsidian si cambió un patrón.

## Árbol de decisión rápido

| Necesito… | Herramienta |
|-----------|-------------|
| Entender una solución grande | explode/sanitized (+ `solution-analysis`) |
| Confirmar el estado vivo de un layout/campo/valor | ProofKit MCP |
| Crear/modificar un script, CF o cálculo | agentic-fm (fmxmlsnippet) |
| Crear/modificar tablas o campos | agentic-fm (OData `schema-build`) |
| Migrar/sembrar datos | agentic-fm (`data-migrate`/`data-seed`) o ProofKit `data_api_orchestrator` |
| Construir una interfaz de usuario web | **ProofKit** (Vía 3) |
| Ordenar el trabajo de una feature no trivial | Superpowers (proceso) |

## Gating y degradación elegante

ProofKit (Vías 1 y 3) exige `connectedFiles` con archivo conectado. Si no está, **cae al flujo estático** (explode, CONTEXT.json, OData) sin bloquear. agentic-fm nunca depende de ProofKit para funcionar.

## Ver también

- [../fm-access.md](../fm-access.md) — las 3 vías y el reparto de estructura
- [superpowers-workflow.md](superpowers-workflow.md) — el proceso paso a paso
- [../proofkit/webviewer-build.md](../proofkit/webviewer-build.md) — construir interfaces web (motor por defecto)
