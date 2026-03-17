# Webviewer Output Channel — Build Status

Session-persistent notes on what was built, what remains, every quirk discovered, and where to resume. Read this at the start of any session continuing webviewer output channel work.

See `webviewer/WEBVIEWER_INTEGRATION.md` for the full webviewer architecture reference.

---

## Architecture overview

The webviewer is a Preact/Monaco SPA served by a **Vite dev server at port 8080** (`strictPort: true`). The Vite server includes its own middleware (`server/api.ts`) that serves a REST API — it is NOT a dumb frontend pointing at the companion server.

Two distinct servers are involved in any agent output flow:

| Server | Port | Purpose |
|---|---|---|
| **Vite dev server** (`webviewer/`) | 8080 | Serves the SPA + REST API (`/api/*`). Webviewer talks to this directly. |
| **Companion server** (`agent/scripts/companion_server.py`) | 8765 | Agent-facing HTTP server. Handles clipboard, trigger, context, explode, webviewer lifecycle. |

The companion manages Vite's lifecycle (`/webviewer/start`, `/webviewer/stop`) but does not serve the webviewer content.

### Critical constraint: SSE/WebSocket unreliable in FM WebKit

FileMaker's WebViewer object embeds a WebKit-based webview. **Vite's HMR WebSocket and `import.meta.hot` custom events are not reliable in this environment.** The existing `server/ws.ts` (file-watcher WebSocket) is unreliable inside FM for the same reason.

The reliable mechanism for pushing content to the webviewer is **HTTP polling** — the webviewer calls a Vite API endpoint on a timer. CONTEXT.json delivery already uses this pattern successfully.

This means the SSE-from-companion approach described in SKILL_INTERFACES.md is inappropriate for FM WebKit. The agent output channel should use the polling pattern instead.

### Preferred approach: polling via Vite API

Rather than the companion broadcasting to webviewer via SSE:

1. Agent calls `POST /webviewer/push` on the **companion** with `{ type, content, before? }`
2. Companion writes the payload to a file (e.g. `agent/config/.agent-output.json`)
3. Webviewer polls a **Vite** endpoint (`GET /api/agent-output`) on a short interval (~1s, active only when the agent output panel is open)
4. When the file changes, the webviewer renders the new content

This mirrors how CONTEXT.json is already delivered (file on disk → polling) and avoids the WebSocket/SSE reliability issue entirely.

### Alternative: JS bridge

FileMaker can call `window.pushContext(json)` via `Perform JavaScript in Web Viewer`. A similar `window.pushAgentOutput(payload)` global could be registered in the webviewer and triggered by an FM script. This is the most direct path but requires an FM script and a user interaction or OData trigger — less suitable for fully autonomous agent output.

---

## What was built

### Companion: Vite lifecycle management

`companion_server.py` has these endpoints — built and working:

| Endpoint | Status | Notes |
|---|---|---|
| `GET /webviewer/status` | ✅ Built | Returns `{ "running": true/false }` — checks if companion-spawned Vite process is alive |
| `POST /webviewer/start` | ✅ Built | Spawns `npm run dev` in `webviewer/` as a detached child process |
| `POST /webviewer/stop` | ✅ Built | Sends SIGTERM to the Vite process group |
| Graceful shutdown | ✅ Built | On `KeyboardInterrupt`, companion stops Vite before exiting (added in `42d1fae`) |

**Important**: `GET /webviewer/status` checks process state (did the companion spawn Vite?), not URL reachability. A Vite process may be running but not yet serving. Skills need a URL reachability check — see below.

### Webviewer: existing infrastructure

The webviewer already has substantial relevant infrastructure (from `webviewer/WEBVIEWER_INTEGRATION.md`):

- **Monaco editor** with FileMaker HR syntax highlighting, completions, and diagnostics
- **`/api/sandbox`** endpoints — read/write XML files in `agent/sandbox/` (GET list, GET file, POST file)
- **`/api/validate`** — runs `validate_snippet.py` on posted XML
- **`/api/context`** — returns CONTEXT.json; webviewer polls this for changes
- **CONTEXT.json polling** — client polls `/api/context` and detects changes via JSON hash comparison; reliable in FM WebKit
- **`window.pushContext(json)`** — JS bridge global; FM can call this directly via `Perform JavaScript in Web Viewer`
- **Autosave** — draft persistence across FM WebViewer reinitialization cycles

---

## What is not yet built

### Companion: `/webviewer/push` endpoint

`POST /webviewer/push` — accepts `{ "type": "preview"|"diff"|"result", "content": "...", "before": "..." }` and writes to `agent/config/.agent-output.json` (or similar).

- Validate `type` is a known payload type
- Write `{ type, content, before, timestamp }` to the output file
- Return `{ "success": true }`

### Companion: URL-reachability check

Distinct from process state: **is the Vite server actually serving requests?**

Simplest approach: agent does `curl -s --max-time 2 http://localhost:8080` and treats any response as available. No companion involvement needed; skills do this directly.

Add `"webviewer_url": "http://localhost:8080"` to `automation.json` so the URL is configurable.

### Vite API: `/api/agent-output` polling endpoint

A new endpoint in `server/api.ts`:

- `GET /api/agent-output` — reads `agent/config/.agent-output.json`; returns its contents or `{ "available": false }` if absent/empty
- `DELETE /api/agent-output` — clears the output file (called when the agent output panel is dismissed)

### Webviewer: "Agent output" panel

