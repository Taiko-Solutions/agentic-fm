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
- **`data_api_orchestrator`** — CRUD sobre la Data API. Opera **por layouts**, que **acotan** los campos disponibles; la validación de esquema es en cliente (zod sobre el resultado), no una comprobación previa de campos. Cuidado con permisos; cruza al lado "hacer".
- **`display_erd_diagram`** — ERD interactivo a partir de TOs.
- **`get_fm_mcp_guide`** — guía oficial (`overview` / `tool-catalog` / `workflows` / `troubleshooting`).

## Límites reales (lo que NO debe hacer)

ProofKit MCP tiene límites en la **introspección de estructura** y, en soluciones grandes, **hace timeout** (**observación de campo Taiko** — caso **Bendita**, solución muy grande; **no** documentado por ProofKit, pero contrastado en la práctica).

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
- **Seguridad del connector.** *(Observación / doc del plugin — la doc pública de ProofKit no describe un "Enhanced Security"; su modelo documentado es la **seguridad heredada de FileMaker**: cuentas, privilegios y reglas de acceso.)* Empíricamente, una conexión nueva puede pedir aprobación temporal (por sesión y archivo); por defecto el connector puede venir sin aprobación explícita, y cualquier proceso local que alcance el puerto hereda acceso. En máquinas compartidas o de cliente, **valora activar la aprobación explícita**.

## Relación con el sistema de contexto

ProofKit MCP **no sustituye** a `CONTEXT.json` ni al explode: los **complementa** con frescura. `CONTEXT.json` sigue siendo la fuente scoped lista-para-pegar; el explode, la estructura completa. MCP entra para confirmar el estado **vivo** de un punto concreto sin re-exportar todo.

## Reparto con el plug-in AgenticFM (si está `usable`)

Desde la incorporación de la capa de plug-in comercial **AgenticFM** (detección en `AGENTS.md` → *Plug-in detection*; routing en [../../PLUGIN_INTEGRATION.md](../../PLUGIN_INTEGRATION.md)) hay **dos** capas de acceso en vivo. No compiten: se reparten por dominio.

- **Plug-in AgenticFM = "lógica viva".** Entender scripts/refs/impacto, resolver IDs/contexto de autoría, HR→XML, validar cálculos, instalar/ejecutar/depurar scripts. Vía preferente **de la parte de autoría** cuando `plugin.usable == true`.
- **ProofKit MCP = "datos + web vivo".** Valores/SQL, metadata de esquema (layout/table/relation/DDL/ERD) y Data API para construir la UI web. El plug-in **no** toca este dominio (`PLUGIN_INTEGRATION.md` no menciona Data API, OData ni web viewer).

**Dos gatings independientes al arrancar**, que no se solapan:

- `connectedFiles` → habilita ProofKit (Vía 1 MCP + Vía 3 Web Viewer).
- companion `/health` → `plugin.usable` → habilita el plug-in AgenticFM.

Una sesión puede tener uno, otro, ambos o ninguno. Regla práctica: *"¿dónde se usa este script / qué se rompe si renombro X?"* → plug-in (o `trace.py`/explode); *"¿qué datos hay / ERD / SQL / construir vista web?"* → ProofKit.

## Prerequisito de instalación (para que "viaje" con la rama)

El repo trae `.mcp.json` con el servidor `proofkit-mcp` (comando `proofkit-mcp`, resuelto por PATH). Cada desarrollador necesita:

1. La app ProofKit instalada (deja el wrapper `proofkit-mcp` en `~/.local/bin`, en PATH).
2. El plugin ProofKit cargado en el archivo FileMaker.
3. Correr *"Connect to MCP"* al abrir el archivo.

Si falta, el servidor simplemente no arranca / `connectedFiles` falla y el flujo estático sigue funcionando.
