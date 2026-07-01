# Acceso a FileMaker desde agentic-fm — las 3 vías (Taiko)

> Fuente **canónica** del agente para decidir *cómo* toca FileMaker en un proyecto Taiko.
> La nota humana equivalente vive en Obsidian (`Proyectos/Taiko/Agentic-FM-Taiko/Guias-FM/Acceso-FileMaker-3-Vias.md`) y **referencia** este fichero; no lo duplica.

agentic-fm accede a FileMaker por **tres vías independientes**. No son variantes de lo mismo: cada una responde una pregunta distinta y tiene límites distintos. Mantenerlas separadas es lo que evita malaplicarlas.

| Vía | Pregunta que responde | Herramienta | Estado |
|-----|----------------------|-------------|--------|
| **1 · ProofKit MCP** | "¿Qué hay AHORA en el archivo?" (ver, en vivo) | servidor MCP `proofkit-mcp` (bridge `localhost:1365`) | **Primaria** para frescura/verificación puntual → [proofkit/mcp-connector.md](proofkit/mcp-connector.md) |
| **2 · OData** | "Haz / cambia / automatiza esto" | FMS OData + `AGFMScriptBridge`; skills `schema-build`, `data-migrate`, `data-seed` | En uso |
| **3 · ProofKit Web Viewer** | "Construye una UI web dentro de FileMaker" | `@proofkit/webviewer` + `fmdapi` + `typegen` | **Activa — motor web por defecto** (con guardarraíles) → [proofkit/webviewer-build.md](proofkit/webviewer-build.md) |

> ⚠️ La "Web Viewer ProofKit" (Vía 3) **no** es el webviewer/editor Monaco de agentic-fm. Para ese, ver `agent/docs/` del webviewer embebido.

---

## Gating: comprobar `connectedFiles` antes de usar Vías 1 y 3

ProofKit (MCP y Web Viewer) requiere el plugin instalado en el archivo **y** el script *"Connect to MCP"* corrido en esa sesión de FileMaker.

- **Antes de cualquier operación ProofKit**, llama a `connectedFiles`.
- Devuelve nombres de archivo → adelante.
- Devuelve `[]` → el puente está pero no hay archivo conectado: pide al usuario correr *"Connect to MCP"* en FileMaker.
- Falla/lanza → el plugin no está cargado: cae a la vía estática (explode/CONTEXT.json) y avisa.

**Nunca bloquees el trabajo por ausencia de ProofKit.** Si no está conectado, el flujo OSS de agentic-fm (explode, CONTEXT.json, OData) sigue siendo suficiente.

---

## La consulta de ESTRUCTURA: el reparto que importa

Hay **dos** fuentes de estructura (campos, scripts, relaciones, lógica) y **no compiten — se reparten por tamaño y frescura**:

- **El "explode" de agentic-fm** — `agent/xml_parsed/` + `scripts_sanitized/` y los `agent/context/{solución}/*.index`. Pre-extraído en disco, **completo, grep-able y sin timeout**. Fuente **PRIMARIA y autoritativa** de estructura, sobre todo en soluciones grandes.
- **ProofKit MCP** — fuente **viva** del archivo conectado, pero **quirúrgica**: brilla en consultas puntuales y **hace timeout en introspección de estructura masiva** (caso real: **Bendita**, solución muy grande).

> **Regla Taiko:** estructura amplia → **manda el explode/sanitized**. ProofKit MCP es el complemento en vivo para preguntas concretas y frescas — nunca el volcado masivo.

| Necesito… | Usa… | Por qué |
|-----------|------|---------|
| Estructura completa/amplia de una solución grande | **explode** (`*.index` + `scripts_sanitized/`) | Completo, en disco, sin timeout |
| IDs/nombres/relaciones de la tarea actual | `CONTEXT.json` (si está fresco) | Scoped, listo para fmxmlsnippet |
| Lógica de un script | `scripts_sanitized/` | Legible, sin ruido XML |
| Valor en vivo / "¿existe aún X?" / SQL ad-hoc | **ProofKit MCP** (`execute_filemaker_sql`) | Fuente viva |
| Drift de **un** layout concreto | **ProofKit MCP** (`layout_metadata`) | Targeted |
| ERD de unas TOs concretas | **ProofKit MCP** (`display_erd_diagram`) | Visual, scoped |
| Volcar la estructura entera **vía MCP** en solución grande | ❌ evítalo | Hace **timeout** → usa el explode |

Esto encaja **encima** del *Lookup decision tree* de agentic-fm (`CONTEXT.json` → `index` → `xml_parsed`) como capa **viva** de frescura/verificación.

---

## Cómo se combinan (visión de una línea)

**Vía 1 = ver (en vivo) · Vía 2 = hacer (automatizar) · Vía 3 = UI web (por defecto para interfaces)**, y agentic-fm las coordina bajo el proceso Superpowers. El detalle del flujo unificado está en [knowledge/combined-workflow.md](knowledge/combined-workflow.md).

## Diseñar para reemplazar

Todo esto es un **puente hasta que Claris publique su plugin avanzado definitivo**. Mantén el acceso OData tras un **wrapper Taiko fino**, para que cambiar `@proofkit/fmodata` → `fm-odata-client` → (futuro) Claris sea tocar **un archivo**, no cada herramienta.

## Ficheros relacionados (repo)

- [proofkit/mcp-connector.md](proofkit/mcp-connector.md) — Vía 1, herramientas de consulta en vivo
- [proofkit/webviewer-build.md](proofkit/webviewer-build.md) — Vía 3, flujo de construcción (motor por defecto)
- [proofkit/architecture.md](proofkit/architecture.md) · [proofkit/gotchas.md](proofkit/gotchas.md) · [proofkit/troubleshooting.md](proofkit/troubleshooting.md) · [proofkit/conventions.md](proofkit/conventions.md)
- [knowledge/combined-workflow.md](knowledge/combined-workflow.md) — metodología agentic-fm + Superpowers + ProofKit
