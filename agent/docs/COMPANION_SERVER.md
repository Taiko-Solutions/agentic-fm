# Companion Server

The companion server is a lightweight HTTP server that exposes `fmparse.sh` as a local API endpoint. FileMaker calls it via the native **Insert from URL** script step, which functions as a curl-compatible HTTP client.

**Why this exists:** FileMaker has no built-in mechanism to execute arbitrary shell commands. The traditional workaround is the MBS FileMaker Plugin, which provides a `MBS("Shell.Execute"; ...)` function. The companion server replaces this dependency entirely — no third-party plugin is required. As long as the server is running on the developer's machine, FileMaker can trigger XML parsing and context generation through a simple HTTP POST.

**Windows gap:** The companion server approach is macOS-only at this time. `fmparse.sh` and `fm-xml-export-exploder` are Unix binaries. On Windows, the MBS plugin remains the supported fallback for shell execution.

---

## Starting the server

The server is a single Python file with no external dependencies beyond the standard library. Activate the virtual environment first, then start:

```bash
source .venv/bin/activate

# Default port 8765
python agent/scripts/companion_server.py

# Custom port
python agent/scripts/companion_server.py --port 9000
```

Startup log output:

```
2026-03-09T14:22:01 INFO companion_server v1.0 listening on 127.0.0.1:8765
2026-03-09T14:22:01 INFO Endpoints: GET /health  POST /explode
2026-03-09T14:22:01 INFO Press Ctrl-C to stop.
```

### Background process (Mac)

To run the server in the background without blocking the terminal:

```bash
source .venv/bin/activate
python agent/scripts/companion_server.py &
```

stdout logging will mix with your shell session. Redirect to a log file if that is disruptive:

```bash
python agent/scripts/companion_server.py > /tmp/companion_server.log 2>&1 &
```

### Auto-start with launchd (Mac)

To have the server start automatically at login, create a launchd plist. Replace the paths with your actual username and repo location:

**`~/Library/LaunchAgents/com.agentic-fm.companion-server.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic-fm.companion-server</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/yourname/agentic-fm/.venv/bin/python</string>
        <string>/Users/yourname/agentic-fm/agent/scripts/companion_server.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/yourname/agentic-fm</string>

    <key>StandardOutPath</key>
    <string>/tmp/companion_server.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/companion_server.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load it immediately without logging out:

```bash
launchctl load ~/Library/LaunchAgents/com.agentic-fm.companion-server.plist
```

Verify it is running:

```bash
launchctl list | grep agentic-fm
curl http://localhost:8765/health
```

To unload (stop and disable auto-start):

```bash
launchctl unload ~/Library/LaunchAgents/com.agentic-fm.companion-server.plist
```

---

## Endpoints

### GET /health

A lightweight liveness check. FileMaker or the developer can poll this to confirm the server is up before triggering an explode operation.

**Request:**

```
GET http://localhost:8765/health
```

No request body. No required headers.

**Response (200 OK):**

```json
{
  "status": "ok",
  "version": "1.0"
}
```

---

### POST /explode

The primary endpoint. Accepts a JSON payload describing the export to parse, invokes `fmparse.sh` as a subprocess, and returns the exit code and output so FileMaker can detect success or failure.

**Request headers:**

```
Content-Type: application/json
Content-Length: <byte length of body>
```

**Request body — JSON schema:**

| Field | Type | Required | Description |
|---|---|---|---|
| `solution_name` | string | Yes | The solution identifier. Used by `fmparse.sh` as the subfolder name under `xml_exports/` and `agent/xml_parsed/`. Must match the name used when the XML was exported. |
| `export_file_path` | string | Yes | Absolute path to the FileMaker XML export file (or directory of XML exports) on the local machine. Tilde expansion is supported (`~/...`). |
| `repo_path` | string | Yes | Absolute path to the root of the agentic-fm repository. `fmparse.sh` is resolved at `{repo_path}/fmparse.sh`. Tilde expansion is supported. |
| `exploder_bin_path` | string | No | Absolute path to the `fm-xml-export-exploder` binary, if it is not on `PATH`. Passed through to `fmparse.sh` as the `FM_XML_EXPLODER_BIN` environment variable. |

**Example request body:**

```json
{
  "solution_name": "Invoice Solution",
  "export_file_path": "/Users/yourname/Desktop/InvoiceSolution.xml",
  "repo_path": "/Users/yourname/agentic-fm",
  "exploder_bin_path": "/usr/local/bin/fm-xml-export-exploder"
}
```

**Success response (200 OK):**

Returned when `fmparse.sh` exits with code `0`.

```json
{
  "success": true,
  "exit_code": 0,
  "stdout": "==> Parsing Invoice Solution\n==> Done.\n",
  "stderr": ""
}
```

**Failure response (500):**

Returned when `fmparse.sh` exits with a non-zero code (e.g. the exploder binary is missing or the export file cannot be read).

```json
{
  "success": false,
  "exit_code": 1,
  "stdout": "==> Parsing Invoice Solution\n",
  "stderr": "ERROR: fm-xml-export-exploder: command not found\n"
}
```

**Validation error response (400):**

Returned when required fields are missing or the request body is not valid JSON.

```json
{
  "success": false,
  "exit_code": -1,
  "error": "Missing required fields: solution_name, repo_path"
}
```

**What the server actually runs:**

The server constructs and executes this command as a subprocess, with `cwd` set to `repo_path`:

```bash
{repo_path}/fmparse.sh -s "{solution_name}" "{export_file_path}"
```

If `exploder_bin_path` is provided, it is injected into the subprocess environment as `FM_XML_EXPLODER_BIN` before the command runs. `fmparse.sh` reads this variable to locate the exploder binary without requiring it to be on `PATH`.

---

## Security

The server binds exclusively to `127.0.0.1` (localhost). It is not reachable from other machines on the network — only processes running on the same machine can connect. No authentication is implemented, which is acceptable because the attack surface is limited to local processes already running under the same user account.

Do not change `BIND_HOST` to `0.0.0.0` or expose the server through a reverse proxy. The `/explode` endpoint executes arbitrary shell scripts with the permissions of the user who started the server.

---

## FileMaker integration

FileMaker calls the server from an "Explode XML" companion script using the **Insert from URL** step. The step is configured with:

- **URL:** `http://localhost:8765/explode`
- **Method:** POST
- **cURL options:** `--header "Content-Type: application/json" --data @$json_payload`

