# Propuestas Upstream

## 2026-03-10 — Documentar patrón Omit Find para búsquedas "distinto de"

- **Categoría**: knowledge
- **Descripción**: FileMaker no tiene operador "distinto de" (`≠`) en modo búsqueda. Para buscar registros donde un campo NO tiene un valor concreto, hay que usar Find + New Record/Request + Omit Record. Este patrón debería documentarse como knowledge ya que es un gotcha habitual.
- **Archivos afectados**: nuevo `agent/docs/taiko/knowledge/omit-find-pattern.md`
- **Origen**: Conversión de Roles | Control Bloqueo — necesidad de buscar roles con PermisoBloqueo ≠ 2 para la regla de FechaTodosRoles3.

## 2026-03-10 — validate_snippet.py solo acepta un archivo por invocación

- **Categoría**: script_utility
- **Descripción**: `validate_snippet.py` solo acepta un argumento posicional `path`. Sería útil aceptar múltiples archivos para validar varios snippets en una sola invocación (ej: `validate_snippet.py file1.xml file2.xml`).
- **Archivos afectados**: `agent/scripts/validate_snippet.py`
- **Origen**: Al validar los dos XML regenerados de roles-control-bloqueo, el comando con dos archivos falló con error de argumentos no reconocidos.

## 2026-04-22 — Multi-developer configuration for distributed teams

- **Category**: architecture / fm-package
- **Summary**: Let multiple developers work on the same FMS-hosted solution, each from their own machine, with their own local `agentic-fm` repo and their own companion server — without any of them having to edit FM scripts to slot themselves into the flow.

### The problem

`Get agentic-fm path` implicitly assumes one developer per solution. First time it runs it opens a folder picker and stores the chosen path in `$$AGENTIC.FM`. That global lives in the FM session of whoever is running things — fine for a single dev caching their own path, but it falls apart the moment two people open the same solution from different machines in parallel.

On top of that, `Explode XML` (interactive mode) hardcodes the companion URL to `http://localhost:8765`. With the new exclusive-bind policy where `COMPANION_BIND_HOST` is set to a LAN or Tailscale address instead of `127.0.0.1`, `localhost` just answers "Connection refused" — every developer needs their own bind address baked in somewhere.

The workaround most teams end up with is ugly: a chain of `If Get(AccountName) = "..."` branches inside `Get agentic-fm path`, each assigning a hardcoded path and companion IP. It works, but it doesn't scale (every new developer edits the script), it mixes environment config with package logic, and it forces machine-specific data to live inside the `.fmp12` instead of in the repo where it belongs.

### Two ideas behind the proposal

The first: each developer's config should live next to their companion, not inside the FM solution. `automation.json` already carries the local repo path and companion bind — extending it to describe the developer too feels natural. The FM solution only needs to know how to ask the companion who it's talking to.

The second: the agentic-fm FM package should expose a lookup mechanism keyed on `AccountName` (or an equivalent identifier), and `Get agentic-fm path` uses that lookup to resolve the config. The lookup cascades through a few sources, in order:

1. `$$AGENTIC.FM` already cached in the session — fast path, no work needed.
2. A remote lookup against the companion server, assuming the solution knows how to reach it.
3. A lookup against an `agentic_fm_users` table inside the FM package — optional, useful offline.
4. Interactive dialog as last resort — the current behavior, preserved for onboarding.

### Three options I considered

**Option A — FM table inside the agentic-fm package.** Add an `agentic_fm_users` table to the package file with `account_name`, `repo_path`, `companion_host`, `companion_port`. `Get agentic-fm path` queries it and fills the globals. A `Configure agentic-fm user` script provides the UI for create/edit. It's FM-native, has no external moving parts, and is versionable via table export. Downsides: a minor breaking change (every client solution adds the relationship to the package file), and every developer sees everyone else's config — low-sensitivity but noisy.

**Option B — a `/whoami` endpoint on the companion plus a minimal bootstrap in FM.** The companion reads `automation.json` (which already holds per-solution config) and exposes `/whoami` returning the block for the current user. All config stays outside FM — whatever each developer tweaks lives in their own `automation.json`. Zero breaking change on the FM side. The one wart is the bootstrap: FM has to know how to reach the companion before it can ask anything, which means a tiny local preference file or pre-loaded global somewhere.

**Option C — a custom function with an embedded mapping.** `Get agentic-fm path` queries a custom function `AgenticFmUserConfig()` that returns a JSON blob of all users. Nothing new to build, but it just moves the multi-user config from a script to a CF inside the `.fmp12` — same root problem, different shape.

### Recommendation

A and B in two iterations.

Iteration 1, fast and with no breaking changes: implement Option B. The bootstrap can be an environment variable or a file like `~/.agentic-fm/bootstrap.json`, read by `Get agentic-fm path`:

```
{
  "companion_url": "http://<ip-or-hostname>:<port>"
}
```

The script reads that file, calls `{companion_url}/whoami`, and loads the response into the globals. The companion answers from `automation.json` by looking up `AccountName` (either as a query param or an origin header — either works).

Iteration 2: add the `agentic_fm_users` table from Option A as a fallback for when the companion is down — offline work, onboarding, or debugging.

### Concrete upstream changes

1. `agent/config/automation.json` grows an optional `users` section:
   ```
   "users": {
     "<account_name>": {
       "repo_path": "<posix-path>",
       "companion_host": "<ip-or-hostname>",
       "companion_port": 8765
     }
   }
   ```

2. `agent/scripts/companion_server.py` gets `GET /whoami?account=<name>` that reads `automation.json.users[account]` and returns it. A `400 account not configured` handles the miss case.

3. `filemaker/agentic-fm.xml` — `Get agentic-fm path` refactored: fast path if `$$AGENTIC.FM` is already cached, otherwise read the bootstrap, call `/whoami` with `Get(AccountName)`, load the globals, and keep the interactive fallback for when anything upstream is missing.

