# ProofKit MCP — el connector como "ojos" en vivo (Vía 1)

> Cómo Taiko usa ProofKit **de forma principal hoy**: un plugin/connector en FileMaker que deja al agente **consultar el archivo en vivo** (estructura puntual, SQL, valores). Es la **Vía 1** de [../fm-access.md](../fm-access.md). Comparte el bridge local (`localhost:1365`) con la Vía 3, pero su uso es distinto.

**Antes de operar:** `connectedFiles` debe devolver el/los archivo(s). Si devuelve `[]`, corre el script *"Connect to MCP"* en FileMaker (ver *Ciclo de vida*).

## Para qué brilla (en vivo y quirúrgico)

Herramientas del servidor MCP `proofkit-mcp`, para preguntas **concretas y frescas**:

- **`connectedFiles`** — ¿hay archivo conectado? Diagnóstico del puente. **Llamar siempre primero.**
- **`execute_filemaker_sql`** — SQL de solo lectura ad-hoc contra el archivo en vivo.
- **`layout_metadata`** — campos/portales que **un** layout expone ahora (ideal para verificar drift de ese layout, y schema discovery para apps web).
- **`table_metadata`, `get_relation_info`, `get_value_list_info`, `get_script_names`** — metadatos puntuales.
- **`get_filemaker_ddl_schema`** — DDL, pero **solo de las TOs seleccionadas** (no de toda la solución).
- **`data_api_orchestrator`** — CRUD con validación de campos contra layout (cuidado con permisos; cruza al lado "hacer").
- **`display_erd_diagram`** — ERD interactivo a partir de TOs.
- **`get_fm_mcp_guide`** — guía oficial (`overview` / `tool-catalog` / `workflows` / `troubleshooting`).

## Límites reales (lo que NO debe hacer)

ProofKit MCP tiene límites en la **introspección de estructura** y, en soluciones grandes, **hace timeout**. Caso real: **Bendita** (solución muy grande).

- ❌ **No** lo uses para volcar estructura **completa/amplia** de una solución grande.
- ❌ **No** pidas DDL de muchas TOs a la vez — selecciona las que necesitas.
- ✅ Para estructura amplia o de soluciones grandes → el **explode** de agentic-fm.

## MCP vs explode/sanitized (regla corta)

**Estructura amplia → explode; pregunta puntual y en vivo → MCP.** El explode (`agent/xml_parsed/`, `scripts_sanitized/`, `context/*.index`) es **primario y autoritativo**: completo, en disco, sin timeout. Tabla de reparto completa en [../fm-access.md](../fm-access.md).

## Dos contextos de uso (importante)

El guide oficial distingue dos modos y **no mezclar herramientas**:

- **Exploración de datos (chat):** `table_metadata` → `get_filemaker_ddl_schema` → `display_erd_diagram` → `execute_filemaker_sql`. SQL y DDL son correctos aquí.
- **Construcción de app web (Vía 3):** `layout_metadata` → `data_api_orchestrator`. **No** uses SQL ni DDL aquí — la Data API opera por layouts, así que `layout_metadata` es el descubrimiento de esquema correcto.

## Ciclo de vida y seguridad

- **Reconexión tras reiniciar FileMaker.** `connectedFiles` devuelve `[]` hasta correr de nuevo *"Connect to MCP"*; no hay auto-reconexión. Diagnóstico: `curl -s http://localhost:1365/connectedFiles`.
- **Enhanced Security.** Con seguridad reforzada activada, una conexión nueva pide aprobación temporal (por sesión y archivo, idle hasta 1 h). Por defecto el connector puede venir con *Enhanced Security: off* — cualquier proceso local que alcance el puerto hereda acceso. En máquinas compartidas o de cliente, **valora activar la aprobación explícita**.

## Relación con el sistema de contexto

ProofKit MCP **no sustituye** a `CONTEXT.json` ni al explode: los **complementa** con frescura. `CONTEXT.json` sigue siendo la fuente scoped lista-para-pegar; el explode, la estructura completa. MCP entra para confirmar el estado **vivo** de un punto concreto sin re-exportar todo.

## Prerequisito de instalación (para que "viaje" con la rama)

El repo trae `.mcp.json` con el servidor `proofkit-mcp` (comando `proofkit-mcp`, resuelto por PATH). Cada desarrollador necesita:

1. La app ProofKit instalada (deja el wrapper `proofkit-mcp` en `~/.local/bin`, en PATH).
2. El plugin ProofKit cargado en el archivo FileMaker.
3. Correr *"Connect to MCP"* al abrir el archivo.

Si falta, el servidor simplemente no arranca / `connectedFiles` falla y el flujo estático sigue funcionando.
