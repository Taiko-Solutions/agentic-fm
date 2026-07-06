# Python

Always use `python3` — never bare `python`. macOS does not ship a `python` binary; the system Python is only available as `python3`. Core scripts and the `agent/fmlint/` package use the Python standard library only — no virtual environment is required for them.

## Virtual environment (optional — skill dependencies)

Some skills (e.g. `icon-swap`) require Python packages beyond the standard library. These are installed in an **optional venv** inside the project folder. The venv is gitignored and does not affect stdlib-only scripts.

**When to set up:** Only when a skill reports missing dependencies (e.g. `fm_svg_convert.py --check-deps` fails). Do not proactively create the venv — prompt the developer first.

**Setup (macOS):**
```bash
python3 -m venv agent/.venv
source agent/.venv/bin/activate
pip install cairosvg Pillow
```

**System dependencies (if needed for stroke-to-fill SVG conversion):**
```bash
brew install potrace
```

**Running scripts with the venv:** When the venv exists, use `agent/.venv/bin/python3` instead of bare `python3` for scripts that need the extra packages:
```bash
agent/.venv/bin/python3 agent/scripts/fm_svg_convert.py --check-deps
```

Or activate the venv first: `source agent/.venv/bin/activate`

**Important:** On some macOS configurations, `pip install` to the system Python is blocked by default. The venv approach avoids this entirely. Never suggest `sudo pip install` or `--break-system-packages`.

# Session startup

> **(Taiko) Atajo unificado — un solo comando.** `python3 agent/scripts/session_start.py` ejecuta TODOS los chequeos de arranque de esta sección en una sola llamada (update de git con detección taiko/main, entorno/sandbox, frescura del código embebido, companion + plug-in) **más** el gating ProofKit (`:1365/connectedFiles`), la presencia de `PROJECT.md` y la frescura de `CONTEXT.json`. Córrelo **una vez por sesión**, interpreta su resumen (OK/WARN/FAIL/SKIP) y actúa según lo que indique cada línea. Las subsecciones siguientes quedan como referencia de qué significa cada chequeo y como fallback si el script no está disponible.

At the start of each new CLI/IDE session, before responding to the first prompt, run an update check:

```bash
git fetch origin --quiet 2>/dev/null; git rev-list HEAD..origin/main --count 2>/dev/null
```

If the result is greater than `0`, pause and notify the user before proceeding:

> **agentic-fm update available** — your clone is N commit(s) behind `origin/main`. Run `git pull --ff-only` to update before continuing, then restart your agent session. See `UPDATES.md` for details.

Do this **once per session**, not on every prompt. If the check fails (no network, not a git repo, etc.), skip it silently and continue.

> **(Taiko) Solo repo base.** Este chequeo contra `origin/main` es el mecanismo del repo **base** agentic-fm (origen petrowsky). En un **repo de proyecto cliente NO aplica**: esos repos se actualizan trayendo la **rama `taiko`** del repo base (`git pull <remoto-taiko> taiko` → merge a la rama del proyecto), nunca `origin/main`, y no proponen PRs a petrowsky. Ver "Propagación de reglas y actualizaciones (Taiko)".

## Environment detection

Also at session start, check if you are running in a sandboxed or non-macOS environment:

```bash
uname -s 2>/dev/null; command -v osascript &>/dev/null && echo "OSASCRIPT" || echo "NO_OSASCRIPT"
```

If `uname` returns `Linux` or `osascript` is not found, read `agent/docs/SANDBOXED_ENVIRONMENT.md` before proceeding. That document covers setup paths, platform limitations, and the filesystem bridge workflow for sandboxed agents.

## Embedded agentic-fm freshness

The agentic-fm scripts (`AGFM*`, `Push Context`, `Explode XML`, the menu, …) and the `Context` custom function are pasted into each host solution during setup and do **not** update automatically when the bundled versions in `filemaker/` change. An embedded copy can silently fall behind and cause confusing failures.

Also at session start, once a solution has been exploded, run the freshness check:

```bash
python3 agent/scripts/check_embedded_agfm.py
```

It compares the embedded objects (from `agent/xml_parsed/`) against the bundled reference and reports `OK` / `STALE` / `MISSING` per object. If it finds any `STALE` or `MISSING` object, notify the user that the solution's embedded agentic-fm code is out of date and should be re-deployed from `filemaker/`. It exits `0` and prints "nothing to check" when no solution is exploded — in that case, skip silently. Do this **once per session**.

## Plug-in detection (optional enhancement)

Also at session start, ask the companion server whether the optional AgenticFM plug-in is present and **usable**. The companion is the single detection broker — one call answers it:

```bash
curl -s --max-time 5 http://local.hub:8765/health
```

Read the `plugin` block in the response:

- `plugin.usable == true` — the plug-in is installed, reachable, **and** licensed (`status ∈ {active, trial}`). Read `agent/docs/PLUGIN_INTEGRATION.md` and enter **plugin-preferred mode**: prefer the plug-in for understanding/context, authoring, validation, and install, with the OSS path as the fallback (full routing table in that doc).
- `plugin.installed == true` but `usable == false` — installed but the license/trial has lapsed or the server is down. Stay on the **pure OSS path**. At most **once per session**, you may surface the gentle lapsed-license nudge described in `PLUGIN_INTEGRATION.md` (§10.4). Never block or degrade the OSS workflow.
- block absent / `installed == false` / companion unreachable — pure OSS path, no nudge.