4. Same file — `Explode XML` swaps the hardcoded URL `http://localhost:8765/explode` for `"http://" & $$AGENTIC.FM.COMPANION.HOST & ":" & $$AGENTIC.FM.COMPANION.PORT & "/explode"`. The globals are populated by `Get agentic-fm path`.

5. `filemaker/README.md` picks up a new "Multi-developer setup" section walking through the bootstrap and the `/whoami` flow.

### Compatibility

The current flow — folder picker dialog plus hardcoded `localhost` — keeps working as a fallback whenever `automation.json.users` is missing or doesn't list the current developer, or when no bootstrap file is present. Solo developers see no functional change; everything here is opt-in. Distributed teams migrate by adding their block to `automation.json.users` and dropping a minimal bootstrap file on their machine. No edits to FM scripts required.

### Where this came from

Ran into this deploying agentic-fm against a multi-file solution — seven `.fmp12` files hosted on a shared development FMS — where the team expects several developers to work in parallel, each on their own machine, local repo, and companion with a different bind IP. The hardcoded `If AccountName = ...` pattern inside `Get agentic-fm path` worked as a one-off, but made it obvious that per-developer environment configuration deserves a better home than the body of an FM script.

## 2026-07-03 — Knowledge: monitorizar FileMaker desde un vigía externo (OData) — gotchas de tiempo y privilegios

- **Categoría**: knowledge
- **Descripción**: Al integrar un monitor externo (Zabbix) que lee estado de FileMaker por OData de solo-lectura, tres gotchas reutilizables. (1) **OData respeta privilegios de campo**: un campo con *no access* para la cuenta OData es invisible en `$metadata` y devuelve `8309 "The field named 'X' does not exist in a specified table"` — mensaje engañoso (parece typo/caché pero es permisos). Diferencial de diagnóstico: ExecuteSQL/Data API con cuenta admin sí ve el campo; OData con la cuenta RO no. Fix: Custom Field Privileges → view only (+ `[Any New Field]` view only). (2) **OData devuelve timestamps *naive* etiquetados `Z`** aunque sean hora local (`2026-07-03T18:32:00Z` siendo las 18:32 CEST) → un parser externo (JS `Date.parse`) los lee como UTC → desfase de zona (~2 h) → alertas tardías. Fix: hacer la aritmética de tiempo en FileMaker (`Get(CurrentHostTimestamp)`, hora del host) y exponer los **segundos ya calculados**; el monitor solo lee un número. Alternativa: exponer epoch Unix UTC (`Get(CurrentTimeUTCMilliseconds) - 62135596800000`). (3) **Los campos calc de "edad desde X" deben ser *unstored***: si son stored se congelan en el valor de escritura (0). Patrón recomendado: el monitor lee por OData un número que FM calcula (unstored) y lo extrae por JSONPath; cuenta OData dedicada de solo lectura; vigía externo para no compartir el punto de fallo de lo vigilado.
- **Archivos afectados**: nuevo `agent/docs/taiko/knowledge/fm-external-monitoring.md` + índice en `agent/docs/taiko/knowledge/MANIFEST.md` (keywords: zabbix, monitor externo, odata, timestamp, zona horaria, unstored, privilegios de campo, heartbeat)
- **Origen**: Proyecto 973 Fase 2 — heartbeat de la cola SimpleQ vigilado por Zabbix vía OData. Patrón genérico FM ↔ monitor externo; sin datos de cliente.

## 2026-07-06 — fmlint param-fidelity rules (X001–X003): machine-enforce the silent-discard class

- **Categoría**: fmlint / catalogs / tooling
- **Descripción**: FileMaker descarta en silencio los elementos de parámetro cuyo tag no coincide con lo que el step espera (el step se importa bien; el parámetro cae a su default). Hoy esa clase de bug vive como prosa en AGENTS.md. Propuesta: familia nueva de reglas fmlint que la detecta mecánicamente usando el propio catálogo — X001 (elemento de param desconocido según `params[].xmlElement`, con sugerencia difflib), X002 (param presente sin su `discriminator`, p.ej. `<Layout>` sin `<LayoutDestination>`), X003 (combinaciones verificadas: `Style="Card"` sin bitmask `Styles`; `<FileReference>` anidado en `<Script>` o sin `<UniversalPathList>`). Incluye: suite de tests con smoke masivo contra `snippet_examples/` (0 falsos positivos tras allowlist `{Text, Animation}`), 2 fixes de catálogo descubiertos por el smoke (param `Layout` ausente en New Window; `UniversalPathList` ausente en Generate Response from Model), `agent/scripts/ci_checks.py` (valida catálogos JSON + tests conversor + tests fmlint; el caso real que lo motiva: una coma faltante dejó todo el step-catalog como JSON inválido sin que nada lo detectara), gate de sanity en el hook pre-push, y fix de `install-hooks.sh` para git worktrees (`--git-common-dir`). Al aprobarse, la prosa CRITICAL equivalente de AGENTS.md puede sustituirse por una tabla de 3 filas que referencia las reglas (hecho ya en la capa Taiko como demostración).
- **Archivos afectados**: `agent/fmlint/rules/param_fidelity.py` (nuevo), `agent/fmlint/rules/__init__.py`, `agent/fmlint/tests/` (nuevo), `agent/catalogs/step-catalog-en.json` (2 params), `agent/scripts/ci_checks.py` (nuevo), `agent/scripts/hooks/pre-push`, `agent/scripts/install-hooks.sh`, `.claude/CLAUDE.md`/`AGENTS.md` (adelgazamiento)
- **Origen**: Auditoría de fluidez del sistema (2026-07-06). Detonantes: fix e36ed6a (coma en catálogo = JSON inválido silencioso) y b768b13 (conversor perdía params de transacciones) — misma familia de fallos que los bloques CRITICAL acumulados desde Borneo 944.x.

