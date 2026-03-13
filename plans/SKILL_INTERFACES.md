# Skill Interface Contracts

Defines the agreed interfaces between skills — trigger phrases, inputs, outputs, and inter-skill dependencies. All Wave 1 agents must treat this document as authoritative before authoring any skill that calls or is called by another.

---

## Interface conventions

- **Inputs**: What the skill expects to exist or be provided before it runs
- **Outputs**: What the skill produces and where it writes it
- **Calls**: Other skills this skill invokes during execution
- **Called by**: Other skills that invoke this one

---

## Setup & Connectivity

### `odata-connect`

**Trigger phrases**: "set up OData", "connect OData", "configure OData", "OData walkthrough"

**Inputs**:
- Developer has FileMaker Server running (Docker or native)
- Database file name

**Outputs**:
- Developer has verified OData connectivity
- Account with `fmodata` extended privilege confirmed
- No file artifact — this is a guided walkthrough skill

**Calls**: none

**Called by**: `schema-build`, `data-seed`, `data-migrate`

---

### `context-refresh`

**Trigger phrases**: "refresh context", "push context", "update context", "re-export context"

**Inputs**:
- Developer is on the correct layout in FM Pro

**Outputs**:
- `agent/CONTEXT.json` written with current layout scope

**Calls**: none

**Called by**: `multi-script-scaffold`

---

### `solution-export`

**Trigger phrases**: "explode XML", "export solution", "sync xml_parsed", "update xml_parsed"

**Inputs**:
- Developer has FM Pro open with the target solution

**Outputs**:
- `agent/xml_parsed/` fully refreshed

**Calls**: none

**Called by**: `solution-audit`, `solution-docs`, `migrate-out`, `migrate-native`

---

## Schema & Data Model

### `schema-plan`

**Trigger phrases**: "design schema", "plan data model", "create ERD", "design tables"

**Inputs**:
- Natural language description of the application
- Optionally: existing SQL DDL, spreadsheet structure, or legacy schema

**Outputs**:
- `plans/schema/{solution-name}-erd.md` — Mermaid ERD (base tables only)
- `plans/schema/{solution-name}-fm-model.md` — FM-specific model with table occurrences and relationship specs

**Calls**: none

**Called by**: `solution-blueprint`

---

### `schema-build`

**Trigger phrases**: "build schema", "create tables", "create fields", "run schema"

**Inputs**:
- `plans/schema/{solution-name}-fm-model.md` produced by `schema-plan`
- OData connection verified (`odata-connect` completed)
- FM database name and OData base URL

**Outputs**:
- Tables and fields created in live FM solution via OData
- `plans/schema/{solution-name}-build-log.md` — record of what was created

**Calls**: `odata-connect` (if connection not yet verified)

**Called by**: `solution-blueprint`

---

### `relationship-spec`

**Trigger phrases**: "relationship spec", "specify relationships", "define relationships", "relationship checklist"

**Inputs**:
- `plans/schema/{solution-name}-fm-model.md`

**Outputs**:
- `plans/schema/{solution-name}-relationships.md` — click-through checklist: TO names, join fields, cardinality, cascade delete settings

**Calls**: none

**Called by**: `solution-blueprint`

---

## Scripts

### `multi-script-scaffold`

**Trigger phrases**: "multi-script", "scaffold scripts", "placeholder technique", "untitled placeholder"

**Inputs**:
- Description of the script system to build (number of scripts, interdependencies)
- Developer has FM Pro open

**Outputs**:
- Instruction to developer: how many Untitled placeholders to create
- After `context-refresh`: all N scripts generated as fmxmlsnippet in `agent/sandbox/`
- Rename checklist for the developer

**Calls**: `context-refresh` (to capture Untitled script IDs)

**Called by**: `solution-blueprint`

---

### `implementation-plan`

**Trigger phrases**: "plan this", "plan before coding", "decompose requirements", "implementation plan"

**Inputs**:
- Natural language description of the script or feature to build
- `agent/CONTEXT.json` (current layout context)

**Outputs**:
- Written plan in conversation: steps, dependencies, edge cases, FM-specific constraints
- No file artifact unless developer requests one

**Calls**: none

**Called by**: `solution-blueprint`, `script-refactor`, `multi-script-scaffold`

---

### `script-refactor`

**Trigger phrases**: "refactor", "improve this script", "clean up script", "modernise script"

**Inputs**:
- Target script identified (via `script-lookup` or direct sandbox path)
- `agent/CONTEXT.json` or index files for field/layout references

**Outputs**:
- Refactored script in `agent/sandbox/` as fmxmlsnippet
- Summary of changes made

**Calls**: `script-lookup` (if target script not already in sandbox), `implementation-plan`

**Called by**: `solution-audit`

---

### `script-test`

**Trigger phrases**: "test this script", "write a test", "verification script", "assert results"

**Inputs**:
- Target script identified
- Expected inputs and outputs documented

**Outputs**:
- Companion verification script in `agent/sandbox/` as fmxmlsnippet
- Uses `fm-debug` companion server to report pass/fail

**Calls**: `fm-debug`

**Called by**: none (terminal skill)

---

### `script-debug`

**Trigger phrases**: "debug this", "script not working", "wrong output", "script error"

**Inputs**:
- Target script identified
- Error description or unexpected behaviour

**Outputs**:
- Diagnosis and fixed script in `agent/sandbox/`
- May produce debug instrumentation steps as interim output

**Calls**: `fm-debug`

**Called by**: none (terminal skill)

---

## Layout & UI

### `layout-design`

**Trigger phrases**: "design layout", "create layout objects", "build layout", "add fields to layout"