Gate on `usable`, never on `installed`. Do this **once per session**, not per prompt. If the check fails for any reason, skip it silently and continue — the OSS workflow never depends on the plug-in.

# Local development context

If `PROJECT.md` exists at the project root, read it at session start. It contains local-only context: meta-project notes, toolchain details, and `external_tools/` documentation. Its absence is normal — it is gitignored and will not be present in collaborator environments.

## Documentation Audience

- When writing docs for this project, default audience is END-USERS who download the repo as a tool, NOT collaborative developers/contributors, unless explicitly told otherwise.

# Overview

This project is designed to create FileMaker objects — primarily scripts and calculations — in the clipboard-supported fmxmlsnippet format. Developers reference and use the HR (human-readable) format for scripts. The following folders are used.

- _sandbox/_ is where all newly created or in-progress work is stored.
- _CONTEXT.json_ is the primary source of IDs, names, relationships, and other metadata for the current task. See **Context system** below.
- _context/_ contains pre-extracted index files — a secondary lookup source. See **Context system** below.
- _xml_parsed/_ is the XML output from the FileMaker solution. See **Context system** below.
- _catalogs/_ contains two catalogs: the step catalog (`step-catalog-en.json`) — structured index of all FileMaker script steps with parameter definitions, types, enums, and HR signatures; and the function catalog (`function-catalog.json`) — index of all 358 FileMaker calculation functions with name and prototype. The step catalog is the primary reference for step XML structure; the function catalog validates function names and signatures in calculations.
- _snippet_examples/_ is an **archival** reference folder. The step catalog is the single source of truth for step structure. Read snippet_examples only when the catalog's `notes` field is insufficient.
- _fmlint/_ is the FMLint linter package. Run via `python3 -m agent.fmlint` to validate fmxmlsnippet XML or human-readable scripts.

# Context system

Multiple sources of context are available about the FileMaker solution. Always start with the most efficient source.

## CONTEXT.json (primary)

`agent/CONTEXT.json` is the primary source when it exists and reflects the current task. It is generated by FileMaker and scoped to the objects relevant to the current layout and task. It contains:

- `task` — a natural-language description of what to create
- `current_layout` — the layout the user is on, with name, ID, and base table occurrence
- `tables` — relevant tables with their fields (name, ID, type, auto-enter, calculations)
- `relationships` — how the relevant tables connect (TOs, join fields, cascade settings)
- `scripts` — scripts that may need to be called, with name and ID
- `layouts` — layouts that may need to be navigated to, with name, ID, and base TO
- `value_lists` — value lists that may be needed, with name, ID, and values

**All IDs in CONTEXT.json are ready to use directly in fmxmlsnippet output.** No lookup is required. See `agent/CONTEXT.example.json` for the full schema.

**CONTEXT.json only exists for established solutions where context has been exported from FileMaker.** Always check for its presence before attempting to read it — if absent, derive context from the index files, xml_parsed, or by asking the developer directly. Never fail or stall because CONTEXT.json is absent.

**Proactively suggest a Push Context refresh when the request doesn't match the current context.** Before generating any code, check whether the developer's request aligns with `current_layout.name` and `task`. If mismatched, suggest running Push Context on the correct layout before proceeding.

**Context must be refreshed when the FM state changes during a build** — e.g., after a new layout is created, the agent needs a fresh CONTEXT.json scoped to that layout.

**When CONTEXT.json does not exist or is stale**, ask the developer to navigate to the relevant layout in FileMaker and run the **Push Context** script. This script prompts for a task description, calls the `Context()` custom function, and writes the result directly to `agent/CONTEXT.json`.

> **(Taiko) Refresh automatizable — intenta la vía agéntica antes de pedir el manual.** Si hay automatización disponible (bloque `odata` en `automation.json` para Tier 3, o companion activo para Tier 2), el agente puede refrescar el contexto él mismo: `python3 agent/scripts/refresh_context.py --task "…" [--layout X] [--yes]` — encadena `AGFMGoToLayout` + `Push Context` y espera el `CONTEXT.json` fresco. **Confirma SIEMPRE con el desarrollador antes de disparar** (regla de AUTOMATION.md; tras su OK, pasa `--yes`). El refresh manual queda como fallback si no hay vía o falla.

## Index files (secondary)

`agent/context/{solution}/*.index` files are pipe-delimited lookup tables covering the entire solution. Use these when CONTEXT.json does not contain the needed object. Each file has a header comment documenting the column format.

- `fields.index` — every field across all tables
- `relationships.index` — the relationship graph
- `layouts.index` — all layouts with name, ID, base TO, and folder path
- `scripts.index` — all scripts with name, ID, and folder path
- `table_occurrences.index` — TO-to-base-table mapping
- `value_lists.index` — value list names, sources, and values

Search with grep: `grep "Invoices Details" "agent/context/SolutionApp/layouts.index"`

## xml_parsed (last resort)

Only fall back to grepping `agent/xml_parsed/` if the needed information is not in CONTEXT.json or the index files.