## 2026-07-06 — session_start.py: consolidar los chequeos de arranque en un solo comando

- **Categoría**: script_utility / AGENTS.md
- **Descripción**: AGENTS.md exige hoy 4+ chequeos separados al arrancar cada sesión (update check, environment detection, embedded freshness, plug-in detection, más PROJECT.md), cada uno un round-trip del agente. `agent/scripts/session_start.py` los ejecuta todos en una sola llamada, aislados y tolerantes a fallos (WARN/SKIP, nunca crash), con salida compacta de una línea por chequeo y `--json` para consumo programático. Añade además chequeos útiles no cubiertos: frescura/task de CONTEXT.json y salud del bridge de terceros. La sección "Session startup" de AGENTS.md puede compactarse a un párrafo que referencia el script (hecho como callout aditivo en la capa Taiko como demostración). stdlib only.
- **Archivos afectados**: `agent/scripts/session_start.py` (nuevo), `.claude/CLAUDE.md`/`AGENTS.md` (compactación de "Session startup")
- **Origen**: Auditoría de fluidez (2026-07-06): 5-6 round-trips medidos antes del primer prompt útil en cada sesión.

## 2026-07-07 — Metodología de tests Taiko: doctrina genérica multi-cliente (borrador, requiere engine nuevo)

- **Categoría**: knowledge / testing infrastructure
- **Descripción**: Doctrina de tests automatizados para Controllers FileMaker Taiko (patrón API-like: params JSON in, resultado JSON out). Specs en YAML viven en el vault Obsidian (`Proyectos/Soporte/<Cliente>/Tests/`), nunca en el repo — solo el engine genérico (`agent/testing/`: runner, client OData multi-archivo, assertions, fixtures con cleanup automático por tracking de IDs, spec_loader con JSON Schema, reporter consola+JSONL+bitácora vault) es código compartido. Diseñada cliente-agnóstica desde el origen: migrar a un cliente nuevo son 3 pasos sin tocar el engine. Incluye guardarraíles de seguridad (el runner rechaza ejecutar contra hosts que matcheen `prod`/`produccion`/`live` o una lista negra explícita) y aislamiento por solución (el `cliente:` del front-matter decide qué bloque de `automation.json` se usa). El engine `agent/testing/` **no existe todavía** — esto es la doctrina/diseño, escrito como piloto en Borneo, pendiente de implementación y de revisión de equipo antes de aplicarse a `taiko`.
- **Archivos afectados**: nuevo `agent/testing/` (runner.py, client.py, assertions.py, fixtures.py, side_effects.py, spec_loader.py, reporter.py, vault_path.py, schemas/spec.schema.json); nuevo `agent/docs/taiko/knowledge/testing-methodology.md` (o vault `Proyectos/Taiko/Agentic-FM-Taiko/Arquitectura/Testing-Metodologia.md` como espejo legible, referenciado pero aún no creado); `agent/config/testing.json.example`
- **Origen**: Sesión de diseño Marco + Claude "agentic-fm-tests-piloto-borneo" (2026-05-02). Documento completo (borrador) vive local sin commitear en el clon de Borneo: `agent/docs/taiko/testing-methodology.md` — no se ha subido a `origin/taiko` a la espera de esta revisión.

## 2026-07-11 — fmlint: detectar pasos inalcanzables tras Exit Script / Halt Script incondicional

- **Categoría**: fmlint
- **Descripción**: `Exit Script [ If ( Get(LastMessageChoice) = 2 ; "Cancelado" ) ]` en mitad de un script parece una salida condicional pero no lo es — `Exit Script` siempre sale; el `If()` solo condiciona el texto devuelto. Todo paso posterior al mismo nivel de anidamiento es código muerto y el script muere en silencio a mitad de flujo. Caso real: dos scripts de prueba generados con este patrón nunca llegaban a su `Perform Script` y la verificación aparentaba estar hecha sin haberse ejecutado. Propuesta: regla nueva (p. ej. B00x) que marque como WARNING cualquier paso que siga a un `Exit Script`/`Halt Script` habilitado dentro del mismo bloque (mismo nivel de If/Loop), con hint sugiriendo el patrón correcto `If [condición] → Exit Script → End If`. Cero falsos positivos esperables: un Exit Script legítimo al final de rama no tiene pasos posteriores en su bloque.
- **Archivos afectados**: `agent/fmlint/rules/` (regla nueva), tests de fmlint
- **Origen**: Sesión Borneo 944 circuito Peticiones (2026-07-11) — bug #4 del plan de implementación: patrón de cancelación post-diálogo mal autoría en dos scripts de prueba, indetectado por fmlint y por revisión visual del HR.

## 2026-07-11 — fm_xml_to_snippet.py: New Window pierde todos sus parámetros

- **Categoría**: converters
- **Descripción**: al convertir SaXML→fmxmlsnippet, el paso `New Window` (id 122) se emite como `<Step id="122" name="New Window"/>` autocerrado — se pierden Style, Name, Layout y bounds. El SaXML lo serializa como `Parameter type="WindowReference"` con `<WindowReference><Style/><Name/><LayoutReferenceContainer/><Bounds/><Options/></WindowReference>`, estructura que el conversor no mapea. Pegado así, FileMaker crea el paso con defaults (ventana sin nombre en el layout actual) — en el patrón transaccional Taiko (`New Window` condicional antes de `Open Transaction`) rompe el `Close Window [Name: $WindowName]` posterior y el aislamiento de la transacción, en silencio. Forma correcta de destino: `<LayoutDestination value="SelectedLayout"/> + <NewWndStyles Styles="…"/> + <Name><Calculation/></Name> + <Layout id name/>`. Misma familia que el fix de Revert/Open Transaction (b768b13). Mitigación mientras tanto: diff round-trip `snippet_to_hr` del snippet convertido contra el sanitizado antes de desplegar cualquier script convertido.
- **Archivos afectados**: `agent/scripts/fm_xml_to_snippet.py`, tests del conversor
- **Origen**: Sesión Borneo 944 circuito Peticiones (2026-07-11), Task 3 — detectado con diff round-trip al convertir el script 1303 (que abre ventana transaccional con nombre `$WindowName` y layout concreto); reconstruido a mano antes de desplegar, sin incidente.

