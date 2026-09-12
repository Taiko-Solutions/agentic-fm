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