- ALWAYS use grep to search — never read full file contents
- Prefer `scripts_sanitized/` for understanding script logic over `scripts/` XML
- `scripts/` contains Save As XML (SaXML) format — use `agent/scripts/fm_xml_to_snippet.py` to convert to fmxmlsnippet when needed
- `custom_menus/` and `custom_menu_sets/` contain one XML file per custom menu/set
- Do NOT read `xml_parsed/layouts/` unless analyzing layout objects — layout XML is extremely verbose and rarely needed; layout IDs and names are in CONTEXT.json and `layouts.index`

## Automation

The agentic-fm script collection and OData-based automation are documented in `agent/docs/AUTOMATION.md`. See that file when triggering FM scripts programmatically or working with `agent/config/automation.json`.

# Output format

The developer always works in **human-readable (HR) script format**. The agent's final deliverable is **fmxmlsnippet XML** written to `agent/sandbox/`.

- Output should contain ONLY script steps within the `<fmxmlsnippet type="FMObjectList">` wrapper — **do NOT wrap in `<Script>` tags**.
- Use the simplified fmxmlsnippet syntax from the step catalog, NOT the verbose XML format found in xml_parsed/scripts.
- The `script-preview` skill generates an HR preview before XML generation — use it when the developer wants to review logic before committing to XML.
- Line numbers always reference the human-readable script (`scripts_sanitized/`), never the raw XML.

## fmxmlsnippet rules

> **CRITICAL — No XML comments in fmxmlsnippet output**
>
> XML comments (`<!-- -->`) are **silently discarded** when FileMaker reads fmxmlsnippet content from the clipboard. Never use XML comments to document script intent — use FileMaker script steps instead:
>
> - **Inline comment** → `# (comment)` step (`id="89"`)
>   ```xml
>   <Step enable="True" id="89" name="# (comment)">
>     <Text>This is an inline comment visible in the Script Workspace.</Text>
>   </Step>
>   ```
> - **Blank line** → empty self-closing `# (comment)` with no `<Text>` element
>   ```xml
>   <Step enable="True" id="89" name="# (comment)"/>
>   ```
> - **Doc block comment** → disabled `Insert Text` step targeting `$README`
>   ```xml
>   <Step enable="False" id="61" name="Insert Text">
>     <SelectAll state="False"/>
>     <Text>PARAMETER FORMAT:&#xD;  JSONSetElement ( "{}" ; ...</Text>
>     <Field>$README</Field>
>   </Step>
>   ```

- The id attribute of most tags can be 0 — FileMaker auto-assigns on paste.
- Certain steps require a matching partner (If/End If, Loop/End Loop, etc.). The catalog's `blockPair` field identifies these relationships and each step's role (`open`, `middle`, `close`).
- The `selfClosing` flag in the catalog indicates `<Step ... />` vs `<Step ...>...</Step>`.
- XML comments within snippet_examples are for reference only — never include them in output.