## 2026-07-11 — deploy.py: _switch_to_document matchea ventanas por substring y elige archivo equivocado

- **Categoría**: script_utility
- **Descripción**: `_switch_to_document` selecciona la ventana destino con AppleScript `whose name contains "<target_file>"`. Cuando el nombre de un archivo es prefijo de otro en la misma solución multi-archivo (p. ej. `Borneo` y `Borneo-Controller`), el filtro matchea ambos y se cliquea el primero — deploy Tier 2/3 aterriza en el archivo equivocado reportando éxito. Caso real: dos scripts nuevos con `--file Borneo` se crearon en `Borneo-Controller`, con referencias de campo irresolubles (TOs del frontend). Propuesta: match exacto contra el nombre de ventana normalizado (los títulos de ventana FM son `<archivo> (<layout>)` — comparar el prefijo hasta el paréntesis, o `name is` con fallback a `begins with "<file> ("`); si hay 0 o >1 candidatos, abortar con error explícito en vez de clicar el primero. Añadir verificación post-switch (`get name of window 1` debe empezar por el archivo pedido) antes de pegar.
- **Archivos afectados**: `agent/scripts/deploy.py` (`_switch_to_document`), quizá companion `/trigger`
- **Origen**: Sesión Borneo 944 circuito Peticiones (2026-07-11), Task 4 — detectado con ProofKit `get_script_names` tras un deploy Tier 3 aparentemente exitoso.

## 2026-07-12 — Knowledge: List() no agrega found set sobre TO externa en servidor

- **Categoría**: knowledge (taiko)
- **Descripción**: `List(TOexterna::campo)` devuelve solo el valor del registro actual (no de todo el found set) cuando la TO apunta a una fuente de datos externa (ESS / otro archivo FileMaker) Y el script corre en servidor (OData/PSOS). En FileMaker Pro con TO local funciona; en servidor con TO externa, no. Síntoma real: un script que notificaba a los integrantes de un departamento solo alcanzaba a 1 de N. Diagnóstico: `Get(FoundCount)` = N correcto, pero `List(TOexterna::campo)` = 1. Patrón de fix (idéntico en espíritu a `cross-to-pointer-in-loops.md`): iterar el found set con `Go to Record [First]` + Loop + acumular `List($acc; TO::campo)` del registro actual + `Go to Record [Next; Exit after last]`. Candidato a `agent/docs/taiko/knowledge/` (p. ej. ampliar `cross-to-pointer-in-loops.md` con una sección "List() sobre TO externa en servidor" o doc nuevo).
- **Archivos afectados**: `agent/docs/taiko/knowledge/` (doc nuevo o sección), `agent/docs/taiko/knowledge/MANIFEST.md`
- **Origen**: Borneo 944 circuito Peticiones (2026-07-12), script `Peticiones | Notificar Departamento {json}`.

## 2026-07-12 — Patrón: modo de envío (pruebas/produccion/off) en el chokepoint de email

- **Categoría**: knowledge (taiko) / template
- **Descripción**: Patrón "email sandbox" para el script central de envío transaccional: al inicio, dos config (`$EmailModo` ∈ {produccion, pruebas, off}, `$EmailDestinoPruebas`). En `pruebas` reescribe `to` al buzón de pruebas, elimina cc/bcc y marca el asunto `[PRUEBAS]`; el log registra el destinatario real ("[REDIRIGIDO A PRUEBAS → x] destinatario real: …"). En `off` no envía. Como dev y prod son archivos separados, la config es por-archivo (redeploy para cambiar de modo). Resuelve el escenario "ir a producción sin enviar correos reales todavía / cliente prueba sin spamear usuarios". Reutilizable en cualquier solución Taiko con envío transaccional. Candidato a `agent/docs/taiko/knowledge/` o `agent/docs/taiko/templates/`. Nota: sustituye el antipatrón de hardcodear un `$ToTest` en cada script emisor.
- **Archivos afectados**: `agent/docs/taiko/knowledge/` o `templates/`, MANIFEST
- **Origen**: Borneo 944, `Email Transaccional | Enviar` (1396), 2026-07-12.

## 2026-09-04 — Bug: `snippet_to_hr.py` no aplica `invertedHr` del catálogo

- **Categoría**: herramientas (`agent/scripts/`)
- **Descripción**: El conversor `agent/scripts/snippet_to_hr.py` ignora el flag `invertedHr` que sí declara `agent/catalogs/step-catalog-en.json`. Los pasos cuyo parámetro se llama `NoInteract` (Sort Records, Go to Record/Request/Page, Perform Find, Commit Records/Requests, …) tienen `hrLabel: "With dialog"` con `invertedHr: true`, porque el XML expresa la **negación**: `<NoInteract state="True"/>` significa **"With dialog: Off"**. El conversor imprime el valor crudo, así que muestra `With dialog: On` — exactamente lo contrario de lo que hace el paso. `grep -n "invertedHr" agent/scripts/snippet_to_hr.py` no devuelve nada: el flag no está implementado.
- **Por qué importa**: la vista previa HR es el artefacto que el desarrollador revisa **antes** de pegar en Script Workspace. Un booleano invertido en esa vista es exactamente el tipo de fallo que la previsualización debería atrapar y en cambio introduce. El XML es correcto; lo que engaña es la vista. Además el revisor puede "corregir" un XML que ya estaba bien.
- **Fix propuesto**: al renderizar un parámetro de tipo `boolean`, si su definición en el catálogo trae `invertedHr: true`, invertir el valor antes de aplicar `hrEnumValues` / el `On`/`Off`. Un solo punto en el renderizador de parámetros.
- **Extra (menor)**: los parámetros `type: "complex"` — como el `SortList` de Sort Records — se renderizan vacíos (`Sort order:` sin contenido). Sería útil que al menos listasen `TO::Campo` y la dirección de cada `<Sort>`.
- **Archivos afectados**: `agent/scripts/snippet_to_hr.py`
- **Origen**: refactor de un guión de interfaz con `Sort Records` + `Go to Record/Request/Page`. Ambos pasos, copiados literalmente de `agent/snippet_examples/`, aparecían en la vista previa como `With dialog: On` cuando el XML dice lo contrario. Patrón genérico del conversor; sin datos de cliente.

