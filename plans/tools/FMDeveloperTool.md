# FMDeveloperTool

> Status: **exploration** | Created: 2026-03-20

## Overview

`FMDeveloperTool` (v21.1.5.500) is a command-line utility that ships with FileMaker Server. It performs file-level operations on `.fmp12` files: cloning, copying, encrypting, recovering, saving as XML, consistency checking, size analysis, and uploading to FMS.

## Where It Runs

This tool is installed on every FileMaker Server at:
```
/opt/FileMaker/FileMaker Server/Database Server/bin/FMDeveloperTool
```

**In the agentic-fm context**, the tool runs server-side — not in the agent container. The agent triggers it through one of these paths:

1. **FM script via OData** — an FM script calls the tool via the MBS plugin's `Shell.Execute` function (or similar), triggered by the agent through `AGFMScriptBridge`
2. **FM script via Perform AppleScript** — on macOS FMS, a script step runs the shell command directly
3. **Server-side script** — FMS scheduled scripts or system-level scripts that wrap the CLI

The tool is available in this agent container for **exploration and testing only** — to understand its behavior, parse its output formats, and prototype integration before wiring up the server-side execution path.

## Command Reference

### --saveAsXML

Exports the complete solution structure to a monolithic XML file.

```bash
FMDeveloperTool --saveAsXML <file> <username> <password> \
    [-t <output.xml>] [-e <encryption_key>] [-v] [-f]
```

**Why this matters:** This is the same XML format that FileMaker's built-in `Save a Copy as XML` produces, which `fmparse.sh` already parses into `xml_parsed/`. Running this server-side means the agent can trigger a full solution export without requiring the developer to manually run `Explode XML` from FM Pro.

**Integration with existing workflow:**

| Current (Explode XML) | With FMDeveloperTool |
|---|---|
| Developer runs Explode XML in FM Pro | Agent triggers via OData → AGFMScriptBridge → MBS Shell |
| FM Pro calls Save a Copy as XML | FMDeveloperTool --saveAsXML (server-side) |
| FM script POSTs to companion /explode | Same — companion runs fmparse.sh |
| Companion runs fmparse.sh | Same — splits XML into xml_parsed/ |

The difference: step 1 and 2 no longer require FM Pro or developer interaction. The entire export pipeline can be agent-initiated.

**Server-side execution example (via MBS in FM script):**
```
Set Variable [ $cmd ; Value:
    "/opt/FileMaker/FileMaker Server/Database Server/bin/FMDeveloperTool"
    & " --saveAsXML"
    & " " & Quote ( Get ( DocumentsPath ) & Get ( FileName ) & ".fmp12" )
    & " " & $account & " " & $password
    & " -t " & Quote ( $exportPath )
]
Set Variable [ $result ; Value: MBS ( "Shell.Execute" ; $cmd ) ]
```

**Limitations:**
- Requires Full Access or FMMigration account credentials
- EAR-encrypted files need the encryption key (`-e` flag)
- Server-side path resolution differs from client — `Get ( DocumentsPath )` on server returns the FMS databases directory

### --clone

Creates an empty structural copy of a file — all schema, scripts, layouts, relationships, but zero records.

```bash
FMDeveloperTool --clone <file> <username> <password> \
    [-t <clone.fmp12>] [-e <encryption_key>] [-v] [-f]
```

**Why this matters:** Cloning is the first step of the schema migration pipeline. A clone preserves the complete file structure, which can then be modified (new scripts via clipboard, new fields via OData, new relationships/layouts manually by developer) before data migration.

**Use cases:**
- Creating a staging copy for schema changes
- Producing a "blank template" for distribution
- Pre-migration preparation (clone → modify → migrate data)

### --copy / --copyCompress / --copySelfContained

```bash
# Standard copy
FMDeveloperTool --copy <file> <username> <password> [-t <target>] [-e <key>]

# Compacted copy (removes internal fragmentation)
FMDeveloperTool --copyCompress <file> <username> <password> [-t <target>] [-e <key>]

# Self-contained (embeds all external container data)
FMDeveloperTool --copySelfContained <file> <username> <password> [-t <target>] [-e <key>]
```

**Use cases:**
- `--copy` — standard backup before modifications
- `--copyCompress` — reclaim space after bulk deletes or schema changes
- `--copySelfContained` — prepare for migration where external container paths will change; create portable archives

### --checkConsistency