> **CRITICAL — Param fidelity is machine-enforced by fmlint (X001–X003)**
>
> FileMaker **silently discards** param child elements whose tag doesn't match what the step expects — the step imports fine but the parameter falls back to its default. fmlint's param-fidelity rules (`agent/fmlint/rules/param_fidelity.py`) validate every `<Step>` against the catalog's `params[].xmlElement` and `discriminator`, so **running `python3 -m agent.fmlint` (mandatory step 6) catches this class mechanically**:
>
> | Trap | Rule |
> |---|---|
> | Unknown param element — e.g. `<State>` on Set Error Capture (must be `<Set>`); `<Option>`/`<ExitAfterLast>` on Go to Record (must be `<RowPageLocation>`/`<Exit>`) | X001 |
> | Param without its discriminator — e.g. `<Layout>` without `<LayoutDestination>` on Go to Layout / New Window → FM silently ignores the layout ref | X002 |
> | `Style="Card"` without the `Styles` bitmask (opens as Document; use `Styles="3222339600"`) · `<FileReference>` nested inside `<Script>` or missing `<UniversalPathList>` (cross-file ref doesn't resolve) | X003 |
>
> Full examples and correct forms: `agent/docs/taiko/knowledge/silent-discard-params.md`.

> **CRITICAL — `List()` must end with a `""` terminator (Taiko convention)**
>
> `List ( "x" )` with a single argument throws a parser error on paste (the calc ends up commented out `/*…*/`). Always terminate: `List ( "accion" ; "" )`. Apply uniformly in `$REQUIRED` lists and calls inside `error.CreateVarsFromKeys` / `error.ThrowIfMissingParam` / `error.ThrowIfMissingVar`.

> **CRITICAL — Internal layout `name` ≠ exported filename**
>
> The exporter may write `Utility__Peticiones - ID 295.xml` (TWO underscores) when the layout's internal `name` is `Utility_Peticiones` (ONE). Mismatches fail silently in `<Layout name>` refs AND in runtime literals (`Get(LayoutName)` checks, button params). Always verify against the **first column** of `agent/context/<solution>/layouts.index`, and prefer `Get ( LayoutName )` over hardcoded literals. (Real case: Borneo 944.9, dead back button.)

> **CRITICAL — Utility shadow `AsJSON` calc must use storage `Global`, not unstored**
>
> As a normal unstored calc, `AsJSON` evaluates in the current layout's TO context and **returns `{}` when read from another layout** — the Manager merges `{}` and downstream checks pass through silently. Fix in FM: Manage Database → field → Storage Options → **"Use global storage"**, uniformly on **every** Utility's AsJSON field. (Discovered in Borneo 944.9; document affected files in the solution's 01-Decisiones-Tomadas.md.)



# Core workflow

## Before writing

**MANDATORY: Before writing ANY script or function:**

1. Read `agent/CONTEXT.json` for the task description and all reference IDs (when present)
2. Read `agent/docs/CODING_CONVENTIONS.md` — all generated FileMaker code must follow these conventions
3. Scan `agent/docs/knowledge/MANIFEST.md` for keyword matches against the current task — read and apply matching documents
4. For scripts: grep the step catalog for each step type used (see **Step catalog** below); validate any calculation function name against the function catalog (see **Function catalog** below)
5. Substitute the specific IDs/names/values from CONTEXT.json

## After writing

**MANDATORY: After writing or updating a file within agent/sandbox/:**

6. Run `python3 -m agent.fmlint agent/sandbox/<filename>` to validate. Fix any ERROR-severity diagnostics before presenting to the user; review WARNING-severity.
6b. (Optional) Preview the human-readable form of the generated script before deploying: `python3 agent/scripts/snippet_to_hr.py agent/sandbox/<filename>`. Use this to verify logic visually or to show the developer what the script will look like in Script Workspace without pasting.
7. Deploy using `agent/scripts/deploy.py`. Use the tier appropriate for the situation (see `agent/config/automation.json`). When falling back to Tier 1 (manual paste), present instructions in this exact format:

> The script is on your clipboard. To install it:
>
> 1. Open **Script Name** in Script Workspace
> 2. **⌘A** — select all existing steps and delete
> 3. **⌘V** — paste

**Container and non-macOS environments**: `deploy.py` detects the runtime environment automatically. When running inside a Docker container or any non-macOS host, AppleScript execution is delegated to the companion server on the macOS host via `/trigger`. No special handling is needed — just call `deploy.py` the same way.

## Lookup decision tree

Two kinds of lookup are needed: **solution-specific references** (layout, field, script IDs) and **step structure** (XML elements and attributes).

1. Does CONTEXT.json have the reference? → Use it directly. Done.
2. Is it a step structure question? → Grep the step catalog. Done.
3. Reference missing from CONTEXT.json? → Search the appropriate `agent/context/{solution}/*.index` file.
4. Still missing? → Grep `agent/xml_parsed/` as last resort. Never read entire files.
5. **(Taiko) ¿Necesitas el estado VIVO** — valor actual, "¿existe aún X?", drift de un layout concreto? → si `connectedFiles` responde, usa **ProofKit MCP** (`execute_filemaker_sql`, `layout_metadata`, `display_erd_diagram`) como capa de frescura **sobre** las fuentes estáticas. **Nunca** para volcar estructura masiva (timeout en soluciones grandes). Ver `agent/docs/taiko/fm-access.md`.

## Step catalog

`agent/catalogs/step-catalog-en.json` is the canonical reference for all FileMaker script steps. **Never read the full file** (~200KB+). Always grep for individual entries:

```bash
grep -A 60 '"name": "Step Name"' "agent/catalogs/step-catalog-en.json"
```

**Priority order: catalog params → catalog notes → snippet_examples (archival)**

- For steps with `"status": "complete"` — construct XML directly from the catalog's `params` array, `selfClosing` flag, and `id`
- For behavioral context — check the catalog's `notes` field (`constraints`, `platform`, `gotchas`, `performance`, `behavioral`)
- Fall back to snippet_examples (path in `snippetFile`) only when notes are insufficient or status is `"auto"`/`"unfinished"`

### Key catalog fields

| Field         | Purpose                                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`          | FileMaker internal step ID — use in `<Step id="X">`                                                                                          |
| `selfClosing` | `true` → `<Step ... />`, `false` → `<Step ...>...</Step>`                                                                                    |
| `params[]`    | Full parameter spec: `xmlElement`, `type`, `hrLabel`, `wrapperElement`, `parentElement`, `xmlAttr`, `required`, `defaultValue`, `enumValues` |
| `hrSignature` | Human-readable parameter format for HR output                                                                                                |
| `blockPair`   | Matching step partners and role (`open`/`middle`/`close`)                                                                                    |
| `notes`       | Behavioral context sub-keys                                                                                                                  |
| `snippetFile` | Path to archival snippet_examples file                                                                                                       |
| `status`      | `"complete"` / `"auto"` / `"unfinished"`                                                                                                     |

### Param types → XML emission

| Type           | XML pattern                                                                          |
| -------------- | ------------------------------------------------------------------------------------ |
| `boolean`      | `<Element xmlAttr="True\|False"/>` — check `enumValues` for HR labels                |
| `enum`         | `<Element xmlAttr="value">` or `<Element>value</Element>`                            |
| `calculation`  | `<Calculation><![CDATA[expression]]></Calculation>`                                  |
| `namedCalc`    | `<WrapperElement><Calculation><![CDATA[expression]]></Calculation></WrapperElement>` |
| `text`         | `<Element>literal text</Element>`                                                    |
| `field`        | `<Field table="TO" id="N" name="FieldName"/>` — resolve from CONTEXT.json            |
| `script`       | `<Script id="N" name="ScriptName"/>` — resolve from CONTEXT.json                     |
| `layout`       | Layout reference — resolve from CONTEXT.json                                         |
| `findRequests` | See `agent/catalogs/find-requests.md`                                                |
| `flagElement`  | Empty element presence = on, absence = off                                           |

### HR format generation

- Look up the step by name, use the `hrSignature` field for the parameter format
- If `hrSignature` is null, fall back to reading the archival snippet_examples file

## Function catalog

`agent/catalogs/function-catalog.json` is the canonical reference for all 358 FileMaker calculation functions. **Never read the full file**. Always grep for the specific function:

```bash
grep -i '"name": "FunctionName"' agent/catalogs/function-catalog.json -A 1
```

**When to use:**
- Before writing any calculation expression — verify the function name exists and use the exact prototype from the catalog
- When unsure whether a function exists in FileMaker — the catalog is the authoritative list; if it is not here, do not use it
- To get the correct parameter signature: the `prototype` field shows the exact call syntax

**Do NOT invent function names.** If a function is not in the catalog, use a different approach or ask. Invented function names silently fail in FileMaker calculations.

# Clipboard

FileMaker objects are transferred via the macOS clipboard using proprietary binary descriptor classes — **not** plain text. Never use `pbpaste` or `pbcopy`; they corrupt multi-byte UTF-8 characters.

```bash
# Read FM objects from clipboard → save as XML
python3 agent/scripts/clipboard.py read agent/sandbox/output.xml

# Write XML file → clipboard (ready to paste into FileMaker)
python3 agent/scripts/clipboard.py write agent/sandbox/myscript.xml
```

The write command auto-detects the correct clipboard class from the XML content. For full technical details, see `agent/docs/CLIPBOARD.md`.

## MBS Plugin clipboard (alternative)

When the MBS FileMaker Plugin is available, the developer may transfer XML to FileMaker using MBS clipboard functions instead of `clipboard.py`. In this case, the AI should **NOT** run the `clipboard.py write` step automatically. The workflow becomes:

1. Generate and validate the script in `agent/sandbox/`
2. Inform the user that the file is ready in `agent/sandbox/<filename>`
3. The user handles the clipboard transfer via MBS or other means

The AI should only run `clipboard.py write` when the user explicitly requests it.

# Custom functions

FileMaker solutions may contain custom functions. These are referenced by name in calculations (CDATA text) and do **not** require IDs in fmxmlsnippet output. The AI must know which custom functions exist so it uses them rather than inventing alternatives.

Custom functions fall into three categories:

1. **Constants** — return a fixed value (e.g. `CardWindowHeight` returns `600`). Always use the custom function name; do NOT substitute a literal number.
2. **Functional code** — general-purpose utility logic with no field references (e.g. `FormatPhone ( phoneNumber )`). Safe to call from any context.
3. **Solution-specific code** — contain references to fields or table occurrences. Before using one, verify the script will be running on a layout whose base TO supports the referenced fields.

When CONTEXT.json includes a `custom_functions` section, prefer it. Otherwise, check:

- `xml_parsed/custom_functions_sanitized/` — human-readable calculation text
- `xml_parsed/custom_function_calcs/` — XML calculation definitions

# Custom menus

Custom menus are a distinct object type from scripts with a different clipboard format and XML wrapper. **Before creating or modifying any custom menu XML, use the `menu-lookup` skill** to extract the real UUIDs. Without these, FileMaker silently ignores the paste. Full details in `agent/docs/CUSTOM_MENUS.md`.

# Library

The `agent/library` folder is a curated collection of reusable fmxmlsnippet code. Use the `library-lookup` skill to access the manifest.

**Proactively** — before writing significant logic, scan the manifest for keyword matches. If found, adapt the library code rather than writing from scratch.

**Integration rules:**

- Extract inner `<Step>` elements only (not the `<Script>` wrapper) unless specifically requested
- Replace placeholder references with real values from CONTEXT.json
- Do not remove structural or purpose comments embedded in library code

# References

- **Coding conventions**: `agent/docs/CODING_CONVENTIONS.md` — variable naming, Let() formatting, operator spacing, boolean values, control structure style
- **Knowledge base**: `agent/docs/knowledge/MANIFEST.md` — behavioral intelligence about FileMaker nuances and gotchas
- **Debugging**: Use the `fm-debug` skill when a script's behavior cannot be diagnosed from source code alone. Details in `agent/docs/AGENTIC_DEBUG.md`
- **Function reference**: `agent/docs/filemaker/functions/` — official FM function docs (not guaranteed present). Validate function names against this folder when writing calculations. Do not invent function names.
- **Schema guidance**: `agent/docs/SCHEMA_GUIDANCE.md` — complete param type → XML mapping reference
- **Script format converters**: `agent/docs/CONVERTERS.md` — catalogue of every converter between FileMaker script formats (SaXML, HR, fmxmlsnippet) and which tool handles each conversion (e.g. `fm_xml_to_snippet.py`, `snippet_to_hr.py`)
- **Documentation conventions**: When writing docs, use generic placeholder names (`SolutionApp`, `SolutionData`) instead of real solution names. Exception: when the context is explicitly about a specific solution.
- **Sandboxed environments**: `agent/docs/SANDBOXED_ENVIRONMENT.md` — setup and operation guide for agents running in sandboxed, containerized, or virtualized environments (Codex, Claude Code, Docker, etc.). Read this if you detect you are not running natively on macOS.

# Taiko Solutions conventions (override)

`agent/docs/taiko/CODING_CONVENTIONS.md` contains Taiko-specific conventions that **OVERRIDE** the base conventions above. Read this file FIRST — it takes priority. For anything not defined in the Taiko conventions, fall back to the base `agent/docs/CODING_CONVENTIONS.md`.

Key overrides: PascalCase variables (`$ClienteID` not `$invoiceTotal`), comments in Spanish, `Insert Calculated Result` preferred over `Set Variable`, script naming with `.Controller` suffix, three-layer architecture naming.

# Propagación de reglas y actualizaciones (Taiko)

Modelo de **dos niveles**. La dirección importa:

```
  petrowsky/agentic-fm            (origen open source)
        ▲  PRs selectivos   │  git pull main → merge a taiko
        │  (SOLO repo base)  ▼
  Taiko-Solutions/agentic-fm · rama taiko   (base del equipo)
        ▲  mejoras suben     │  git pull taiko → merge a la rama del proyecto
        │                    ▼
  Repo de proyecto cliente         (consume taiko)
```

**Reglas:**

1. **En un repo de proyecto cliente, el flujo hacia petrowsky NO aplica.** La única fuente de actualizaciones es la **rama `taiko`** del repo base (`git pull <remoto-taiko> taiko` → merge a la rama del proyecto). No hagas el chequeo de "agentic-fm update available" contra `origin/main`, no `git pull --ff-only` de main, y **no propongas PRs a petrowsky**. Petrowsky lo gestiona **exclusivamente** el repo base Taiko.
2. **Las mejoras suben a `taiko`.** Si en un proyecto cliente detectas una mejora en la **capa de herramientas/reglas** (knowledge, convenciones, custom functions, utilidades de `agent/scripts/`, templates, snippet_examples, library), **regístrala para que suba a la rama `taiko`** — nunca directa a petrowsky, y **nunca con datos de cliente**. Mecanismo y qué NUNCA sube: `agent/docs/taiko/UPSTREAM_IMPROVEMENTS.md` (log en `agent/UPSTREAM_PROPOSALS.md`; el mantenedor del repo base lo aplica a `taiko`).
3. **Petrowsky solo desde el repo base.** Traer novedades de petrowsky (`git pull main` → merge a `taiko`) y proponer PRs a petrowsky son operaciones **exclusivas del repo base Taiko**, jamás de un proyecto cliente.

# Ejecución local por defecto (Taiko)

**Por defecto, todo agentic-fm corre en local.** El desarrollador trabaja con el archivo abierto en **FileMaker Pro en su Mac**; el companion server escucha en `127.0.0.1:8765` y todas las llamadas (Explode XML, Push Context, deploy, clipboard, debug) van por `localhost`. **FileMaker Server no interviene** y no necesita alcanzar el companion.

**La ruta FileMaker Server → companion es opt-in.** El modo server-side/headless (automatización disparada por OData contra la solución alojada, companion en `0.0.0.0`, un FMS remoto alcanzando el equipo del desarrollador) se activa **solo bajo petición directa del desarrollador**. Mientras no lo pida explícitamente:

- Asume **ejecución local** (`localhost`, FM Pro abierto en el Mac). No la propongas, no preguntes por ella, no la asumas.
- No sugieras cambiar el bind del companion a `0.0.0.0` ni configurar acceso remoto desde FileMaker Server.

Si el equipo cambia de política, se cambia **esta regla en el repo** — no se decide por conversación.

# Taiko Solutions knowledge base

`agent/docs/taiko/knowledge/` contains Taiko-specific architectural patterns and development decisions. These define how Taiko builds FileMaker solutions — error handling (Clew pattern), three-layer architecture, transactional editing, and logging.

Before writing a script, scan **both** manifests for keyword matches against the current task:

1. `agent/docs/taiko/knowledge/MANIFEST.md` — Taiko patterns (check first)
2. `agent/docs/knowledge/MANIFEST.md` — general FileMaker knowledge

If any entry matches, read the corresponding document and apply its insights during script composition.

## Taiko script templates

`agent/docs/taiko/templates/` contains human-readable script templates in `scripts_sanitized` format. Use these as structural references when composing Taiko scripts:

- `clew-simple.md` — traditional Clew pattern (read, query, navigation)
- `clew-transactional.md` — Utility Manager + Initialize Shadow + Transactional Controller

Read the appropriate template before generating a new script to ensure the correct structure and conventions are applied.

# ProofKit & acceso a FileMaker (Taiko)

Taiko toca FileMaker por **tres vías** (mapa canónico: `agent/docs/taiko/fm-access.md`):

- **Vía 1 · ProofKit MCP** — ver en vivo (SQL, metadata, valores, ERD). Capa de frescura sobre el explode/CONTEXT.json **y herramienta de pleno derecho por sí sola** — exploración de datos en chat, verificación puntual durante autoría, comprobación post-deploy, debugging — exista o no una interfaz web en la tarea. Detalle: `agent/docs/taiko/proofkit/mcp-connector.md` (§ *Vertiente standalone*).
- **Vía 2 · OData** — hacer/automatizar (AGFMScriptBridge; skills `schema-build`/`data-migrate`/`data-seed`).
- **Vía 3 · ProofKit Web Viewer** — construir interfaces web. **Motor web por defecto** de Taiko. Detalle: `agent/docs/taiko/proofkit/webviewer-build.md`.

**Reglas de operación:**

1. **Gating.** Antes de cualquier herramienta ProofKit (Vías 1 y 3), llama a `connectedFiles`. Si devuelve `[]` o falla, cae al flujo estático (explode, CONTEXT.json, OData) **sin bloquear**. agentic-fm nunca depende de ProofKit para funcionar.
2. **Estructura: manda el explode.** Estructura amplia/completa → explode/sanitized (`agent/xml_parsed/`, `context/*.index`), sin timeout. ProofKit MCP solo para preguntas **puntuales y en vivo** — nunca volcado masivo (timeout en soluciones grandes, p. ej. Bendita).
3. **Reparto de autoría.** agentic-fm autora scripts/cálculos/esquema (fmxmlsnippet/OData); ProofKit v2 **no** edita scripts/esquema, solo construye UI web y lee/escribe datos (Data API). Complementarios.
4. **Interfaces web: proactivo con guardarraíles.** Cuando una tarea encaje con una UI web (listados, dashboards, interacciones ricas), **propón** una interfaz ProofKit — mencionando los guardarraíles (`agent/docs/taiko/proofkit/gotchas.md`). Motor por defecto ProofKit; el skill `webviewer-build` solo como excepción (HTML trivial o sin conexión ProofKit). **Al scaffoldear, copia `agent/docs/taiko/proofkit/CLAUDE-webapp.md` como `CLAUDE.md` del proyecto web**: las sesiones de UI cargan solo las reglas web (ligeras), sin el stack fmxmlsnippet del repo padre.
5. **Metodología combinada.** El flujo unificado agentic-fm + Superpowers + ProofKit está en `agent/docs/taiko/knowledge/combined-workflow.md` (indexado en el MANIFEST, escaneable por keywords).

El servidor MCP `proofkit-mcp` viaja con la rama vía `.mcp.json` (comando `proofkit-mcp`, resuelto por PATH). Prerequisito por desarrollador: app ProofKit instalada + plugin cargado en el archivo + script *"Connect to MCP"* corrido en la sesión.

# Patrones upstream pendientes de validación práctica

La siguiente tabla lista patrones descubiertos en knowledge articles upstream que **aún no se han formalizado** en `agent/docs/taiko/knowledge/`. Antes de generar código, comprobar si la tarea actual hace match con algún **trigger** de la tabla:

- **Si hay match**: sugerir al desarrollador evaluar el patrón como experimento, explicando qué aporta y qué riesgos tiene. **Nunca aplicar silenciosamente.**
- **Si el desarrollador confirma**: aplicar, medir impacto en el caso concreto, y documentar aprendizaje.
- **Tras validación exitosa**: mover el patrón a `agent/docs/taiko/knowledge/<nombre>.md` adaptado al estilo Taiko (PascalCase, comentarios en español, integración con Clew) y **retirarlo de esta tabla**.

La tabla representa un **backlog de adopción** — está vacía cuando no hay nada pendiente.

| Patrón | Triggers (contextos donde tiene sentido) | Doc upstream | Notas |
|---|---|---|---|

# Metodología de desarrollo — Superpowers (Taiko)

> Esta sección gobierna CÓMO se aborda el trabajo. Las convenciones de código Taiko (`agent/docs/taiko/CODING_CONVENTIONS.md`) y el resto de este CLAUDE.md siguen mandando sobre el QUÉ y el formato del XML. Superpowers aporta el proceso; aquí se define cómo se adapta a FileMaker. Jerarquía: instrucciones de Marco > este contrato > skills de Superpowers > comportamiento por defecto.

## Cuándo aplica (umbral por alcance estructural)

Antes de empezar, clasifica la tarea:

| PROCESO COMPLETO (brainstorm → plan → casos → review) | DIRECTO (sin proceso) |
|---|---|
| Toca **≥2 scripts o custom functions** | 1 script/CF aislado |
| **Cambia el esquema** (tablas, campos) | Bugfix puntual |
| Crea un **módulo o funcionalidad nueva** | Refactor cosmético / consulta |

Si dudas, pregunta. Marco puede forzar el proceso completo en cualquier tarea ("pásalo por proceso completo"), aunque sea pequeña.

## Qué skills de Superpowers se usan

| Skill | Uso en FileMaker |
|---|---|
| `brainstorming` | Sí, en tareas de alcance estructural. Para auditar una solución existente antes de diseñar, usa el skill `Solution-Analysis`. |
| `writing-plans` | Sí. Plan de las piezas a crear (CF, scripts Controller/Transaccional, triggers) y su orden. |
| `systematic-debugging` | Sí, ante cualquier fallo. **La técnica FM es el skill `Skill-Debug`** (instrumentar → companion `/debug` → `output.json`). El proceso de 4 fases lo pone Superpowers; la herramienta la pone Skill-Debug. |
| `requesting-code-review` | Sí, antes de dar por buena una pieza: revisa el XML contra el spec y contra `CODING_CONVENTIONS.md`. |

**NO se usan en FileMaker:** `test-driven-development` (red-green literal — ver abajo), `using-git-worktrees`, `subagent-driven-development`.

## Verificación (sustituye al TDD red-green)

FileMaker no tiene tests unitarios. **No se aplica el ciclo red-green ni la regla de "borrar el código escrito antes del test".** En su lugar, en toda tarea de alcance estructural:

1. **Antes de generar el script**, escribe los **casos de aceptación**: entrada concreta → salida esperada. Ej.: `ValidarNIF("12345678Z") → válido`; `…("12345678A") → inválido`; `…("") → inválido`.
2. Genera el script siguiendo las convenciones Taiko.
3. Impórtalo en FileMaker y **verifica esos casos**. Apóyate en el skill `script-test` para generar el script de verificación con esos inputs/outputs.
4. Un caso que falla = no está hecho. Corrige y vuelve a verificar.

## Dónde viven los artefactos

El proceso vive en el repo (se propaga). Los artefactos de cada solución viven en el **vault** de Obsidian — nunca se versionan en el repo de cliente:

| Artefacto | Ubicación en el vault |
|---|---|
| Spec / diseño | `Proyectos/.../[proyecto]/00-Especificacion.md` |
| Decisiones | `01-Decisiones-Tomadas.md` |
| Casos de aceptación | dentro del spec |
| Registro al cerrar | `Changelog-Agentic.md` |

## Detalle

El flujo completo paso a paso está en `agent/docs/taiko/knowledge/superpowers-workflow.md` (escaneable por keywords: feature, diseño, plan, módulo, refactor).

Cuando la tarea combine autoría FileMaker, consulta en vivo y/o interfaz web, el flujo unificado (agentic-fm + Superpowers + ProofKit) está en `agent/docs/taiko/knowledge/combined-workflow.md`. Ver también la sección "ProofKit & acceso a FileMaker (Taiko)".

# FileMaker and MBS documentation

## Dash + MCP (preferred)

When the Dash MCP server is available, use it to look up FileMaker and MBS Plugin documentation directly. This is faster and more accurate than the bundled docs.

- Use `search_documentation` with docset identifiers for FileMaker and MBS to find function syntax, script step options, and error codes.
- Use `load_documentation_page` to read the full documentation page for a specific topic.

When Dash MCP is available, there is no need to run `agent/docs/filemaker/fetch_docs.py` or to consult the local `agent/docs/filemaker/` directory.

## Claris official LLM docs (online complement)

Claris publishes its full help knowledge base as LLM-ready markdown, updated continuously:

- `https://help.claris.com/llms.txt` — index of topics with links. Small; fetch this first to locate the right page.
- `https://help.claris.com/llms-full.txt` — the entire help KB inlined (~1.9 MB). Fetch with a targeted query, never the whole file.

Retrieve these with `WebFetch`. Use them as a **complement** to Dash, not a replacement:

- **Dash stays primary** for fast, offline, structured lookup of function syntax, script step options, and error codes.
- **Reach for the Claris source** when Dash lacks a topic, when you need conceptual or behavioral documentation, or for the newest FileMaker 2025/2026 features whose Dash docsets may be stale or missing — it is the official, current source.
- Network-dependent: skip when offline and fall back to bundled docs below.

## Bundled docs (fallback)

If Dash MCP is not available, the project can generate local documentation files using `agent/docs/filemaker/fetch_docs.py`. See the README for details. These files are gitignored and must be generated locally.

# Change log (Obsidian)

When an Obsidian MCP server is available, the AI should log significant completed tasks to keep the team informed.

After the user confirms a task is complete (script created, refactored, bug fixed), append an entry to the solution's changelog in Obsidian:

**Path:** `Proyectos/Taiko/<ProjectName>/Changelog-Agentic.md`

**Entry format:**

```markdown
## YYYY-MM-DD — Brief summary

- **Script**: name of the script created/modified
- **Type**: Nuevo | Modificación | Refactoring | Bugfix
- **Description**: 1-2 sentences describing what was done and why
- **Files**: list of files in sandbox/ generated
```

If the file does not exist, create it with a `# Changelog Agentic-FM` header.

Only log when the user explicitly confirms the task is done. Do not log exploratory work, failed attempts, or intermediate steps.

# Constraints

- XML within _xml_parsed/_ is NEVER modified — only referenced.
- When an existing script in _xml_parsed/_ is referenced for modification, copy it into _sandbox/_.
- XML within _snippet_examples/_ is NEVER modified. Prompt the user if changes seem needed.
- Index files in _context/_ are NEVER manually edited — regenerated by `fmcontext.sh`.
- _CONTEXT.json_ is generated by FileMaker — never manually created or modified by AI.
- _step-catalog-en.json_ is maintained via `agent/catalogs/UPDATING_CATALOGS.md`. See `agent/docs/SCHEMA_GUIDANCE.md` for the param type → XML mapping reference.
