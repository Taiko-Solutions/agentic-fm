# ProofKit Web Viewer — los 11 gotchas (guardarraíles obligatorios)

> Al construir una interfaz web ProofKit (Vía 3), estos hallazgos son **guardarraíles de aplicación obligatoria**. El patrón común: **muchos fallos se disfrazan de error de red** (spinner infinito o "el bridge no respondió"). Procedencia: field report de Eikonsys (Ibrahim Bittar), 2026-06-16, sobre una solución de 1.300+ layouts.

| ID | Síntoma | Causa real | Qué hacer | Sev |
|----|---------|-----------|-----------|-----|
| **F1** | "No carga", parece timeout | Cambiaste un layout y no regeneraste typegen → zod rechaza toda la lectura | **Regenera typegen** tras tocar campos; mira la consola | Alta |
| **F2** | `Loading…` eterno, sin error | `fmFetch` no tiene timeout propio; el callback nunca llegó | Envuelve en `withTimeout` (15–30 s) | Alta |
| **F3** | Arranque en frío: todo cuelga | Sin archivo conectado al cargar → bridge inyecta un stub que solo loguea | **Conecta FileMaker antes de cargar**; recarga fuerte | Alta |
| **F7** | typegen fallido deja el proyecto sin compilar | `clearOldFiles: true` borra antes de regenerar | **`clearOldFiles: false`** + commit de `generated/` | Alta · pérdida datos |
| **F4** | 502 / "No active WebSocket" intermitente | Split-brain HTTP/WS del bridge bajo carga | Baja concurrencia; baseline sesión única | Media |
| **F5** | Toda lectura da timeout tras renombrar el WV | `setWebViewerName` ≠ `Object Name` del objeto | Realinea el nombre **exacto** | Media |
| **F6** | 4 lecturas en paralelo fallan; en serie van | Canal single-threaded | **Serializa** (`await`), nada de `Promise.all` | Media |
| **F8** | `connectedFiles` = `[]` tras reiniciar FM | Sin auto-reconexión | Corre *"Connect to MCP"* + recarga | Media |
| **F11** | Conexiones auto-aprobadas | *Enhanced Security: off* por defecto | Valora aprobación explícita en entornos sensibles | Info |
| **F9** | App ignora un campo recién añadido | Caché de Vite + caché HTTP del navegador | Reinicia Vite, `rm -rf node_modules/.vite`, recarga fuerte | Baja |
| **F10** | `tsc --noEmit` falla desde `node_modules` | Typings del adaptador con ruta no resoluble | Filtra el ruido de `@proofkit/*` en CI | Baja |

Diagnóstico paso a paso en [troubleshooting.md](troubleshooting.md); hábitos preventivos en [conventions.md](conventions.md).
