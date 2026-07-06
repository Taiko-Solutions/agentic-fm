# ProofKit Web Viewer — gotchas (guardarraíles)

> Al construir una interfaz web ProofKit (Vía 3), estos hallazgos son guardarraíles. El patrón común: **muchos fallos se disfrazan de error de red** (spinner infinito o "el bridge no respondió") cuando la causa real vive en la frontera **fmFetch / callback / validación de esquema**, o en la **conexión**.
>
> **Procedencia mixta — distínguela.** **[doc]** = documentado por ProofKit (`llms-full.txt`). **[campo]** = field report de Eikonsys (Ibrahim Bittar), 2026-06-16, sobre una solución de 1.300+ layouts; observación empírica, no necesariamente en la doc oficial. Algún hallazgo de campo quedó **desfasado** por cambios de ProofKit (ver **F6**).
>
> **Antes de culpar al rendimiento del bridge, comprueba versiones:** el batching exige `@proofkit/webviewer ≥ 3.2`, `@proofkit/fmdapi ≥ 5.2` y **add-on ≥ 3.0**. Con add-on antiguo, ProofKit cae en silencio al camino directo (sin batching) → app lenta sin error. Ver [conventions.md](conventions.md).

| ID | Síntoma | Causa real | Qué hacer | Fuente |
|----|---------|-----------|-----------|--------|
| **F1** | "No carga", parece timeout | Cambiaste un layout y no regeneraste typegen → zod rechaza toda la lectura | **Regenera typegen** tras tocar campos; mira la consola | doc |
| **F3** | Arranque en frío: todo cuelga | Sin archivo conectado al cargar → el bridge inyecta un stub que solo loguea | **Conecta FileMaker antes de cargar**; recarga fuerte | doc |
| **F12** | Iba bien y de pronto cuelga/falla en runtime | Se cerró la ventana del connector *"Connect to MCP"* o el archivo pasó a **modo Diseño** | **Mantén la ventana connector abierta y en modo Navegar**; reábrela | **doc** |
| **F5** | Toda lectura da timeout | El nombre no casa: la variable `$webViewerName` del script de callback ≠ `Object Name` del objeto WV | Realinea el nombre **exacto**. (No existe una API `setWebViewerName`: es la variable del script FM) | doc |
| **F8** | `connectedFiles` = `[]` tras reiniciar FM | Hay que re-correr *"Connect to MCP"*; sin auto-reconexión | Corre *"Connect to MCP"* + recarga | doc |
| **F7** | typegen borra lo generado y deja el proyecto sin compilar | `clearOldFiles: true` (el **default**) borra `generated/` antes de regenerar | **`clearOldFiles: false`** + commit de `generated/` (convención Taiko) | doc |
| **F6** | (**Desfasado**) creíamos que 4 lecturas en paralelo fallaban y había que serializar | El `WebViewerAdapter` **agrupa por defecto** las lecturas Data API concurrentes (batching, ~16 ms) en una sola script call | **Consejo invertido:** NO serialices a mano ni evites `Promise.all` — dispararlas juntas las coalesce. Serializar mata el batching | **doc** (invierte el consejo de campo) |
| **F2** | `Loading…` largo, sin error | El callback tardó o no llegó. `fmFetch` tiene un error `"timed out"` nativo, pero conviene un timeout propio | Envuelve en `withTimeout` (15–30 s) como red de seguridad | campo (matizado) |
| **F9** | La app ignora un campo recién añadido | Caché de Vite + caché HTTP/cookies del Web Viewer | Reinicia Vite, `rm -rf node_modules/.vite`, recarga fuerte; en FM, el step **`Flush Web Viewer Cookies`** (id 237) limpia la caché de cookies del WV | campo |
| **F4** | 502 / "No active WebSocket" intermitente | Split-brain HTTP/WS del bridge bajo carga (**no aparece en la doc oficial**) | Baja concurrencia; baseline sesión única. Verifica add-on ≥ 3.0 antes de culpar al bridge | **campo** |
| **F11** | Conexiones auto-aprobadas | Seguridad del connector (la doc oficial no describe un "Enhanced Security"; el modelo documentado es la seguridad heredada de FileMaker) | Valora aprobación explícita en entornos sensibles | campo |
| **F10** | `tsc --noEmit` falla desde `node_modules` | Typings del adaptador con ruta no resoluble | Filtra el ruido de `@proofkit/*` en CI | campo |

Diagnóstico paso a paso en [troubleshooting.md](troubleshooting.md); hábitos preventivos en [conventions.md](conventions.md).