**Inputs**:
- Layout already exists in FM (developer has created the shell)
- `agent/CONTEXT.json` scoped to the target layout
- Design brief (fields, portals, buttons, UI intent)

**Outputs**:
- XML2-formatted layout objects in `agent/sandbox/` ready for clipboard
- Loaded to clipboard via `clipboard.py write`

**Calls**: none

**Called by**: `solution-blueprint`

---

### `layout-spec`

**Trigger phrases**: "layout spec", "layout blueprint", "spec out layout", "describe layout"

**Inputs**:
- Design brief or feature description

**Outputs**:
- Written layout blueprint in conversation: object list, field bindings, portal config, button wiring, conditional formatting rules

**Calls**: none

**Called by**: `solution-blueprint`, `layout-design`

---

### `webviewer-build`

**Trigger phrases**: "web viewer", "webviewer app", "HTML in FileMaker", "build web viewer"

**Inputs**:
- Feature description
- Data schema (from `agent/CONTEXT.json` or `schema-plan` output)

**Outputs**:
- HTML/CSS/JS web viewer content — either inline `Set Web Viewer` step or external file
- FM bridge scripts in `agent/sandbox/` (Perform JavaScript, JSON data passing)

**Calls**: none

**Called by**: `solution-blueprint`

---

## Custom Functions & Configuration

### `function-create`

**Trigger phrases**: "create custom function", "write a custom function", "translate formula", "new function"

**Inputs**:
- Plain-English description or equivalent formula from another language

**Outputs**:
- Custom function XML in `agent/sandbox/` as fmxmlsnippet (`XMFN` class)
- Loaded to clipboard via `clipboard.py write`

**Calls**: none

**Called by**: `solution-blueprint`

---

### `privilege-design`

**Trigger phrases**: "privilege set", "access control", "design privileges", "account structure"

**Inputs**:
- Description of roles and access requirements

**Outputs**:
- Written privilege specification (roles, record-level access rules, extended privileges)
- Where possible: pasteable FM objects

**Calls**: none

**Called by**: `solution-blueprint`

---

## Solution-Level

### `solution-blueprint`

**Trigger phrases**: "build a solution", "design an app", "full solution", "blueprint"

**Inputs**:
- Plain-English application description

**Outputs**:
- Ordered build sequence document in `plans/`
- Calls sub-skills in sequence to produce all artifacts

**Calls**: `schema-plan`, `schema-build`, `relationship-spec`, `multi-script-scaffold`, `function-create`, `layout-spec`, `layout-design`, `webviewer-build`, `privilege-design`

**Called by**: none (entry point skill)

---

### `solution-audit`

**Trigger phrases**: "audit solution", "review solution", "technical debt", "anti-patterns"

**Inputs**:
- `agent/xml_parsed/` populated (via `solution-export`)

**Outputs**:
- Written audit report: naming inconsistencies, missing error handling, anti-patterns, modernisation opportunities

**Calls**: `solution-export` (if xml_parsed is stale), `script-refactor` (for targeted fixes)

**Called by**: none (entry point skill)

---

### `solution-docs`

**Trigger phrases**: "document solution", "generate docs", "solution documentation"

**Inputs**:
- `agent/xml_parsed/` populated

**Outputs**:
- `plans/docs/{solution-name}-documentation.md` — schema, relationships, script inventory, custom functions, privilege sets

**Calls**: `solution-export` (if xml_parsed is stale)

**Called by**: none (entry point skill)

---

## Migration

### `migrate-out`

**Trigger phrases**: "migrate out of FileMaker", "replace FileMaker", "WebDirect to web", "export to web"

**Inputs**:
- DDR XML export from FileMaker
- Optionally: WebDirect rendered HTML captures

**Outputs**:
- SQL schema DDL
- REST API design document
- UI component specifications
- Technology stack recommendation

**Calls**: `solution-export` (if xml_parsed needed as supplement)

**Called by**: none (entry point skill)

---

### `migrate-native`

**Trigger phrases**: "migrate to iOS", "native app", "SwiftUI from FileMaker", "Xcode project"

**Inputs**:
- `agent/xml_parsed/` layouts populated

**Outputs**:
- Xcode project scaffold with SwiftUI or UIKit views replicating layout structure

**Calls**: `solution-export` (if xml_parsed stale)

**Called by**: none (entry point skill)

---

### `migrate-in`

**Trigger phrases**: "migrate into FileMaker", "import schema", "bring data into FileMaker"

**Inputs**:
- Source schema (SQL DDL, ORM model, or spreadsheet)
- OData connection verified

**Outputs**:
- OData calls to create tables and fields
- FM script equivalents of source business logic in `agent/sandbox/`
- Layout specifications for source UI equivalents

**Calls**: `odata-connect`, `schema-build`

**Called by**: none (entry point skill)

---

## Data

### `data-seed`

**Trigger phrases**: "seed data", "test data", "populate solution", "generate records"

**Inputs**:
- Schema exists in live FM solution
- OData connection verified
- Description of data volume and realism requirements

**Outputs**:
- Records created in live FM solution via OData
- Summary of what was seeded

**Calls**: `odata-connect` (if not verified)

**Called by**: none (entry point skill)

---

### `data-migrate`

**Trigger phrases**: "migrate data", "import records", "move data into FileMaker"

**Inputs**:
- Source data (CSV, SQL dump, JSON, API)
- Field mapping between source and FM fields
- OData connection verified

**Outputs**:
- Records created in live FM solution via OData
- Migration summary with error count and field mapping log

**Calls**: `odata-connect` (if not verified)

**Called by**: none (entry point skill)
