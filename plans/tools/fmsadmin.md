# fmsadmin

> Status: **exploration** | Created: 2026-03-20

## Overview

`fmsadmin` is the command-line administration tool for FileMaker Server. It manages the server itself — starting/stopping services, hosting/closing files, managing clients, running backups, controlling schedules, and handling certificates. Unlike `FMDeveloperTool` (which operates on `.fmp12` files), `fmsadmin` operates on the **server process**.

## Where It Runs

This tool is installed on every FileMaker Server at:
```
/opt/FileMaker/FileMaker Server/Database Server/bin/fmsadmin
```

**This tool is NOT in the agent container.** It only exists on the FMS machine and must be executed there. The agent triggers it through:

1. **FM script via OData** — an FM script calls `fmsadmin` via MBS plugin's `Shell.Execute`, triggered by the agent through `AGFMScriptBridge`
2. **Direct SSH** (if configured) — the agent could SSH to the FMS machine and run commands directly
3. **FMS Admin API** — for some operations, the Admin API (REST) is an alternative to the CLI

## Authentication

All `fmsadmin` commands require server admin credentials:

```bash
fmsadmin <command> [-u <username>] [-p <password>] [-y]
```

| Flag | Purpose |
|---|---|
| `-u <username>` | Server admin username |
| `-p <password>` | Server admin password |
| `-y` | Auto-confirm prompts (required for non-interactive use) |

For automated use, credentials can be saved:
```bash
fmsadmin <command> --savedbcredentials
```

---

## Command Reference

### File Management

#### LIST FILES
Lists all hosted databases with their status.

```bash
fmsadmin list files [-u admin -p password]
```

**Why this matters:** The agent can query which files are currently hosted, their status (normal, closed, paused), and their paths. Essential for knowing what's available before running operations.

#### OPEN
Opens (hosts) a database file, making it available to clients.

```bash
fmsadmin open "MyFile.fmp12" [-u admin -p password -y]
# or open with encryption key
fmsadmin open "MyFile.fmp12" --key "encryption_key" [-u admin -p password -y]
```

**Why this matters:** After a migration or modification, the agent can host the resulting file without developer intervention.

#### CLOSE
Closes a hosted database, disconnecting all clients.

```bash
# Close a specific file
fmsadmin close "MyFile.fmp12" [-u admin -p password -y]

# Close all files
fmsadmin close [-u admin -p password -y]

# Close with a message to connected clients
fmsadmin close "MyFile.fmp12" -m "Server maintenance in progress" [-u admin -p password -y]
```

**Why this matters:** Files must be closed before migration (`FMDataMigration`) or certain `FMDeveloperTool` operations. The agent needs to close files as part of the deployment pipeline.

#### PAUSE / RESUME
Temporarily suspends database access without fully closing.

```bash
fmsadmin pause "MyFile.fmp12" [-u admin -p password -y]
fmsadmin resume "MyFile.fmp12" [-u admin -p password -y]
```

**Use case:** Brief maintenance operations where a full close/reopen cycle is unnecessary.