A new panel in the webviewer UI that:
- Polls `GET /api/agent-output` every ~1s when the panel is open (same pattern as CONTEXT.json polling)
- On `preview` payload: renders `content` in a read-only Monaco editor instance with FileMaker HR syntax highlighting
- On `diff` payload: renders Monaco diff editor with `before` on the left, `content` on the right; developer can edit the right pane and save via `/api/sandbox`
- On `result` payload: renders structured output (expression, result value, error context)
- Panel activates when a new output arrives; dismisses and clears on close
- Degrades gracefully when no output is pending

### `automation.json` field

Add `"webviewer_url": "http://localhost:8080"` (port 8080, not 5173 — Vite is configured with `strictPort: true` at 8080).

---

## Current status

| Feature | Status |
|---|---|
| Vite process management (`/webviewer/start`, `/webviewer/stop`) | ✅ Built |
| Process-state status check (`GET /webviewer/status`) | ✅ Built |
| Graceful Vite shutdown on companion exit | ✅ Built |
| Monaco editor with FM HR syntax highlighting | ✅ Built (webviewer) |
| CONTEXT.json polling in webviewer | ✅ Built (webviewer) |
| `webviewer_url` in `automation.json` | 🔴 Not built |
| URL-reachability check for skills | 🔴 Not built |
| Companion `/webviewer/push` endpoint (writes `.agent-output.json`) | 🔴 Not built |
| Vite `/api/agent-output` polling endpoint | 🔴 Not built |
| Webviewer "Agent output" panel | 🔴 Not built |
| `preview` payload → read-only Monaco HR display | 🔴 Not built |
| `diff` payload → Monaco diff editor | 🔴 Not built |
| `result` payload → structured output display | 🔴 Not built |
| Terminal fallback when webviewer unavailable | 🔵 Design only — no skills exist yet |

---

## Test plan

Tests are ordered from infrastructure up.

### 1. Vite reachability check

```bash
# Vite running
curl -s --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8080
# Expected: 200

# Vite stopped
curl -s --max-time 2 -o /dev/null -w "%{http_code}" http://localhost:8080
# Expected: 000 (connection refused)
```

Confirm skill routing logic correctly detects availability in both states.

### 2. Companion `/webviewer/push` writes output file

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"type": "preview", "content": "Set Variable [ $x[1] ; 42 ]"}' \
  http://local.hub:8765/webviewer/push

cat agent/config/.agent-output.json
```

**Expected**: file written with `{ "type": "preview", "content": "...", "timestamp": "..." }`.

### 3. Vite `/api/agent-output` returns the payload

```bash
curl -s http://localhost:8080/api/agent-output
```

**Expected**: returns the same JSON written by step 2.

### 4. Webviewer Agent output panel — `preview` end-to-end

Run step 2. Open the webviewer in FM (or a browser). Confirm:
- Agent output panel appears
- Monaco renders `Set Variable [ $x[1] ; 42 ]` with FileMaker syntax highlighting
- Closing the panel clears the output file

### 5. `diff` payload end-to-end

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"type": "diff", "before": "Set Variable [ $x[1] ; 1 ]", "content": "Set Variable [ $x[1] ; 42 ]"}' \
  http://local.hub:8765/webviewer/push
```

**Expected**: Monaco diff editor opens with old on left, new on right. Change highlighted. Developer can edit right pane.

### 6. Fallback when Vite is stopped

Stop the Vite server. Trigger a skill that produces HR output. Confirm:
- Terminal output is produced normally
- No error is raised
- No attempt to write to `.agent-output.json`

### 7. FM WebKit polling reliability

Open the webviewer inside a FileMaker WebViewer object (not a browser). Run step 2. Confirm the agent output panel appears within ~2s. This validates that polling survives FM WebKit's WebSocket/SSE unreliability.

---

## Key files

| File | Purpose |
|---|---|
| `agent/scripts/companion_server.py` | Companion server — add `/webviewer/push` here |
| `agent/config/automation.json` | Add `webviewer_url: "http://localhost:8080"` |
| `webviewer/server/api.ts` | Vite middleware — add `/api/agent-output` endpoint here |
| `webviewer/src/App.tsx` | Root component — add Agent output panel here |
| `webviewer/WEBVIEWER_INTEGRATION.md` | Full webviewer architecture reference |
| `plans/SKILL_INTERFACES.md` | Interface contract (note: SSE references need updating — use polling instead) |

---

## Open items

- **SKILL_INTERFACES.md** references SSE from companion to webviewer. This should be updated to describe the polling approach once the implementation is confirmed.
- **`window.pushAgentOutput` JS bridge**: worth registering as an alternative fast path for the FM WebViewer case — FM could call it directly from an agentic-fm script to push preview content without polling latency.

---

## What to do next

### 1. Add `webviewer_url` to `automation.json`

```json
"webviewer_url": "http://localhost:8080"
```

### 2. Add `/webviewer/push` to companion server

In `companion_server.py`, route `POST /webviewer/push` to a new `_handle_webviewer_push` handler:
- Reads `{ type, content, before? }` from body
- Writes to `agent/config/.agent-output.json`
- Returns `{ "success": true }`

### 3. Add `/api/agent-output` to Vite server

In `webviewer/server/api.ts`:
- `GET /api/agent-output` — reads `.agent-output.json`, returns contents or `{ "available": false }`
- `DELETE /api/agent-output` — removes the file

### 4. Build Agent output panel in webviewer

- Poll `/api/agent-output` on ~1s interval (active only when panel is open or pending)
- Render `preview` / `diff` / `result` payload types
- Run full test plan (tests 1–7)