The FileMaker script builds the JSON payload by assembling field values and preference globals into a Let calculation, then fires the request. A typical payload as assembled in FileMaker:

```json
{
  "solution_name": "Invoice Solution",
  "export_file_path": "/Users/yourname/Desktop/InvoiceSolution.xml",
  "repo_path": "/Users/yourname/agentic-fm"
}
```

After Insert from URL completes, the script parses the response JSON, checks `success`, and branches accordingly — displaying an error dialog if `success` is `false` or proceeding to refresh context if the parse succeeded.

If Insert from URL itself fails (e.g. the server is not running), FileMaker displays its own connection-refused dialog before the script can evaluate the response.

---

## Troubleshooting

### Port already in use

```
OSError: [Errno 48] Address already in use
```

Another process — possibly a previous instance of the companion server — is already bound to port 8765. Find and stop it:

```bash
lsof -i :8765
kill <PID>
```

Or start the server on a different port and update the URL in the FileMaker companion script:

```bash
python agent/scripts/companion_server.py --port 9000
```

### Server not running — FileMaker shows a connection dialog

If the server is not running when FileMaker executes Insert from URL, FileMaker displays a dialog: *"The URL could not be found."* or a similar network error. This is not a script logic failure — it means the companion server is not listening.

Start the server and retry, or check whether the launchd plist is loaded if auto-start is configured.

### fmparse.sh not found

The server constructs the `fmparse.sh` path as `{repo_path}/fmparse.sh`. If `repo_path` is wrong or the file is missing, `fmparse.sh` will fail to launch and the response will contain:

```json
{
  "success": false,
  "exit_code": -1,
  "error": "[Errno 2] No such file or directory: '/path/to/fmparse.sh'"
}
```

Verify that `repo_path` in the JSON payload matches the actual location of the agentic-fm repository root, and that `fmparse.sh` exists there:

```bash
ls /Users/yourname/agentic-fm/fmparse.sh
```

### Permission denied on fm-xml-export-exploder binary

`fmparse.sh` calls `fm-xml-export-exploder`. If the binary is not executable, the subprocess will fail with exit code 1 and `stderr` will contain a permission error. Fix it:

```bash
chmod +x /usr/local/bin/fm-xml-export-exploder
```

If the binary is in a non-standard location and not on `PATH`, supply its full path in the `exploder_bin_path` field of the request payload.

### Diagnosing failures from the server log

When the server is running in the foreground (or writing to a log file), each request produces timestamped output:

```
2026-03-09T14:25:10 INFO 127.0.0.1 - "POST /explode HTTP/1.1" 200 -
2026-03-09T14:25:10 INFO Running fmparse.sh: solution='Invoice Solution' export='/Users/yourname/Desktop/InvoiceSolution.xml' cwd='/Users/yourname/agentic-fm'
2026-03-09T14:25:12 INFO fmparse.sh exited with code 0
```

The `stdout` and `stderr` fields in the response body contain the full output of `fmparse.sh`, which is the first place to look when the exit code is non-zero.
