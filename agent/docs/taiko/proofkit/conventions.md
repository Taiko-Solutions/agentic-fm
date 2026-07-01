# ProofKit Web Viewer — convenciones (checklist de arranque)

> Hábitos preventivos que evitan la mayoría de los 11 gotchas ([gotchas.md](gotchas.md)). Aplícalos **al arrancar** cualquier interfaz web ProofKit (Vía 3), no al depurar.

- [ ] **`clearOldFiles: false`** en `proofkit-typegen.config.jsonc`; `generated/` versionado y **commit antes de cada `typegen`** (F7 puede dejar el proyecto sin compilar).
- [ ] Utilidad **`withTimeout`** (o `{ timeoutMs }`) compartida en **todas** las lecturas (F2). 15–30 s.
- [ ] **Lecturas serializadas** (`await`); sin `Promise.all` de varios `find()` — el canal es single-threaded (F6).
- [ ] **`setWebViewerName` == `Object Name`** del Web Viewer, verificado exacto (F5).
- [ ] Rutina de arranque: **"conecta FileMaker → carga app"**; tras reinicio de FM: **"Connect to MCP → recarga fuerte"** (F3/F8).
- [ ] **Regenerar typegen** tras tocar campos de un layout (F1) — es la causa nº1 de "no carga".
- [ ] Manejo de errores que **distingue validación de esquema (zod) de fallo de transporte** — no todo lo que falla es "la red".
- [ ] Baja concurrencia como baseline; sube solo si el bridge lo aguanta (F4).

## Diseñar para reemplazar

El acceso a datos (Data API / OData) va detrás de un **wrapper Taiko fino**, para que cambiar de `@proofkit/fmodata` → `fm-odata-client` → (futuro) plugin Claris sea tocar **un archivo**. No esparzas llamadas directas a `@proofkit/*` por toda la app.
