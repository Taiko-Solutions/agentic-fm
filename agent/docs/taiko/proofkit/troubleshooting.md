# ProofKit Web Viewer — escalera de diagnóstico ("no carga")

> Cuando una interfaz web ProofKit (Vía 3) "no carga", **no asumas red**. Sigue esta escalera en orden. Ver los hallazgos completos en [gotchas.md](gotchas.md).

1. **Consola del navegador primero.** F1/F2/F5 solo se ven ahí. Empieza siempre por aquí.
2. **¿Error de validación zod?** → **regenera typegen** (F1). Es la causa nº1 tras tocar campos de un layout.
3. **¿"no connected FileMaker file"?** → conecta el archivo + recarga fuerte (F3/F8). Comprueba `connectedFiles`.
4. **¿La ventana del connector "Connect to MCP" sigue abierta y en modo Navegar?** → si se cerró o está en modo Diseño, el bridge se rompe en silencio (F12). Reábrela.
5. **¿El nombre casa?** → la variable `$webViewerName` del script de callback debe coincidir **exacto** con el `Object Name` del objeto Web Viewer (F5). No existe una API `setWebViewerName`.
6. **¿Va lento (no roto)?** → comprueba versiones: el batching exige add-on ≥ 3.0, `@proofkit/webviewer ≥ 3.2`, `@proofkit/fmdapi ≥ 5.2`; con add-on viejo cae al camino directo sin batching. **No serialices las lecturas a mano** — deja que el adapter las agrupe (invierte F6).
7. **¿Campo nuevo ignorado?** → caché de Vite/navegador (F9): reinicia Vite, `rm -rf node_modules/.vite`, recarga fuerte; en FM, el step `Flush Web Viewer Cookies` limpia las cookies del WV.

**Regla de oro:** spinner infinito = frontera fmFetch/callback/zod o **conexión** (ventana connector), **no** la red. `fmFetch` tiene un `"timed out"` nativo, pero pon `withTimeout` en las lecturas por si el callback se pierde (F2).
