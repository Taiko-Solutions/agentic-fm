# Construir una interfaz web con ProofKit (Vía 3 — motor por defecto)

> **Decisión Taiko:** ProofKit es el **motor por defecto** para construir interfaces web dentro de FileMaker. El skill nativo `webviewer-build` de agentic-fm (HTML autocontenido + bridge FM) queda como **excepción** para casos triviales o sin conexión ProofKit (ver *Cuándo cada motor*).

## Cuándo PROPONER una interfaz web (proactivo)

Claude **debe proponer** una interfaz web ProofKit, sin esperar a que la pidan, cuando la tarea encaje con:

- Listados/buscadores, dashboards, o vistas de datos ricas que en FileMaker nativo serían costosas o feas.
- Interacciones modernas (drag-and-drop, gráficos, edición inline, filtros dinámicos).
- Un módulo nuevo donde una UI web daría mejor UX o prepararía una futura migración fuera de FileMaker.

Al proponerla, **menciona los guardarraíles** (fragilidad del puente, [gotchas.md](gotchas.md)) para que la decisión sea informada. No la impongas: es una propuesta.

## Flujo de construcción (con `proofkit-mcp`)

Requiere `connectedFiles` con archivo conectado (Vía 1, [mcp-connector.md](mcp-connector.md)).

1. **`connectedFiles`** — verifica conexión.
2. **`layout_metadata { layouts: "" }`** — lista layouts; elige los que la app necesita. Los prefijados `API`/`dapi` suelen estar diseñados para acceso programático. **Descubrimiento de esquema por layouts** (no SQL/DDL aquí).
3. **`setup_proofkit_project { targetPath }`** — devuelve el comando CLI de scaffold. Por defecto `init .` en el directorio actual.
4. **El agente corre el comando** → scaffold React + Vite + Tailwind + shadcn/ui + TanStack Query + TypeGen.
   - **4b. Copia [CLAUDE-webapp.md](CLAUDE-webapp.md) como `CLAUDE.md` a la raíz del proyecto scaffoldeado** y rellena el bloque "Este proyecto". Así las sesiones de trabajo dentro de la app web cargan SOLO las reglas web (ligeras) y no arrastran el stack fmxmlsnippet/steps/Clew del repo padre — que ahí es ruido.
5. **Instala las skills de ProofKit** (comando que devuelve `setup_proofkit_project`) y sigue su guía para typegen y desarrollo.
6. **CRUD siempre con `data_api_orchestrator`** (valida campos contra layout antes de ejecutar).
7. **Regenera typegen** cuando cambie el metadata de un layout ([conventions.md](conventions.md)).
8. **Preview local** e itera: typecheck, lint, build, inspecciona errores/pantallas, corrige.
9. **`pnpm build`** → `dist/index.html` (fichero único autocontenido).
10. **`deploy_html { connectedFileName, appName, path }`** → empuja el HTML al Web Viewer de FileMaker. El fichero debe estar en una ruta de disco accesible al usuario (no un mount solo-agente).

Aplica el **checklist de arranque** de [conventions.md](conventions.md) desde el paso 4.

## Rendimiento y agilidad (aprovéchalo — es lo que hace ágil el conjunto)

- **Batching por defecto.** El `WebViewerAdapter` de `@proofkit/fmdapi` agrupa las lecturas Data API concurrentes (ventana ~16 ms) en una sola script call. **Dispara las lecturas juntas; no las serialices** — serializar mata el batching. Requiere **add-on ≥ 3.0**, `@proofkit/webviewer ≥ 3.2`, `@proofkit/fmdapi ≥ 5.2` (con versiones viejas cae al camino directo, sin batching, y va lento **sin error**).
- **Paginación acotada.** `listAll()` / `findAll()` paginan con `read` acotado (nunca cargan found sets ilimitados en variables FM). **Tunea el tamaño de página** (25/50/100/250/500) según ancho de layout, portales y contenedores; en local suele pesar más que el batch.
- **Detalle en 1 request.** Modela la pantalla de detalle como **una** lectura Data API que trae padre + líneas + relacionados vía relaciones, en vez de N lecturas.
- **Initial props (pull).** Bootstrap fiable (usuario, record ID, ruta) pidiéndolo por `fmFetch` al montar; no lo inyectes por HTML ni desde `OnRecordLoad` (se pierde por carrera). Evita el flash de UI vacía.
- **Caché con TanStack Query** (ya en el stack): dedupe, refresh en background e invalidación tras writes.
- **Canal FM→WebViewer.** Además de `fmFetch` (WV→FM), tienes `initWebViewerCommands` / `callFMScript` (con `FMScriptOption`) para que FileMaker dispare funciones en la app.

## Deploy: elige método según migraciones

`deploy_html` usa por defecto **Embedded** (el código va como *dato* en el archivo FM). Trade-off Taiko relevante: **Embedded no sobrevive a una migración de datos** (importar datos a un archivo nuevo pierde el Web Viewer). Alternativas documentadas: **Store code in a script** (sobrevive migraciones), **Hosted** (servidor web) o **Downloaded** (híbrido self-updating), y un script post-deploy de OttoFMS. Decide según si la solución hace migraciones.

## Ventaja de la Data API en Web Viewer (vs Vía 2 OData)

La Data API vía `Execute Data API` **no requiere autenticación** (corre como el usuario logueado), **funciona offline** y **funciona aunque la Data API esté desactivada en el servidor**. Es un argumento fuerte para ProofKit como motor web por defecto frente a OData/Otto (Vía 2), que sí piden credenciales/servidor.

## Límite de ProofKit v2

ProofKit v2 se centra **exclusivamente** en la codificación de apps Web Viewer. **No** edita scripts, tablas, campos, layouts ni value lists de FileMaker — eso es terreno de **agentic-fm** (autoría vía fmxmlsnippet / OData). Son complementarios: ProofKit construye la UI y lee/escribe datos; agentic-fm construye la lógica y el esquema.

## Cuándo cada motor (ProofKit vs `webviewer-build`)

| Situación | Motor |
|-----------|-------|
| Interfaz de datos, dashboard, buscador, app con estado, producción | **ProofKit** (por defecto) |
| ProofKit conectado disponible | **ProofKit** |
| HTML muy simple/autocontenido, sin datos vía Data API, o sin ProofKit conectado | skill `webviewer-build` (excepción) |
| Necesitas typegen/tipos, TanStack, componentes shadcn | **ProofKit** |

Si dudas: **ProofKit por defecto**, y justifica si eliges la excepción.
