# ProofKit Web Viewer — escalera de diagnóstico ("no carga")

> Cuando una interfaz web ProofKit (Vía 3) "no carga", **no asumas red**. Sigue esta escalera en orden. Ver los hallazgos completos en [gotchas.md](gotchas.md).

1. **Consola del navegador primero.** F1/F2/F5 solo se ven ahí. Empieza siempre por aquí.
2. **¿Error de validación zod?** → **regenera typegen** (F1). Es la causa nº1 tras tocar campos de un layout.
3. **¿"no connected FileMaker file"?** → conecta el archivo + recarga fuerte (F3/F8). Comprueba `connectedFiles`.
4. **¿La ventana del connector "Connect to MCP" sigue abierta y en modo Navegar?** → si se cerró o está en modo Diseño, el bridge se rompe en silencio (F12). Reábrela.
5. **¿El nombre casa?** → el objeto Web Viewer debe llamarse **`web`** (o la app fija el suyo con `globalSettings.setWebViewerName` y los scripts puente respetan `callback.webViewerName`) (F5/F13). El diálogo "No webviewer named X" es este caso.
6. **¿Va lento (no roto)?** → comprueba versiones: el batching exige add-on ≥ 3.0, `@proofkit/webviewer ≥ 3.2`, `@proofkit/fmdapi ≥ 5.2`; con add-on viejo cae al camino directo sin batching. **No serialices las lecturas a mano** — deja que el adapter las agrupe (invierte F6).
7. **¿Campo nuevo ignorado?** → caché de Vite/navegador (F9): reinicia Vite, `rm -rf node_modules/.vite`, recarga fuerte; en FM, el step `Flush Web Viewer Cookies` limpia las cookies del WV.
8. **¿Callbacks perdidos o diálogos con otra ventana delante?** → `PK_send_callback` entrega al `web` de la **ventana activa** (F14): cierra connector/"ProofKit App" delante de tu pantalla, no entres en Modo Buscar en el layout del WV mientras carga, apaga `refetchOnWindowFocus`.
9. **¿`pnpm dev` dentro del Web Viewer de FM da diálogos o "Cargando…" infinito?** → `fmBridge` inyecta un FileMaker falso (F16): URL `?wv=web` y `fmBridge` condicionado. **¿"window.FileMaker was not available"?** → espera a `window.FileMaker` antes de renderizar (F17).
10. **¿El MCP `proofkit-mcp` no conecta ("Connection closed")?** → desde 3.2.0 el comando es `proofkit mcp` (F18): `.mcp.json` con `command: proofkit, args: [mcp]` y `~/.local/bin` en el PATH.

**Regla de oro:** spinner infinito = frontera fmFetch/callback/zod o **conexión** (ventana connector), **no** la red. `fmFetch` tiene un `"timed out"` nativo, pero pon `withTimeout` en las lecturas por si el callback se pierde (F2).