## 2026-09-08 — check_embedded_agfm.py no encuentra nada en un explode real (3 desajustes de ruta) — **APLICADO en `taiko`**

- **Categoría**: script_utility
- **Descripción**: El chequeo de frescura del código agentic-fm embebido nunca llega a comparar nada en un repo de la rama `taiko`: reporta siempre "No agentic-fm objects found in the exploded solution" y `session_start.py` lo muestra como `[SKIP] embedded — nada que comprobar`, así que el fallo pasa desapercibido y la deriva del código embebido queda sin detectar. Son tres desajustes acumulados entre lo que el script espera y lo que produce hoy `fm-xml-export-exploder` 0.5.1 con el layout multi-BD de la rama `taiko`:
  1. **Subcarpeta por BD.** `_index_embedded_scripts()` hace `scripts_dir.glob("*.xml")` sobre `agent/xml_parsed/scripts`, pero los ficheros están en `agent/xml_parsed/scripts/<Solución>/...`. Glob no recursivo → índice vacío.
  2. **Carpetas del Script Workspace.** El exploder replica el árbol de carpetas de scripts, así que los objetos agentic-fm quedan en `scripts/<Solución>/agentic-fm - ID 37/`, y dentro hay aún subcarpetas (`OData - ID 41`, `Extras - ID 46`). Ni siquiera `rglob` bastaría sin contemplar el anidamiento.
  3. **Sufijo ` - ID N` en el nombre de fichero, y CF en otra carpeta.** El stem real es `Explode XML - ID 39`, no `Explode XML`, así que `_key(p.stem)` nunca casa con el nombre canónico. Y `_embedded_context_text()` busca `custom_functions_sanitized/` o `custom_function_calcs/`, ninguna de las cuales genera el exploder 0.5.1: la CF Context sale en `custom_function_stubs/<Solución>/Context - ID 3.xml`.
  Arreglo propuesto: recorrer con `rglob("*.xml")` bajo `scripts/`, normalizar el stem quitando el sufijo `` - ID \d+`` antes de `_key()`, y añadir `custom_function_stubs/` (con la misma normalización) a las fuentes que prueba `_embedded_context_text()`. Conviene además que `session_start.py` distinga "no hay solución explotada" (SKIP legítimo) de "hay explode pero no se reconoció ningún objeto" (WARN), para que este modo de fallo no vuelva a ser silencioso.
- **Estado**: implementado en la rama `taiko` de este repo base. Se desarrolló y verificó primero contra un explode real en un clon de proyecto, porque el fallo solo se manifiesta con una solución explotada de verdad. Sigue siendo candidato a petrowsky únicamente si allí se adopta el chequeo (hoy el fichero no existe en `upstream/main`). Qué se hizo:
  1. `_index_embedded_scripts()` recorre con `rglob` y normaliza el stem con `_stem_without_id()` (nueva).
  2. `_embedded_context_text()` busca recursivamente y añade `custom_function_stubs` a las fuentes.
  3. La firma semántica se sustituye por **comparación en HR**: ambos lados se renderizan con `snippet_to_hr.py --raw` (`_hr_from_steps()`), lo que elimina de raíz el ruido de `<Repetition>` y de orden.
  4. `_looks_like_converter_loss()` clasifica lo que queda: una pérdida del conversor solo QUITA texto (subsecuencia), mientras que la deriva real añade o cambia. Nuevo estado `OK~` para "coincide salvo ruido conocido".
  5. Las etiquetas de enum se normalizan leyendo `hrEnumValues` del **step catalog** (`_enum_label_map()`), sin hardcodear ningún step; solo se mapean valores de 6+ caracteres para que `True/False → On/Off` no pueda corromper texto ajeno.
  6. `_context_signature(fold_case=True)` absorbe la reescritura de mayúsculas del motor (`GetAsTimestamp` → `GetAsTimeStamp`).
  7. Nuevo flag `--diff`, y `main()` devuelve rc 1 cuando hay explode pero no se reconoce nada (antes rc 0 silencioso). `session_start.py` consume ahora `--json` en vez de parsear la tabla, y su aviso dice explícitamente que se revise el diff antes de repegar.
  8. Tests: `agent/scripts/test_check_embedded_agfm.py` (18 casos, fixtures sintéticas sin datos de cliente), enganchado a `ci_checks.py`. Verificado que **fallan contra la versión anterior** del módulo y pasan contra la arreglada.
  Resultado contra un explode real: de "nothing to check" a 3 OK / 5 OK~ / 3 STALE, y los 3 STALE coinciden uno a uno con la deriva confirmada a mano.
