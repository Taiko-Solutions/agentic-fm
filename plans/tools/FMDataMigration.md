# FMDataMigration

> Status: **exploration** | Created: 2026-03-20

## Overview

`FMDataMigration` (v21.1.5.500) is a command-line utility that ships with FileMaker Server. It migrates all record data from a source FileMaker file into a clone of that file. This is the standard tool for deploying schema changes to production FileMaker solutions.

## Where It Runs

This tool is installed on every FileMaker Server at:
```
/opt/FileMaker/FileMaker Server/Database Server/bin/FMDataMigration
```

**In the agentic-fm context**, the tool runs server-side — triggered by the agent through FM scripts via OData → AGFMScriptBridge → MBS plugin shell execution. The tool is available in this agent container for **exploration and testing only**.

## Command Reference

```bash
FMDataMigration -src_path <source> -clone_path <clone> [options]
```

### Required Parameters

| Parameter | Purpose |
|---|---|
| `-src_path <path>` | Path to the source file (contains the data to migrate) |
| `-clone_path <path>` | Path to the clone file (contains the target schema, empty of data) |

### Authentication

| Parameter | Default | Purpose |
|---|---|---|
| `-src_account <account>` | `Admin` | Full Access or FMMigration account on source |
| `-src_pwd <password>` | blank | Password for source account |
| `-src_key <key>` | — | EAR decryption key for source file |
| `-clone_account <account>` | `Admin` | Full Access or FMMigration account on clone |
| `-clone_pwd <password>` | blank | Password for clone account |
| `-clone_key <key>` | — | EAR decryption key for clone file |

### Output Control

| Parameter | Default | Purpose |
|---|---|---|
| `-target_path <path>` | Source path + " migrated" | Where to write the migrated file |
| `-target_locale <locale>` | Source file's locale | Override locale for the output file |
| `-force` | — | Overwrite existing target file |
| `-v` | — | Verbose output (detailed migration report) |
| `-q` | — | Quiet mode (minimal output) |

### Migration Behavior

| Parameter | Purpose |
|---|---|
| `-ignore_valuelists` | Use value lists from the clone instead of the source. Use when value lists were intentionally changed in the clone. |
| `-ignore_accounts` | Use accounts and encryption key from the clone instead of the source. Use when the security model was changed in the clone. |
| `-ignore_fonts` | Skip font mapping for field contents. Use when font differences between systems are acceptable. |
| `-reevaluate` | Recalculate all stored calculation fields after migration. **Important when calculation logic changed in the clone.** |
| `-rebuildindexes` | Rebuild all field indexes after migration. **Important after field type changes or index strategy modifications.** |

---

## How Data Migration Works

FMDataMigration performs a table-by-table, field-by-field data transfer:

1. **Table matching** — maps source tables to clone tables by internal table ID (not name). Tables that exist in the source but not the clone are skipped. Tables in the clone but not the source remain empty.

2. **Field matching** — maps source fields to clone fields by internal field ID (not name). Fields renamed in the clone still receive data (IDs match). Fields added to the clone start empty. Fields removed from the clone have their data discarded.

3. **Record transfer** — copies all records from each matched source table to the corresponding clone table, preserving record IDs (primary keys), creation/modification timestamps, and container data.

4. **Post-processing** — optionally recalculates stored calculations (`-reevaluate`) and rebuilds indexes (`-rebuildindexes`).

### What Transfers

- All records across all matched tables
- All field data including containers (embedded and external references)
- Record-level metadata (creation timestamp, modification timestamp, record ID)
- Serial number next values
- Value lists (unless `-ignore_valuelists`)
- Accounts and privilege sets (unless `-ignore_accounts`)

### What Does NOT Transfer

- The clone's schema wins — table structure, field definitions, scripts, layouts, relationships, custom functions, privilege sets (unless overridden by flags) all come from the clone
- Global field values come from the clone (globals are schema-level, not record-level)
- External container files are referenced by path — if paths change between source and clone environments, containers may not resolve

---

## The Schema Migration Pipeline

This is the primary use case for agentic-fm integration. The combination of `FMDeveloperTool --clone` and `FMDataMigration` creates a staged schema deployment model:

```
Production File (v1)                    Clone (v2)
┌─────────────────────┐                ┌─────────────────────┐
│ Schema v1           │   --clone →    │ Schema v1 (empty)   │
│ 1M records          │                │                     │
│                     │                │ Developer modifies: │
│                     │                │  + new relationships│
│                     │                │  + new layouts      │
│                     │                │                     │
│                     │                │ Agent deploys:      │
│                     │                │  + new scripts      │
│                     │                │  + new fields       │
│                     │                │  + new functions    │
└─────────┬───────────┘                └──────────┬──────────┘
          │                                       │
          │        FMDataMigration                 │
          │   -src_path v1 -clone_path v2         │
          └──────────────┬────────────────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │ Migrated File       │
               │ Schema v2 + Data v1 │
               │ Ready to host       │
               └─────────────────────┘
```

### Why This Matters

Today, schema changes to a production FileMaker solution happen live — the developer modifies the hosted file directly. There's no staging, no rollback, no version control for structure. Clone + Migrate creates a workflow analogous to database migrations in web development:

