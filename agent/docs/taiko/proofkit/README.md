# ProofKit — base de conocimiento Taiko

Esta carpeta recoge cómo Taiko entiende y usa **ProofKit**. Para Taiko, ProofKit son **dos vías** (mapa completo de acceso a FileMaker en [`../fm-access.md`](../fm-access.md)):

- **Vía 1 — ProofKit MCP (connector):** consultar el archivo FileMaker **en vivo** (estructura puntual, SQL, valores) con mucha más facilidad. Es el uso **principal hoy**. → [`mcp-connector.md`](mcp-connector.md)
- **Vía 3 — stack Web Viewer:** app React **dentro de un Web Viewer**, con cliente tipado y deploy de un solo archivo. **Aparcada** (cuesta avanzar). → el resto de esta carpeta.

Ambas comparten el mismo bridge local (`localhost:1365`) pero se usan de forma muy distinta. A diferencia de `../knowledge/` —*gotchas de scripts FileMaker*—, esto es otro dominio (connector + toolchain web), por eso vive aparte, igual que `../custom_functions/` y `../templates/`.

El conocimiento de la Vía 3 no es teórico: nace de un **informe de campo real** (ver *Procedencia*) y está escrito en el formato del repo — "comportamientos que una IA (o un dev) acertaría mal", con síntoma, causa real y fix preventivo.

---

## Alcance: qué cubre esta carpeta

- **Vía 1 — ProofKit MCP:** [`mcp-connector.md`](mcp-connector.md). El uso principal hoy: consultar FileMaker en vivo vía el connector.
- **Vía 3 — Web Viewer:** `architecture.md` + `gotchas.md` + `troubleshooting.md` + `conventions.md`, derivados del field report. Stack `@proofkit/webviewer` + `@proofkit/fmdapi` + `@proofkit/typegen`, bridge + `fmFetch`/callback.

Fuera de esta carpeta:
- **Vía 2 — OData:** `@proofkit/fmodata` o Soliant `fm-odata-client` (cliente OData en Node, HTTP plano, para herramientas web externas). Vivirá en `../../odata/`. **No hay bridge ni callback**, así que la mayoría de los gotchas del Web Viewer (F2, F3, F5, F6, F9) **no aplican**; solo transfieren *drift de esquema* y *timeouts* (que en HTTP se manejan distinto).

> Antes de aplicar un patrón del **Web Viewer**, confirma el stack en `package.json`: si ves `@proofkit/fmodata`/`fm-odata-client` (y no `@proofkit/webviewer`/`typegen` ni `proofkit-typegen.config.jsonc`), estás en OData — los gotchas del Web Viewer no aplican.

---

## Las piezas del Web Viewer (Vía 3), de un vistazo

> Esto describe el stack del **Web Viewer**. Para la Vía 1 (MCP), ve a [`mcp-connector.md`](mcp-connector.md).

ProofKit conecta una app React (dentro de un Web Viewer) con FileMaker a través de un puente local:

```
  App React  ──Layout.find()──►  fmFetch  ──HTTP/WS──►  bridge  ──►  FileMaker
 (Web Viewer)                   (petición)          (localhost:1365)  (corre script)
       ▲                                                                   │
       └────────  "Perform JavaScript in Web Viewer" (el callback)  ◄───────┘
```

| Pieza | Qué es | Analogía FileMaker |
|---|---|---|
| **typegen** | Genera esquema TypeScript + cliente por cada layout `*.List` | "Foto" congelada de la lista de campos de un layout |
| **esquema zod** | Contrato estricto que valida los datos en runtime | Definición de tipo de campo, pero que *protesta* si algo no cuadra |
| **bridge** | Servicio local HTTP+WebSocket (`localhost:1365`) que une Web Viewer y FileMaker | Tu "Data API", pero local y vía plugin/connector |
| **fmFetch + callback** | La ida (fmFetch) y la vuelta (*Perform JavaScript in Web Viewer*) | El viaje completo de una petición de datos |

Detalle completo en [`architecture.md`](architecture.md).

