# CLAUDE.md — App web ProofKit (plantilla Taiko)

> **Plantilla.** Al scaffoldear un proyecto web ProofKit (`setup_proofkit_project`), copia este fichero como `CLAUDE.md` a la **raíz del proyecto scaffoldeado** (paso 4b de `webviewer-build.md`). Ajusta el bloque "Este proyecto" y borra esta nota.

## Este proyecto

- **Solución FileMaker**: `<<NombreArchivo.fmp12>>`
- **App/Web Viewer destino**: `<<appName>>` en layout `<<layout>>`
- **Repo agentic-fm asociado**: `<<ruta al clone del repo del proyecto>>`

Este directorio es una **app web React/TypeScript que corre dentro de un Web Viewer de FileMaker** (stack ProofKit: Vite + Tailwind + shadcn/ui + TanStack Query + TypeGen). El trabajo aquí es desarrollo web, no autoría FileMaker.

## Qué NO aplica en este subárbol

Las reglas FileMaker del repo agentic-fm padre **no gobiernan este proyecto**: nada de fmxmlsnippet, step catalog, HR scripts, Clew, CONTEXT.json ni convenciones de cálculo FM. No cargues ni consultes esos docs para trabajar aquí — son ruido para el desarrollo web.

**Escalada a agentic-fm**: si la tarea exige crear o modificar un **script de FileMaker** (backend de `fmFetch`), **esquema** (tablas/campos/layouts) o lógica FM, eso NO se hace desde aquí: es tarea agentic-fm en el repo del proyecto (fmxmlsnippet/OData, con sus convenciones). Señálalo, y hazlo allí — luego vuelve.

## Arranque de sesión (mínimo)

1. `connectedFiles` (MCP `proofkit-mcp`; desde ProofKit 3.2.0 el servidor es `proofkit mcp`) debe listar el archivo. Si `[]`: pide correr **"Connect To ProofKit MCP"** en FileMaker.
2. **La ventana del connector debe seguir abierta y en modo Navegar** durante todo el desarrollo (F12). Y **ninguna otra ventana con un Web Viewer llamado `web`** (connector, "ProofKit App") delante de la pantalla que pruebas (F13/F14).
3. `pnpm dev` → en el navegador, el plugin `fmBridge` de Vite habla con el FileMaker real. **Dentro de un Web Viewer de FM** usa `http://localhost:5175/?wv=web` con `fmBridge` condicionado a que la URL no lleve `wv` (F16): si no, inyecta un `window.FileMaker` falso y todo va por el connector.

## Reglas de oro (rendimiento y fiabilidad)

- **Versiones mínimas** (si va lento sin error, revisa esto PRIMERO): ProofKit add-on **≥ 3.0** en el archivo, `@proofkit/webviewer` **≥ 3.2**, `@proofkit/fmdapi` **≥ 5.2**. Con add-on viejo, el batching cae en silencio al camino directo.
- **Deja que el `WebViewerAdapter` agrupe las lecturas** (batching por defecto, ~16 ms): dispáralas juntas; **no** las serialices a mano.
- **Paginación acotada**: `listAll()`/`findAll()`; tunea el **page size** (25/50/100/250/500) según ancho de layout/portales/contenedores.
- **Detalle en 1 request**: una lectura con relaciones (padre + hijos) en vez de N.
- **Typegen**: config en **`proofkit-typegen-config.jsonc`** (guion, no punto); **regenera tras tocar campos/layouts** (`npx @proofkit/typegen`) — causa nº1 de "no carga"; convención Taiko: `clearOldFiles: false` + commit de `generated/`.
- **El objeto Web Viewer se llama `web`** (estándar ProofKit; `PK_execute_data_api` lo tiene fijo). Si usas otro nombre, la app lo fija con `globalSettings.setWebViewerName("…")` (`@proofkit/webviewer` ≥ 3.3) **y** los scripts puente respetan `callback.webViewerName` (F5/F13).
- **Espera a `window.FileMaker`** antes de renderizar (sondeo ~50 ms, máx. 5 s): FM lo inyecta después de empezar a cargar (F17).
- **TanStack Query sin `refetchOnWindowFocus` ni `refetchOnReconnect`**: una recarga con otra ventana delante pierde la respuesta (F14). Refresca desde FM con una función expuesta (`window.refrescarX`).
- **Claves UUIDDecimal nunca por OData** (acaban como `3.09e+37`): script FM o Data API con la clave como texto (F19).
- **`withTimeout`** (15–30 s) en las lecturas; distingue error de **validación zod** de fallo de **transporte** — casi nunca es "la red".
- **Initial props (pull)**: la app pide su bootstrap por `fmFetch` al montar; nunca inyección por HTML/`OnRecordLoad`.
- **Caché**: TanStack Query (dedupe, background refresh, invalidación tras writes).

## Build y deploy

1. `pnpm build` → `dist/index.html` (fichero único autocontenido).
2. **Cierra la pantalla del Web Viewer** en FileMaker (F15) y ejecuta `deploy_html { connectedFileName, appName, path }`.
3. **FileMaker 2026 (estándar Taiko):** el HTML queda en el almacén persistente; el Web Viewer carga `"data:text/html," & GetPersistentData ( "proofkit" ; "<appName>" )`. Es esquema: llega a todos los usuarios y sobrevive a migraciones (lo desplegado en dev viaja a producción). Modo dev dentro de FM: `If ( $$X.WV.DEV ; "http://localhost:5175/?wv=web" ; <fórmula anterior> )` + `Set Web Viewer [ Reset ]`.
4. Antes de FM 2026: `deploy_html` solo hacía Embedded (no sobrevive migraciones) → "store code in a script", Hosted o Downloaded.

## Si algo falla

Sigue la escalera de diagnóstico del repo padre: `agent/docs/taiko/proofkit/troubleshooting.md` (consola primero → zod/typegen → conexión/ventana connector → nombre WV → versiones → caché Vite). Gotchas completos: `agent/docs/taiko/proofkit/gotchas.md`.
