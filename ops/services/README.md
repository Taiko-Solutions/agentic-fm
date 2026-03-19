# Local macOS services (Companion + Webviewer)

This folder provides an operational layer for `agentic-fm` on macOS, focused on:

- auto-start at user login (`launchd`),
- multi-repo workflow (switching active project roots),
- simple service lifecycle commands.

## What it provides

1. **Companion Server** on `127.0.0.1:8765`, managed by `launchd`.
2. **Webviewer** on Docker (`127.0.0.1:8080`), managed by `launchd`.
3. **Active repo switching** for Webviewer without rebuilding the whole setup.
4. Unified **status and diagnostics** from one command.

## Components

- `servicesctl.sh` — primary command (`install|start|stop|restart|status|use-repo|uninstall`).
- `install_launchagents.sh` / `uninstall_launchagents.sh` — LaunchAgent install/remove.
- `start_companion.sh` — Companion startup (`PATH` + `FM_XML_EXPLODER_BIN` bootstrap).
- `start_webviewer_docker.sh` — Webviewer Docker startup.
- `use_repo.sh` — sets active repo for Webviewer.
- `status.sh` — reports Companion + Webviewer + active repo status.

LaunchAgent templates:
- `launchd/com.agenticfm.companion-server.plist.template`
- `launchd/com.agenticfm.webviewer-docker.plist.template`

## Requirements

- macOS
- `launchctl`
- Docker Desktop or OrbStack
- `fm-xml-export-exploder` available (recommended at `~/bin/fm-xml-export-exploder`)

## Install and base usage

From repo root:

```bash
./ops/services/servicesctl.sh install
./ops/services/servicesctl.sh status
```

Lifecycle commands:

```bash
./ops/services/servicesctl.sh start
./ops/services/servicesctl.sh stop
./ops/services/servicesctl.sh restart
./ops/services/servicesctl.sh status
./ops/services/servicesctl.sh uninstall
```

## Multi-repo workflow (Webviewer)

Switch active Webviewer repo:

```bash
./ops/services/servicesctl.sh use-repo /path/to/agentic-fm
```

Equivalent:

```bash
./ops/services/use_repo.sh /path/to/agentic-fm
```

### Important rule

- **Companion** can serve multiple repositories (based on request `repo_path`).
- **Webviewer** runs with **one active repo at a time** (port 8080).

Persisted active repo:

```text
~/Library/Application Support/agentic-fm-services/active_repo.path
```

## Runtime and logs

LaunchAgent runtime:

```text
~/Library/Application Support/agentic-fm-services/runtime
```

Logs:

```text
~/Library/Logs/agentic-fm/services.log
~/Library/Logs/agentic-fm/companion-server.launchd.log
~/Library/Logs/agentic-fm/webviewer-docker.launchd.log
```

## Optional shell integration (`~/.zshrc`)

Not required, but helpful for daily usage.

Example optional helpers:

```bash
agenticfm_start /path/to/agentic-fm
agenticfm_use /path/to/agentic-fm
agenticfm_status
agenticfm_stop
```

> Recommendation: keep these helpers in each user's local shell config and treat them as optional convenience wrappers.

## Troubleshooting

### `Operation not permitted` when running `fmparse.sh` via Companion

This is often a macOS/TCC permission issue when the process runs under `launchd` and accesses repos under `Documents`.

Options:

1. Grant appropriate permissions (for example, Full Disk Access to the Python executable used by the LaunchAgent).
2. Run Companion manually as a temporary workaround.
3. Move repositories to a location with fewer TCC restrictions.

### `fm-xml-export-exploder is not installed or not in PATH`

- Install the binary and/or
- set `FM_XML_EXPLODER_BIN` correctly.

`start_companion.sh` already attempts:

```text
~/bin/fm-xml-export-exploder
```

## Maintenance / PR notes

- This module is macOS-oriented (`launchd` + `osascript` notifications).
- For upstream (`petrowsky/main`), keep it clearly optional and well documented.
- Avoid requiring per-user local config outside `$HOME`.