---

## Mapa de la carpeta — qué leer y cuándo

| Doc | Léelo cuando… |
|-----|---------------|
| [`mcp-connector.md`](mcp-connector.md) | **(Vía 1 — lo principal hoy)** Vayas a consultar FileMaker en vivo vía el connector MCP: qué tools, sus **límites** (timeout en soluciones grandes como Bendita), y cuándo usar MCP vs. el explode/sanitized de agentic-fm. |
| [`architecture.md`](architecture.md) | **(Vía 3 — Web Viewer)** Necesites el modelo mental del Web Viewer: las 4 piezas, el flujo `fmFetch`→callback, el glosario, dev vs. producción. |
| [`gotchas.md`](gotchas.md) | Vayas a construir o depurar un Web Viewer ProofKit. Los 11 hallazgos del informe como patrones accionables, agrupados por tema. |
| [`troubleshooting.md`](troubleshooting.md) | Algo "no carga", hay spinner infinito, o fallos intermitentes. Escalera de diagnóstico ordenada. |
| [`conventions.md`](conventions.md) | Arranques un proyecto ProofKit Taiko o revises uno existente. Hábitos preventivos + checklist. |

---

## Cuándo aplica este conocimiento (triggers)

Escanea esta carpeta cuando la tarea mencione: ProofKit, Web Viewer, `fmFetch`, `typegen`, `zod`, cliente tipado, `@proofkit/*`, el bridge / `connectedFiles`, "Perform JavaScript in Web Viewer", "Connect to MCP", deploy de single-file HTML, o cualquier síntoma de spinner infinito / "el bridge no respondió" en una app React sobre FileMaker.

## Relación con lo que agentic-fm ya tiene

- **MCP `proofkit-mcp`** — las herramientas de introspección (`table_metadata`, `layout_metadata`, `get_value_list_info`, `get_relation_info`, `get_filemaker_ddl_schema`, `execute_filemaker_sql`, `connectedFiles`, `deploy_html`) viajan por el **mismo connector/bridge** que las lecturas del Web Viewer. El informe confirma que estas herramientas de introspección **siguieron siendo fiables** incluso los días en que el canal de lecturas fallaba (ver F4) — son el canal de confianza para verificar el esquema real frente al generado.
- **Skill `webviewer-build`** — genera la app HTML/JS dentro del Web Viewer más los scripts FM puente. Aplica las convenciones de esta carpeta al generar o revisar esos proyectos.
- **`get_fm_mcp_guide`** (proofkit-mcp) — guía oficial del MCP (`topic='overview'`, `'filemaker-concepts'`, `'troubleshooting'`). Complementa, no sustituye, lo de aquí.

---

## Procedencia

El conocimiento inicial procede del **ProofKit Field Report** de **Eikonsys — Ibrahim Bittar** (Claris Partner desde 2003), fechado **16 jun 2026**, dirigido al equipo de ProofKit. Documenta la fiabilidad del puente FileMaker ↔ Web Viewer y del toolchain de esquema tipado, observada al construir un módulo React de producción sobre una solución FileMaker de 1.300+ layouts.

Entorno del informe (referencia): connector v2.2.2, `@proofkit/webviewer` 3.1.0, `@proofkit/fmdapi` 5.1.2, `@proofkit/typegen` ^1.1.1, zod ^4, Vite ^7, React 19.2, Node v26.3, FileMaker Server 2025 (WebDirect), bridge en `localhost:1365`.

> Es un informe orientado a *upstream* (sugerencias al equipo de ProofKit). Aquí lo reinterpretamos como **aprendizaje interno Taiko**: qué evitar y cómo, no propuestas a terceros.

## Mantenimiento

Estos documentos los mantiene el equipo Taiko, viven en la rama `taiko` y nunca se mergean a `main` ni se proponen upstream. Cuando aparezcan nuevos aprendizajes (más informes, experiencia propia), añádelos al doc temático correspondiente y, si introducen un gotcha nuevo, registra su entrada en `../knowledge/MANIFEST.md`.