- **Archivos afectados**: `agent/scripts/check_embedded_agfm.py` (`_index_embedded_scripts`, `_embedded_context_text`, `_key`/normalización de stem), `agent/scripts/session_start.py` (distinguir SKIP de WARN en el chequeo `embedded`)
- **Origen**: Setup del entorno agentic-fm para la solución `Domotica` (2026-09-08). Los 10 scripts agentic-fm y la CF `Context` estaban correctamente instalados y explotados —verificado a mano en `agent/xml_parsed/scripts/Domotica/agentic-fm - ID 37/` y `custom_function_stubs/Domotica/Context - ID 3.xml`— pero el chequeo declaró que no había nada que comprobar. Afecta a cualquier repo de cliente de la rama `taiko`, no solo a este: MemPalace tiene un drawer del wing `cdec` describiendo exactamente el mismo síntoma (los 10 scripts + CF Context presentes en el explode de las 3 BD y el check diciendo "nothing to check"), así que ya se había topado con esto al menos una vez sin que llegara a registrarse aquí.
- **Nota adicional (segundo bug, mismo fichero)**: aunque se arreglen las rutas, la firma semántica tampoco es estable entre formatos. Al comparar a mano se obtienen falsos STALE masivos por ruido del par SaXML→conversor: `<Repetition><Calculation>1</Calculation></Repetition>` que FileMaker añade a los `Set Variable` al guardar, y diferencias de orden/duplicación de `<Calculation>` en steps como `Go to Layout` (`C:$layout` una vez frente a dos). `_signature_from_steps()` debería excluir el subárbol `<Repetition>` y comparar de forma insensible a esas asimetrías, o el chequeo pasará de "no detecta nada" a "lo marca todo STALE".

## 2026-09-08 — fm_xml_to_snippet.py pierde parámetros al convertir SaXML (falsos positivos y scripts rotos en sandbox)

- **Categoría**: script_utility
- **Descripción**: Al convertir un script de `xml_parsed/scripts/` (SaXML) a fmxmlsnippet, el conversor descarta en silencio parámetros de varios steps. Detectado comparando los 10 scripts agentic-fm embebidos en una solución contra el bundle `filemaker/agentic-fm.xml`, pasando ambos lados por `fm_xml_to_snippet.py` → `snippet_to_hr.py --raw`. Casos observados:
  - `Save a Copy as XML` → se pierde el destino (`UniversalPathList`): `Save a Copy as XML [ Destination file: $output ; Window name: … ]` queda en `Save a Copy as XML [ Window name: … ]`. El propio `scripts_sanitized/` del exploder lo marca como `⚠️ PARAMETER "UniversalPathList" NOT PARSED ⚠️`.
  - `Save Records as Snapshot Link` → se pierde `Output path`.
  - `Perform AppleScript` → se pierde el texto del script (`Perform AppleScript [ Text ; tell me to activate ]` queda en `Perform AppleScript [ Text ]`).
  - `Get Folder Path` → se pierden `Dialog title`, `Default location` y la variable destino, y el título acaba mal ubicado en `Repetition`.
  El impacto va más allá del chequeo de frescura: `.claude/CLAUDE.md` documenta el flujo "cuando se referencia para modificar un script existente de `xml_parsed/`, cópialo a `sandbox/`", y ese flujo pasa justamente por este conversor — así que un script copiado a sandbox y re-pegado puede volver a FileMaker **sin la ruta de destino, sin el texto del AppleScript o sin el título del diálogo**, silenciosamente. Es la misma familia de fallo que los params de transacciones del commit b768b13. Propuesta: cubrir estos `xmlElement` en el conversor tomando la definición del step catalog (que ya los describe) en lugar de una lista manual, y añadir un test de round-trip SaXML→snippet→HR sobre `filemaker/agentic-fm.xml`, que ejercita los 10 scripts y detectaría regresiones de esta clase.
- **Archivos afectados**: `agent/scripts/fm_xml_to_snippet.py`, nuevo test de round-trip en `agent/fmlint/tests/` (o `agent/scripts/test_fm_xml_to_snippet.py`), `agent/scripts/ci_checks.py` (incluirlo en el gate)
- **Origen**: Setup del entorno para la solución `Domotica` (2026-09-08). Al intentar decidir si los scripts agentic-fm embebidos estaban al día, 6 de las 7 "diferencias" resultaron ser pérdidas del conversor y no deriva real. Sin filtrar ese ruido, cualquier chequeo de frescura arreglado seguiría dando falsos STALE.

## 2026-09-10 — step-catalog: `Perform Script` no declara el modo "By name" (falso positivo X001)

- **Categoría**: catalog
- **Descripción**: la entrada `Perform Script` (id 1) declara sólo `Calculation` (parámetro), `Script` (por id) y `FileReference` (cross-file). No declara el modo **By name**, que se emite como `<Calculated><Calculation>nombre</Calculation></Calculated>` antes del `<Calculation>` del parámetro. Como `_allowed_children()` de `param_fidelity.py` construye la lista de hijos válidos desde `params[]`, la regla **X001 marca `<Calculated>` como descarte silencioso — falso positivo**: es la forma canónica y funciona (verificado por round-trip: el sandbox emitió `<Calculated>` y el explode posterior muestra `<List name="By name" value="2">` en FM). El coste no es sólo ruido: X001 es precisamente la regla que caza descartes reales, y acostumbrarse a ignorarla en este paso desarma la defensa. **Fix aplicado en local**: añadir a `params[]` un `{"xmlElement":"Calculation","type":"namedCalc","hrLabel":"By name","wrapperElement":"Calculated"}` — mismo modelado que `Add Account` (`wrapperElement: "AccountName"`). Tras el fix, `SelectorContacto_Seleccionar_925.xml` pasa limpio.
- **Archivos afectados**: `agent/catalogs/step-catalog-en.json` (entrada `Perform Script`)
- **Origen**: Sesión Borneo 944.10 (2026-09-10), Tarea 1 — al añadir un callback `Perform Script [By name]` al Manager de la Utility de Contactos. Borneo tiene 18 usos del patrón (6 selectores `$ReturnScript`, 4 routers `$initializeShadow`, 3 `CerrarSelector*`, `AGFMScriptBridge`, ejemplos ProofKit), así que el falso positivo aparece en toda esa familia.