Validates file structural integrity without modifying the file.

```bash
FMDeveloperTool --checkConsistency <file> [-e <encryption_key>]
```

**Why this matters:** This becomes a standard pre/post gate for any file operation:
- Before migration: verify source integrity
- After migration: verify result integrity
- After recovery: verify recovered file
- Periodic health checks as part of server maintenance

No credentials required — only the encryption key if the file is EAR-encrypted.

### --recover

Attempts to rebuild a damaged file.

```bash
FMDeveloperTool --recover <file> [-t <recovered.fmp12>] [-e <key>] \
    [-g rebuild|datablocks|asis] \
    [-i now|later|false] \
    [-r] [-l] [-k] [-b] [-u <username>] [-p <password>]
```

| Flag | Purpose |
|---|---|
| `-g rebuild` | Full block rebuild (default, most thorough) |
| `-g datablocks` | Rebuild data blocks only |
| `-g asis` | Minimal rebuild |
| `-i now` | Rebuild indexes immediately (default) |
| `-i later` | Defer index rebuild to first access |
| `-i false` | Skip index rebuild entirely |
| `-r` | Skip schema rebuild |
| `-l` | Skip structure rebuild |
| `-k` | Keep cached settings (default: delete) |
| `-b` | Bypass startup script and layout (requires admin creds) |

**Use cases:**
- Automated incident response — developer reports corruption, agent triggers recovery server-side, validates result
- Pre-migration safety net — if consistency check fails, recover first
- Multiple recovery passes with different options to maximize data salvage

### --enableEncryption / --removeEncryption

```bash
# Encrypt
FMDeveloperTool --enableEncryption <file> <username> <password> \
    -s <sharedID> -p <passcode> [-h <hint>] [-o] [-t <target>] [-e <key>]

# Decrypt
FMDeveloperTool --removeEncryption <file> <username> <password> \
    [-t <target>] -e <encryption_key>
```

