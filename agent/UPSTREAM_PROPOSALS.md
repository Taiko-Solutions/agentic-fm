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