## 2026-09-10 — fm_xml_to_snippet.py: `Perform Script [By name]` pierde el nombre del script

- **Categoría**: converters
- **Descripción**: al convertir SaXML→fmxmlsnippet, un `Perform Script` en modo By name pierde el nombre calculado. El SaXML lo serializa como `<Parameter type="List"><List name="By name" value="2"><Calculation>…</Calculation></List></Parameter>`, y el conversor emite sólo `<Calculation>` con el **parámetro**, sin el `<Calculated>` del nombre. Resultado: el paso convertido queda como un Perform Script sin destino. Misma familia que el bug de `New Window` (2026-07-11): parámetros envueltos en un contenedor del SaXML que el conversor no mapea. Caso concreto: convertir `Contacto.Seleccionado.Router` (951) produce `<Step id="1" name="Perform Script"><Calculation><![CDATA[$asJson]]></Calculation></Step>` — se ha perdido `$initializeShadow`. Refuerza la mitigación ya recomendada en la entrada de New Window: **diff round-trip `snippet_to_hr` contra el sanitizado antes de desplegar cualquier script convertido**.
- **Archivos afectados**: `agent/scripts/fm_xml_to_snippet.py`, tests del conversor
- **Origen**: Sesión Borneo 944.10 (2026-09-10), Tarea 1 — detectado al buscar la forma canónica del By name para el callback del Manager de Contactos.

## 2026-09-12 — Convención: resultados de script también en variable global (copiables)

- **Categoría**: knowledge (taiko) / convenciones
- **Descripción**: cuando un script presenta un resultado al desarrollador o al usuario con `Show Custom Dialog`, **el diálogo no permite seleccionar ni copiar el texto**. Si ese resultado es un dato que se va a reutilizar (métricas de auditoría, JSON de diagnóstico, listados de IDs), se pierde: hay que transcribirlo a mano o hacer una captura. Convención propuesta: **publicar siempre el resultado en una o dos variables globales antes de mostrar el diálogo** — `$$<Ambito>` con el JSON y `$$<Ambito>Texto` con el resumen legible — y que el diálogo muestre la variable de texto en lugar de recomponer el mensaje. Así el resultado queda copiable desde el Visor de datos sin cambiar la experiencia. Coste cero (dos `Insert Calculated Result`) y evita que el diálogo sea un callejón sin salida. Candidato a `agent/docs/taiko/CODING_CONVENTIONS.md` (sección "Preferred Script Steps" o una nueva "Presentación de resultados") y a mencionar en los templates `clew-simple.md`.
- **Archivos afectados**: `agent/docs/taiko/CODING_CONVENTIONS.md`, `agent/docs/taiko/templates/clew-simple.md`
- **Origen**: Borneo 944 (2026-09-12), `AuditarEstructuraInmuebles.Controller` — Marco tuvo que enviar una captura de pantalla porque el diálogo de la auditoría no dejaba copiar las métricas.

## 2026-09-13 — Library: found set a partir de una lista de IDs (OR con Set Field By Name)

- **Categoría**: library / knowledge
- **Descripción**: patrón reutilizable para dejar en el found set de cualquier layout los registros de una lista de IDs obtenida por `ExecuteSQL` (p. ej. filtrar por una tabla puente N:M respetando un flag `Activo`): `Enter Find Mode` → bucle con un *find request* por ID (`New Record/Request` desde el 2º) → `Set Field By Name [ $campoId ; "==" & GetValue ( $Ids ; $i ) ]` + criterio opcional de texto en la misma petición → `Perform Find`. Recibir los campos por `GetFieldName` lo hace independiente de la TO del layout (sirve para dos layouts sobre TOs distintas de la misma tabla). Incluir el aviso: el criterio de texto debe ir sobre un campo **almacenado y relleno**; un campo auto-enter nunca evaluado en registros migrados deja la búsqueda vacía sin error.
- **Archivos afectados**: nuevo item en `agent/library/` + entrada en MANIFEST; mención en `agent/docs/taiko/knowledge/executesql-pattern.md`
- **Origen**: Borneo 944.11 (2026-09-13), subscript compartido de selector de contactos por empresa activa.

## 2026-09-13 — Knowledge: auditar relaciones multi-predicado tras migrar 1:N → N:M

- **Categoría**: knowledge (taiko)
- **Descripción**: al sustituir un FK directo (1:N) por una tabla puente (N:M), el FK antiguo queda "congelado" en su primer valor histórico. Además de los scripts que filtran por él, hay que auditar las **relaciones del grafo con más de un predicado** que lo siguen usando como condición adicional (p. ej. `Registro::FKContacto = Contacto::Id` **y** `Registro::FKEmpresa = Contacto::FKEmpresaAntiguo`): el ID se guarda bien pero el campo relacionado se muestra en blanco para los registros nuevos o reasignados. Checklist: `grep` en `relationships.index` de las TOs de la tabla migrada con `Equal+Equal` que referencien el FK antiguo, más layouts/scripts/pivots que las usen.
- **Archivos afectados**: nuevo `agent/docs/taiko/knowledge/migracion-1n-a-nm-checklist.md` + MANIFEST
- **Origen**: Borneo 944.11 (2026-09-13): contacto preferente en blanco en Inmuebles y Demandas por relaciones con el FK antiguo como 2ª condición.

## 2026-09-13 — Knowledge/ProofKit: "FileMaker is in a paused state" y conector colgado