1. Clone the production file (structure only)
2. Make all schema changes to the clone (agent + developer collaborate)
3. Test the clone with sample data
4. Close the production file on FMS
5. Migrate production data into the tested clone
6. Host the migrated file as the new production
7. Keep the original as rollback insurance

### Server-Side Execution

The migration runs on the FMS machine where both files are accessible. The agent triggers it via an FM script:

```
# FM calculation for the shell command
Let ( [
    ~tool = "/opt/FileMaker/FileMaker Server/Database Server/bin/FMDataMigration" ;
    ~cmd = ~tool
        & " -src_path " & Quote ( $srcPath )
        & " -clone_path " & Quote ( $clonePath )
        & " -target_path " & Quote ( $targetPath )
        & " -src_account " & Quote ( $account )
        & " -src_pwd " & Quote ( $password )
        & " -clone_account " & Quote ( $account )
        & " -clone_pwd " & Quote ( $password )
        & " -reevaluate -rebuildindexes -force -v"
] ;
    MBS ( "Shell.Execute" ; ~cmd )
)
```

The verbose output (`-v`) should be captured and returned to the agent for parsing — it contains the migration report with table/field match results and any warnings.

---

## Migration Scenarios

### Scenario 1: Adding Fields and Scripts

The most common case. New fields are added to existing tables, new scripts reference them.

```bash
FMDataMigration -src_path production.fmp12 -clone_path clone.fmp12 \
    -target_path migrated.fmp12 \
    -src_account Admin -src_pwd "" \
    -clone_account Admin -clone_pwd "" \
    -force -v
```

New fields in the clone will be empty after migration. The agent can then populate them via OData if needed (`data-seed` skill).

### Scenario 2: Changing Calculation Logic

When stored calculations change in the clone, their values need recalculating against the migrated data.

```bash
FMDataMigration ... -reevaluate -v
```

The `-reevaluate` flag forces all stored calcs to recalculate. Without it, the migrated file carries stale calculation results from the source.

### Scenario 3: Changing Security Model

When accounts, privilege sets, or extended privileges change in the clone.

```bash
FMDataMigration ... -ignore_accounts -v
```

Without `-ignore_accounts`, the source's accounts overwrite the clone's. Use this flag when the clone has a new security model.

### Scenario 4: Full Schema Overhaul

Major changes: new tables, removed tables, reorganized fields, new value lists, new accounts.

```bash
FMDataMigration ... -ignore_valuelists -ignore_accounts -reevaluate -rebuildindexes -force -v
```

All flags active — use the clone's value lists and accounts, recalculate everything, rebuild all indexes.

### Scenario 5: Multi-File Solutions

FileMaker solutions often span multiple files (UI file + data file, or functional separation). Each file migrates independently:

```bash
FMDataMigration -src_path UI_v1.fmp12 -clone_path UI_v2.fmp12 ...
FMDataMigration -src_path Data_v1.fmp12 -clone_path Data_v2.fmp12 ...
```

File references between files don't change during migration (they're schema, not data), but the agent should verify external data source paths match after migration.

---

## Error Handling

FMDataMigration exits with status codes:
- **0** — success
- **Non-zero** — failure (file not found, auth failure, corruption, etc.)

The verbose output (`-v`) contains detailed diagnostics. The agent should:
1. Capture both stdout and stderr
2. Parse for warnings (unmatched tables, unmatched fields, font mapping issues)
3. Run `FMDeveloperTool --checkConsistency` on the result
4. Report findings to the developer before hosting the migrated file

---

## Potential Skills

| Skill | How FMDataMigration Fits |
|---|---|
| `schema-migrate` | Core engine — migrates data from production to modified clone |
| `data-migrate` | Can also serve general data transfer between files (not just schema changes) |
| `solution-audit` | Pre-migration analysis — compare source and clone XML to predict migration behavior |
| `file-ops` | Migration as one operation in a larger pipeline (clone → modify → migrate → encrypt → upload) |

---

## Considerations

### File Locking

Both source and clone files must be **closed** (not hosted on FMS) during migration. The workflow requires:
1. Close the production file on FMS (`fmsadmin close`)
2. Run migration
3. Open the migrated file on FMS (`fmsadmin open`)

The agent can orchestrate this via fmsadmin commands (see TOOL_fmsadmin.md).

### Downtime

Migration requires the production file to be offline. For large files (millions of records, large containers), migration can take significant time. The agent should:
- Estimate migration duration based on file size (from `FMDeveloperTool --querySize`)
- Communicate expected downtime to the developer
- Suggest scheduling for low-traffic windows

### Container Data

External container data is referenced by path. If the clone changes external storage configuration, container references may break. The agent should flag this when comparing source and clone schemas.

### Rollback

The original source file is not modified by migration. It serves as the rollback path — if the migrated file has issues, re-host the original. The agent should always preserve the source.

---

## Next Steps

1. **Test migration on FMS** — run a migration via MBS Shell in an FM script, capture verbose output
2. **Parse verbose output** — understand the report format so the agent can generate meaningful migration summaries
3. **Build `AGFMDataMigration` FM script** — wrapper script that accepts JSON parameters and runs the CLI
4. **Test multi-file migration** — verify behavior with external file references
5. **Measure performance** — establish baseline migration times per record count / file size for downtime estimation