#### REMOVE
Removes a database from hosting (stops serving it, but doesn't delete the file).

```bash
fmsadmin remove "MyFile.fmp12" [-u admin -p password -y]
```

#### VERIFY
Closes and verifies database consistency (similar to `FMDeveloperTool --checkConsistency` but runs on hosted files through the server).

```bash
fmsadmin verify "MyFile.fmp12" [-u admin -p password -y]
```

---

### Client Management

#### LIST CLIENTS
Lists all connected clients with their details.

```bash
fmsadmin list clients [-u admin -p password]
```

Returns: client ID, username, machine name, IP address, connection type, connected file(s).

**Why this matters:** Before closing a file for migration, the agent should check for connected clients and warn the developer.

#### DISCONNECT
Disconnects a specific client by ID.

```bash
fmsadmin disconnect <client_id> [-m "message"] [-u admin -p password -y]
```

#### SEND
Sends a message to connected clients.

```bash
# Message all clients
fmsadmin send -m "Server maintenance starting in 5 minutes" [-u admin -p password -y]

# Message clients of a specific file
fmsadmin send -m "This file will be closed shortly" -c <client_id> [-u admin -p password -y]
```

**Why this matters:** Before taking a file offline for migration, the agent can notify connected users.

---

### Backup

#### BACKUP
Creates a backup of hosted databases.

```bash
# Backup a specific file
fmsadmin backup "MyFile.fmp12" [-d <destination_path>] [-u admin -p password -y]

# Backup all files
fmsadmin backup [-d <destination_path>] [-u admin -p password -y]
```

**Why this matters:** The agent should trigger a backup before any destructive operation (migration, schema change, recovery). This is a safety gate in the deployment pipeline.

---

### Server Process Control

#### START / STOP / RESTART

```bash
# Database Server
fmsadmin start server [-u admin -p password -y]
fmsadmin stop server [-u admin -p password -y]
fmsadmin restart server [-u admin -p password -y]

# FileMaker Script Engine (FMSE)
fmsadmin start fmse [-u admin -p password -y]
fmsadmin stop fmse [-u admin -p password -y]
fmsadmin restart fmse [-u admin -p password -y]

# Web Publishing Engine
fmsadmin start wpe [-u admin -p password -y]
fmsadmin stop wpe [-u admin -p password -y]
fmsadmin restart wpe [-u admin -p password -y]

# Admin Server (Admin Console)
fmsadmin start adminserver [-u admin -p password -y]
fmsadmin stop adminserver [-u admin -p password -y]

# XDBC Listener (ODBC/JDBC)
fmsadmin start xdbc [-u admin -p password -y]
fmsadmin stop xdbc [-u admin -p password -y]
```

**Why this matters:** Some operations require specific services to be running or stopped:
- OData requires the Database Server and Data API
- Server-side scripts require FMSE
- XDBC must be running for ODBC/JDBC access

#### STATUS
Gets the status of a client or file.

```bash
fmsadmin status file "MyFile.fmp12" [-u admin -p password]
fmsadmin status client <client_id> [-u admin -p password]
```

---

### Schedules

#### LIST SCHEDULES
Lists all configured schedules with their IDs.

```bash
fmsadmin list schedules [-u admin -p password]
```

#### RUN
Manually triggers a schedule by ID.

```bash
fmsadmin run schedule <schedule_id> [-u admin -p password -y]
```

**Why this matters:** If backup schedules or maintenance scripts are configured as FMS schedules, the agent can trigger them on demand.

#### ENABLE / DISABLE
Enables or disables a schedule.

```bash
fmsadmin enable schedule <schedule_id> [-u admin -p password -y]
fmsadmin disable schedule <schedule_id> [-u admin -p password -y]
```

---

### Security

#### CERTIFICATE
Manages SSL certificates.

```bash
fmsadmin certificate create [-u admin -p password -y]
fmsadmin certificate import <cert_file> [-u admin -p password -y]
```

#### RESETPW
Resets the admin console password.

```bash
fmsadmin resetpw [-u admin -p password -y]
```

#### CLEARKEY
Removes the saved encryption password for a database.

```bash
fmsadmin clearkey "MyFile.fmp12" [-u admin -p password -y]
```

---

### Plugins

#### LIST PLUGINS
Lists installed server-side plugins.

```bash
fmsadmin list plugins [-u admin -p password]
```

**Why this matters:** The agent can verify that required plugins (MBS, BaseElements) are installed before attempting operations that depend on them.

---

### Other

#### AUTORESTART
Gets or sets auto-restart behavior for the Admin Server.

```bash
fmsadmin autorestart adminserver [-u admin -p password]
```

---

## Integration with agentic-fm

### The Deployment Pipeline

`fmsadmin` commands fill critical gaps in the end-to-end deployment pipeline:

```
1. fmsadmin backup "Production.fmp12"          ← safety backup
2. fmsadmin send -m "Maintenance in 5 min"     ← notify users
3. fmsadmin list clients                        ← check who's connected
4. fmsadmin close "Production.fmp12" -y         ← take offline
5. FMDataMigration -src_path ... -clone_path .. ← migrate data
6. FMDeveloperTool --checkConsistency ...        ← validate result
7. fmsadmin open "Migrated.fmp12"               ← host new version
8. fmsadmin send -m "Maintenance complete"      ← notify users
```

Steps 1-4 and 7-8 require `fmsadmin`. Without it, the pipeline has manual gaps.

### Server-Side Execution

`fmsadmin` runs on the FMS machine. In the Docker architecture:

```
Agent Container                    FMS Container
┌──────────────┐                  ┌──────────────────────┐
│              │   OData POST     │                      │
│  Agent       │ ──────────────→  │  AGFMScriptBridge    │
│              │                  │       │               │
│              │                  │       ▼               │
│              │                  │  AGFMServerAdmin      │
│              │                  │  (FM script wrapper)  │
│              │                  │       │               │
│              │                  │       ▼               │
│              │                  │  MBS Shell.Execute    │
│              │                  │  → fmsadmin close ... │
│              │   JSON result    │       │               │
│              │ ←────────────── │       ▼               │
│              │                  │  Return result        │
└──────────────┘                  └──────────────────────┘
```

### Proposed FM Script: `AGFMServerAdmin`

A new agentic-fm script that wraps `fmsadmin` commands:

**Parameter format (JSON):**
```json
{
  "command": "close",
  "target": "MyFile.fmp12",
  "options": {
    "message": "Maintenance in progress",
    "force": true
  }
}
```

**Supported commands:**
- `list_files` — returns hosted file list as JSON
- `list_clients` — returns connected client list as JSON
- `close` — closes a file (with optional message)
- `open` — opens a file (with optional encryption key)
- `pause` / `resume` — suspends/resumes file access
- `backup` — triggers backup of a file
- `send` — sends message to clients
- `status` — returns file or client status
- `verify` — closes and verifies a file
- `list_plugins` — returns installed plugins

The script reads server admin credentials from a secure storage mechanism (not passed as parameters) and constructs the `fmsadmin` shell command via MBS.

### Alternative: FMS Admin API

FileMaker Server also exposes a REST-based Admin API. For some operations, this may be simpler than wrapping `fmsadmin` in FM scripts:

```bash
# Authenticate
curl -X POST https://fms.example.com/fmi/admin/api/v2/user/auth \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"password"}'

# List databases
curl https://fms.example.com/fmi/admin/api/v2/databases \
    -H "Authorization: Bearer <token>"

# Close a database
curl -X PATCH https://fms.example.com/fmi/admin/api/v2/databases/1 \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"status":"CLOSED","messageText":"Maintenance"}'
```

The Admin API could be called directly from the agent container (or companion server) without needing FM scripts as intermediaries. This is worth exploring as a potentially simpler integration path for server administration commands.

---

## Credential Management

`fmsadmin` credentials are the FMS server admin account — separate from file-level Full Access accounts. Proposed `automation.json` extension:

```json
{
  "solutions": { ... },
  "fms_admin": {
    "host": "fms.example.com",
    "username": "admin",
    "password": "serverpassword",
    "admin_api_url": "https://fms.example.com/fmi/admin/api/v2"
  }
}
```

---

## Potential Skills

| Skill | How fmsadmin Fits |
|---|---|
| `schema-migrate` | `close` before migration, `open` after migration, `backup` as safety gate, `send` to notify users |
| `file-ops` | `verify` for consistency checks, `open`/`close` for hosting control, `backup` on demand |
| `solution-audit` | `list files` for inventory, `list clients` for usage analysis, `status` for health monitoring |
| `solution-export` | `pause` to ensure consistent export, `resume` after |

---

## Next Steps

1. **Verify fmsadmin access from FM scripts** — test MBS Shell.Execute with a simple `fmsadmin list files` command
2. **Evaluate Admin API vs CLI** — determine which path is simpler for the agent to use directly
3. **Build `AGFMServerAdmin` FM script** — or decide to use Admin API from the companion server instead
4. **Document credential flow** — how server admin credentials flow securely from `automation.json` to the execution context
5. **Test the full deployment pipeline** — end-to-end: backup → notify → close → migrate → verify → open → notify