- **Categoría**: knowledge (proofkit gotchas)
- **Descripción**: `execute_filemaker_sql` y demás herramientas ProofKit fallan con *"FileMaker is in a paused state, so scripts cannot execute right now"* cuando el desarrollador tiene un diálogo modal, un script en pausa o el Script Debugger detenido; no es un fallo de conexión. Y si `PK_get_relation_info` devuelve timeout con *"MCP Server Connector window is open but is not responding"*, hay que cerrar esa ventana y relanzar *Connect To ProofKit MCP*. Documentar ambos síntomas con la acción a pedir al desarrollador para no diagnosticar mal.
- **Archivos afectados**: `agent/docs/taiko/proofkit/gotchas.md`
- **Origen**: Borneo 944.11 (2026-09-13), varias consultas en vivo interrumpidas.

## 2026-09-13 — Knowledge: obtener el ID de un script recién creado sin explode ni OData

- **Categoría**: knowledge
- **Descripción**: el placeholder technique necesita el ID del script nuevo antes de generar los `Perform Script` que lo llaman. Si OData no responde y no se quiere relanzar el explode, basta con una expresión en el Visor de datos: `Let ( [ ~n = ScriptNames ( Get ( FileName ) ) ; ~i = ScriptIDs ( Get ( FileName ) ) ] ; While ( [ ~k = 1 ; ~r = "" ] ; ~k ≤ ValueCount ( ~n ) and ~r = "" ; [ ~r = If ( GetValue ( ~n ; ~k ) = "<Nombre>" ; GetValue ( ~i ; ~k ) ; "" ) ; ~k = ~k + 1 ] ; ~r ) )`. `get_script_names` de ProofKit devuelve solo nombres. Añadir al skill `multi-script-scaffold` como vía alternativa.
- **Archivos afectados**: `.claude/skills/multi-script-scaffold/SKILL.md`, `agent/docs/knowledge/script-ids.md`
- **Origen**: Borneo 944.11 (2026-09-13), OData con timeout al resolver el ID del subscript compartido.

## 2026-09-13 — fmlint: falsos positivos al lintar pasos copiados del Script Workspace (X001 + C003) — **APLICADO en `taiko`**

- **Categoría**: fmlint
- **Descripción**: Dos falsos positivos al lintar XML leído del portapapeles con `clipboard.py read`:
  - **X001** marcaba `<DisableStepCollapsed state="…"/>` como elemento de parámetro desconocido. FileMaker lo añade a TODOS los pasos al copiar desde el Script Workspace (estado de plegado del editor; equivale al `<Boolean type="Collapsed">` del SaXML) y no es un parámetro, así que no figura en ningún `params` del catálogo. Arreglo: allowlist `EDITOR_STATE_ELEMENTS` en `param_fidelity.py`, separada de `GLOBAL_ALLOWED`, sin tocar el catálogo. X001 sigue saltando con elementos desconocidos reales del mismo paso.
  - **C003** troceaba los nombres de custom function con espacio de nombres: en `transaction.SetError ( … )` el `\b` de `_FUNC_CALL_RE` casaba justo después del punto y se informaba `SetError`. Como consecuencia, declarar el nombre real en `extra_known_functions` nunca silenciaba el aviso. Arreglo: la regex captura el nombre completo con puntos (`(?<![\w.])([A-Za-z_][\w.]*\w|[A-Za-z_])\s*\(`). Declarar solo el sufijo ya no basta, que es lo correcto.
- **Archivos afectados**: `agent/fmlint/rules/param_fidelity.py`, `agent/fmlint/rules/calculations.py`, `agent/fmlint/tests/test_param_fidelity.py` (2 tests), `agent/fmlint/tests/test_known_function.py` (nuevo, 4 tests), `agent/fmlint/README.md` (nota C003)
- **Origen**: Lint de pasos copiados de una solución real (2026-09-13). En 9 ficheros de sandbox guardados desde el portapapeles, 822 de 1152 X001 (severidad ERROR) eran `DisableStepCollapsed`, lo que enmascaraba los X001 legítimos. Mejora posible, no incluida: cargar la lista de CFs desde `CONTEXT.json` o desde `xml_parsed/custom_functions_sanitized/` para no depender de `extra_known_functions`.

## 2026-09-17 — fmlint: el corpus smoke test relee el contexto del proyecto por fichero (19 min en un clone grande)

- **Categoría**: fmlint / tooling / performance
- **Descripción**: `CorpusSmokeTest.test_snippet_examples_corpus_is_clean` (`agent/fmlint/tests/test_param_fidelity.py`) linta los 216 ficheros de `agent/snippet_examples/` con un único `LintRunner`, pero el coste por fichero crece con el tamaño del explode del clone, señal de que el contexto del proyecto (índices y objetos de la solución) se vuelve a leer en cada `lint_file()` en vez de reutilizarse. Medido el 2026-09-17 con el mismo corpus en dos clones: en uno de 3 soluciones, 1–2,7 s por fichero (~4 min en total); en uno de 12 soluciones, 5–11 s por fichero → **17 tests en 18 min 47 s**. Efecto práctico: `agent/scripts/ci_checks.py` aborta con `TimeoutExpired` en clones grandes, porque llama a los tests de fmlint con un límite de 300 s, y el desarrollador se queda sin la comprobación previa al push.
- **Propuesta**: cachear el contexto del proyecto en `LintRunner` (cargarlo una vez por instancia, o memoizarlo por `project_root`) de modo que el corpus se linte con una sola lectura. Alternativas, si el contexto debe recargarse: que el test lo construya una vez y lo inyecte, y subir o hacer configurable el límite de `ci_checks.py`. Conviene medir antes y después con el mismo corpus en un clone grande.
- **Archivos afectados**: `agent/fmlint/engine.py`, `agent/fmlint/context.py`, `agent/fmlint/tests/test_param_fidelity.py`, `agent/scripts/ci_checks.py`.
- **Origen**: Puesta al día de varios clones con la rama `taiko` (2026-09-17). Los tests **pasan** en ambos clones: es rendimiento, no un fallo de reglas.
