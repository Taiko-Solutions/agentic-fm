# Taiko Solutions — Development Standards

This folder contains Taiko-specific coding conventions, architectural patterns, and knowledge documents. They extend and, where noted, override the base conventions in `agent/docs/CODING_CONVENTIONS.md`.

## How it works

The AI reads these documents in addition to the standard project docs. The priority order is:

1. **Taiko conventions** (`agent/docs/taiko/CODING_CONVENTIONS.md`) — read first, always applies
2. **Base conventions** (`agent/docs/CODING_CONVENTIONS.md`) — fallback for anything Taiko does not define
3. **Taiko knowledge base** (`agent/docs/taiko/knowledge/MANIFEST.md`) — scanned by keyword before writing scripts
4. **Base knowledge base** (`agent/docs/knowledge/MANIFEST.md`) — also scanned

## Contents

### CODING_CONVENTIONS.md

Taiko naming standards, script structure preferences, language rules, and author metadata. Overrides specific sections of the base conventions (variables use PascalCase instead of camelCase, comments in Spanish, Insert Calculated Result preferred over Set Variable, etc.).

### knowledge/

Curated documents describing Taiko's architectural patterns and development decisions. These go beyond generic FileMaker best practices — they define how Taiko builds solutions.

| File | Description |
|------|-------------|
| `clew-pattern.md` | Error handling system using Loop/Exit Loop If as try-catch |
| `three-layer-architecture.md` | Interface, Controller, Data layer separation |
| `utility-transactional.md` | Non-destructive editing with global fields and transactions |
| `logging-system.md` | Error logging to Log table with retry capability |
| `executesql-pattern.md` | Resilient ExecuteSQL pattern with SQL.Get* functions |

### custom_functions/

fmxmlsnippet XML files containing custom function definitions that every Taiko solution should include. These can be pasted directly into FileMaker.

| File | Description |
|------|-------------|
| `sql-cfs.xml` | fm-sql-cfs module (Geist Interactive) — SQL.GetFieldName, SQL.GetTableName, SQL.GetColumn, SQL.GetColumn2Fields, SQL.GetColumnStatement, SQL.GetRecordsAsJSON, SQL.RecordExists |
| `clew.xml` | Clew error handling framework (Marcelo Piñeyro / Soliant) — 40 functions: error.*, _error_* constants, json.* utilities, Log.*, getScriptEnvironment, IsRunningOnServer |
| `triggers.xml` | Trigger suppression module (Jeremy Bante) — TriggersAreActive, TriggersDisable, TriggersEnable, TriggersReset |

### templates/

Human-readable script templates in `scripts_sanitized` format (numbered, indented steps). The AI uses these as structural references when composing scripts — they are not XML output.

| File | Description |
|------|-------------|
| `clew-simple.md` | Traditional Clew pattern (read, query, navigation scripts) |
| `clew-transactional.md` | Utility Manager + Initialize Shadow + Transactional Controller |

### UPSTREAM_IMPROVEMENTS.md

Instructions and a reusable CLAUDE.md section for solution-specific repos. When included, the AI will detect tool improvements during normal development and log proposals to `agent/UPSTREAM_PROPOSALS.md` — without ever leaking solution-specific data. The developer reviews proposals periodically and applies them to this template repo.

## Maintenance

These documents are maintained by the Taiko Solutions team. They live exclusively on the `taiko` branch and are never merged to `main` or proposed upstream.

To update: edit the files directly on the `taiko` branch, commit, and push.
