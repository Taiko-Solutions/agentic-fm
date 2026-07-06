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

1. `curl -s http://127.0.0.1:1365/connectedFiles` — debe listar el archivo. Si `[]`: pide correr **"Connect to MCP"** en FileMaker.
2. **La ventana del connector debe seguir abierta y en modo Navegar** durante todo el desarrollo — cerrarla o pasar a modo Diseño rompe el bridge en silencio.
3. `pnpm dev` — con el plugin `fmBridge` de Vite, el dev server habla con el FileMaker real (sin build/upload por cada cambio).

## Reglas de oro (rendimiento y fiabilidad)

- **Versiones mínimas** (si va lento sin error, revisa esto PRIMERO): ProofKit add-on **≥ 3.0** en el archivo, `@proofkit/webviewer` **≥ 3.2**, `@proofkit/fmdapi` **≥ 5.2**. Con add-on viejo, el batching cae en silencio al camino directo.
- **Deja que el `WebViewerAdapter` agrupe las lecturas** (batching por defecto, ~16 ms): dispáralas juntas; **no** las serialices a mano.
- **Paginación acotada**: `listAll()`/`findAll()`; tunea el **page size** (25/50/100/250/500) según ancho de layout/portales/contenedores.
- **Detalle en 1 request**: una lectura con relaciones (padre + hijos) en vez de N.
- **Typegen**: config en **`proofkit-typegen-config.jsonc`** (guion, no punto); **regenera tras tocar campos/layouts** (`npx @proofkit/typegen`) — causa nº1 de "no carga"; convención Taiko: `clearOldFiles: false` + commit de `generated/`.
- **`$webViewerName`** (variable del script FM de callback) debe igualar **exacto** el `Object Name` del Web Viewer.
- **`withTimeout`** (15–30 s) en las lecturas; distingue error de **validación zod** de fallo de **transporte** — casi nunca es "la red".
- **Initial props (pull)**: la app pide su bootstrap por `fmFetch` al montar; nunca inyección por HTML/`OnRecordLoad`.
- **Caché**: TanStack Query (dedupe, background refresh, invalidación tras writes).

## Build y deploy

1. `pnpm build` → `dist/index.html` (fichero único autocontenido).
2. `deploy_html { connectedFileName, appName, path }` (herramienta MCP) — método **Embedded** por defecto. ⚠️ Embedded **no sobrevive a migraciones de datos**: si la solución migra, valora "store code in a script" / Hosted / script post-deploy OttoFMS.

## Si algo falla

Sigue la escalera de diagnóstico del repo padre: `agent/docs/taiko/proofkit/troubleshooting.md` (consola primero → zod/typegen → conexión/ventana connector → nombre WV → versiones → caché Vite). Gotchas completos: `agent/docs/taiko/proofkit/gotchas.md`.
