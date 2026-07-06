# ProofKit Web Viewer — convenciones (checklist de arranque)

> Hábitos preventivos que evitan la mayoría de los gotchas ([gotchas.md](gotchas.md)). Aplícalos **al arrancar** cualquier interfaz web ProofKit (Vía 3), no al depurar.
> Procedencia: **[doc]** = documentado por ProofKit (`proofkit.proof.sh`, `llms-full.txt`); **[campo]** = observación empírica de Taiko (field report Eikonsys, 2026-06-16), no necesariamente en la doc oficial.

## Versiones — compruébalas PRIMERO [doc]

El **batching** de la Data API es la palanca nº1 de rendimiento y exige versiones mínimas. Con un add-on antiguo, ProofKit **cae en silencio** al camino directo (sin batching) y la app va lenta **sin dar error** — sospecha de esto antes de culpar al bridge:

- [ ] **ProofKit add-on ≥ 3.0** en el archivo FileMaker (lo instala el asistente/CLI).
- [ ] **`@proofkit/webviewer` ≥ 3.2.0** y **`@proofkit/fmdapi` ≥ 5.2.0** en el proyecto.
- [ ] Ningún archivo en **add-on 2.04** — esa versión podía **dañar privilegios de acceso** (corregido después).

## Datos y rendimiento [doc]

- [ ] **Deja que el `WebViewerAdapter` agrupe las lecturas.** El batching viene **activado por defecto** (ventana ~16 ms): dispara las lecturas juntas y ProofKit las coalesce en una sola script call. **NO las serialices a mano ni evites `Promise.all`** — serializar mata el batching. (Esto **sustituye** al viejo consejo F6.)
- [ ] **Paginación acotada** con `listAll()` / `findAll()` (nunca cargan found sets ilimitados en variables FM). **Tunea el tamaño de página** — prueba 25/50/100/250/500 según ancho de layout, portales y contenedores; en local suele pesar **más** que el batch.
- [ ] **Pantalla de detalle en 1 sola lectura** vía relaciones (padre + líneas + relacionados) en vez de N lecturas.
- [ ] **Bootstrap con initial props (patrón "pull")**: la app pide sus props a FM por `fmFetch` al montar. **No** las inyectes por sustitución de HTML ni desde `OnLayoutEnter`/`OnRecordLoad` (se pierden por carrera). Evita el flash de UI vacía.
- [ ] Aprovecha **TanStack Query** (ya en el stack) para caché, dedupe e invalidación tras writes.

## Esquema y typegen [doc]

- [ ] Config typegen en **`proofkit-typegen-config.jsonc`** (¡**guion**, no punto!). Un nombre mal escrito hace que typegen no encuentre la config y lance el asistente `init`.
- [ ] **Regenerar typegen** tras tocar campos/layouts (`npx @proofkit/typegen`) — es la causa nº1 de "no carga": zod valida en runtime y **rechaza** datos que no casan con el esquema generado.
- [ ] **`clearOldFiles`**: el default de ProofKit es **`true`** (borra `generated/` antes de regenerar; útil para limpiar layouts obsoletos). **Decisión Taiko** (no requisito ProofKit): ponerlo **`false`** y **versionar `generated/`**, para no depender de FM en CI ni quedarnos sin compilar si un typegen falla a medias.

## Runtime / conexión [doc]

- [ ] Rutina de arranque: **"conecta FileMaker → carga app"**. Tras reinicio de FM: **"Connect to MCP → recarga fuerte"**.
- [ ] **Mantén abierta la ventana del connector "Connect to MCP" en modo Navegar.** Cerrarla o pasar el archivo a modo Diseño **rompe el bridge en silencio** (F12).
- [ ] **`$webViewerName` (variable del script FM de callback) == `Object Name` del objeto Web Viewer**, exacto. Ojo: **no es una API JS** (`setWebViewerName` no existe); es la variable que el script de callback usa para devolver el resultado a la instancia correcta.
- [ ] `withTimeout` en las lecturas como red de seguridad **[campo]**: `fmFetch` tiene un error `"timed out"` nativo, pero un timeout propio (15–30 s) evita cuelgues si el callback se pierde.
- [ ] Manejo de errores que **distingue validación de esquema (zod) de fallo de transporte** — no todo lo que falla es "la red".

## Diseñar para reemplazar

El acceso a datos va detrás de un **wrapper Taiko fino**, para que cambiar de **`@proofkit/fmdapi`** (Data API) o **`@proofkit/fmodata`** (OData) → (futuro) plugin Claris sea tocar **un archivo**. No esparzas llamadas directas a `@proofkit/*` por toda la app.
