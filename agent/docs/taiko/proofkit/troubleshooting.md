# ProofKit Web Viewer — escalera de diagnóstico ("no carga")

> Cuando una interfaz web ProofKit (Vía 3) "no carga", **no asumas red**. Sigue esta escalera en orden. Ver los hallazgos completos en [gotchas.md](gotchas.md).

1. **Consola del navegador primero.** F1/F2/F5 solo se ven ahí. Empieza siempre por aquí.
2. **¿Error de validación zod?** → **regenera typegen** (F1). Es la causa nº1 tras tocar campos de un layout.
3. **¿"no connected FileMaker file"?** → conecta el archivo + recarga fuerte (F3/F8). Comprueba `connectedFiles`.
4. **¿Renombraste el Web Viewer?** → `setWebViewerName` debe coincidir **exacto** con el `Object Name` del objeto WV (F5).
5. **¿Lecturas en paralelo?** → serialízalas con `await`; nada de `Promise.all` de varios `find()` (F6).
6. **¿Falla a ratos bajo carga?** → límite conocido del bridge (F4); baja concurrencia, sesión única de baseline.
7. **¿Campo nuevo ignorado?** → caché de Vite/navegador (F9): reinicia Vite, `rm -rf node_modules/.vite`, recarga fuerte.

**Regla de oro:** spinner infinito = frontera fmFetch/callback/zod, no la red. Si no tienes `withTimeout` en las lecturas, un callback perdido cuelga para siempre (F2) — ponlo antes de depurar nada más.