| Flag | Purpose |
|---|---|
| `-s <sharedID>` | Shared ID for files encrypted together (required for encrypt) |
| `-p <passcode>` | EAR encryption password (required for encrypt) |
| `-h <hint>` | Password hint |
| `-o` | Keep open storage containers as-is (don't convert to secure) |

**Use cases:**
- Dev/prod separation — develop unencrypted, encrypt before deployment
- Key rotation — decrypt, re-encrypt with new key
- Compliance automation — ensure all production files meet EAR requirements
- Deployment pipeline — clone → modify → encrypt → upload

### --querySize / --sortBySize

```bash
# Table-level size report
FMDeveloperTool --sortBySize <file> <username> <password> -su mb

# Specific table breakdown
FMDeveloperTool --querySize <file> <username> <password> -tt "Invoices" -su mb

# Specific field
FMDeveloperTool --querySize <file> <username> <password> -tt "Invoices" -tf "Photo" -su mb

# Index sizes
FMDeveloperTool --sortBySize <file> <username> <password> -qi -su mb

# CSV output for programmatic parsing
FMDeveloperTool --sortBySize <file> <username> <password> -su mb -cf
```

| Flag | Purpose |
|---|---|
| `-tt <table>` | Target specific table |
| `-tf <field>` | Target specific field (with `-tt`) |
| `-qi` | Query/sort by index size instead of data size |
| `-ec` | Exclude embedded container data from totals |
| `-qu <N>` | Limit to top N results |
| `-su bytes\|kb\|mb\|gb` | Size unit (default: bytes) |
| `-cf` | CSV output format |

**Why this matters:** The agent can generate quantitative solution audits:
- Which tables consume the most storage
- Which fields have oversized indexes (candidates for `None` storage)
- Container storage analysis (embedded vs. external)
- Growth tracking across snapshots over time

The CSV output (`-cf`) is particularly valuable — the agent can parse it programmatically and generate structured reports with recommendations.

### --uploadDatabases

Uploads `.fmp12` files directly to a FileMaker Server.

```bash
FMDeveloperTool --uploadDatabases <host> <host_username> <host_password> \
    -dl <file1> [<file2> ...] \
    [-tf "Databases/"|"Secure/"|"Databases/Subfolder/"] \
    [-e <encryption_key>] \
    [-worc] [-aodo] [-ic]
```

| Flag | Purpose |
|---|---|
| `-dl <paths>` | List of files/folders to upload |
| `-tf <folder>` | Target folder on server (default: `Databases/`) |
| `-worc` | Upload without remote container data |
| `-aodo` | Don't automatically open/host after upload |
| `-ic` | Ignore SSL certificate verification |
| `-e <key>` | Encryption key (if all files share same EAR key) |

**Why this matters:** Closes the automation loop. After any server-side file operation (clone, migrate, encrypt), the result can be uploaded to FMS (or a different FMS instance) without manual file transfer.

**Note:** This command can target a remote FMS — it doesn't have to upload to the same server it runs on. This enables cross-server deployment workflows.

### --renameFiles

Batch renames files using regex.

```bash
FMDeveloperTool --renameFiles <folder> <username> <password> \
    -sl <file1> [<file2> ...] \
    -rg <regex> -rt <replacement> \
    [-e <key>] [-v] [-f]
```

**Use cases:**
- Solution rebranding (`-rg "OldName_(.*)" -rt "NewName_$1"`)
- Multi-file solutions where internal file references need coordinated renaming
- Version-stamping before deployment

### --removeAdminAccess / --enableKiosk

```bash
# Lock out admin access
FMDeveloperTool --removeAdminAccess <file> [-t <target>] [-e <key>]

# Enable kiosk mode
FMDeveloperTool --enableKiosk <file> [-t <target>] [-e <key>]
```

Specialized deployment hardening commands. No credentials required.

---

## Server-Side Execution Patterns

### Via MBS Plugin (recommended)

The MBS plugin's `Shell.Execute` or `Shell.ExecuteInBackground` functions can run CLI commands from within an FM script. The agent triggers the FM script via OData → AGFMScriptBridge.

```
# FM calculation for the shell command
Let ( [
    ~tool = "/opt/FileMaker/FileMaker Server/Database Server/bin/FMDeveloperTool" ;
    ~file = Get ( DocumentsPath ) & "MyFile.fmp12" ;
    ~cmd = ~tool & " --saveAsXML " & Quote ( ~file ) & " Admin \"\" -t " & Quote ( $exportPath )
] ;
    MBS ( "Shell.Execute" ; ~cmd )
)
```

### Via Perform AppleScript (macOS only)

```applescript
do shell script "/opt/FileMaker/FileMaker\\ Server/Database\\ Server/bin/FMDeveloperTool --checkConsistency " & quoted form of filePath
```

### Via BaseElements Plugin

Similar to MBS — `BE_ExecuteSystemCommand` runs shell commands server-side.

### Via FM Server Scheduled Script

FMS can schedule scripts that include shell execution steps. The agent could create/modify these schedules via fmsadmin (see TOOL_fmsadmin.md).

---

## Credential Management

All FMDeveloperTool operations require the file's Full Access (or FMMigration) account credentials. In an automated context:

- Credentials should be stored in `automation.json` (gitignored) — never hardcoded in scripts or plans
- The FM script wrapper receives credentials as script parameters (JSON, encrypted in transit via HTTPS/OData)
- EAR encryption keys add a second credential layer

Proposed `automation.json` extension:

```json
{
  "solutions": { ... },
  "files": {
    "My Solution.fmp12": {
      "account": "Admin",
      "password": "",
      "encryption_key": ""
    }
  }
}
```

---

## Potential Skills

| Skill | How FMDeveloperTool Fits |
|---|---|
| `solution-export` | `--saveAsXML` as server-side alternative to FM Pro's Explode XML — agent-initiated, no developer interaction |
| `solution-audit` | `--querySize` / `--sortBySize` for quantitative storage analysis; `--checkConsistency` for integrity validation |
| `schema-migrate` | `--clone` creates the migration target; `--checkConsistency` validates pre/post; `--saveAsXML` enables schema diff |
| `file-ops` | Encryption lifecycle, recovery, compression, upload — utility operations triggered by agent via FM scripts |

---

## Next Steps

1. **Test `--saveAsXML` on FMS** — verify output format matches what `fmparse.sh` expects
2. **Build an FM script wrapper** — `AGFMDeveloperTool` script that accepts JSON parameters and calls the CLI via MBS Shell
3. **Test `--querySize` output parsing** — run against a real file, capture CSV output, verify agent can generate meaningful reports
4. **Prototype the clone + migrate pipeline** — end-to-end test with a test solution
5. **Document server-side path resolution** — `Get ( DocumentsPath )` behavior on FMS vs FM Pro
