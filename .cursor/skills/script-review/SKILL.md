---
name: script-review
description: Code review a FileMaker script and its full call tree — all subscripts reached via Perform Script are loaded and analysed together. Evaluates error handling, structure, naming, performance, parameter contracts, and cross-script issues. Use when the developer says "review", "code review", "evaluate", or "assess" a script, or mentions "script ID" in a review context.
---

# Script Review

Perform a thorough code review of a FileMaker script and every script it calls. The review covers the full call tree — not just the entry-point script in isolation.

**CRITICAL**: Debugging breakpoints within FileMaker scripts are not a runtime issue. Breakpoints are only active when a developer explicitly invokes the FileMaker debugger. Do not flag them.

---

## Step 1: Locate the target script

Use the `script-lookup` skill to find the script if not already identified. Read the human-readable version from `agent/xml_parsed/scripts_sanitized/`.

---

## Step 2: Resolve the call tree

Before analysing any logic, build the full picture of every script involved.

### 2a. Extract Perform Script references

Scan the human-readable script for all `Perform Script` lines. Each one names or references a subscript. Extract every target script name.

```bash
grep -i "Perform Script" "agent/xml_parsed/scripts_sanitized/{solution}/{path}.txt"
```

### 2b. Load each subscript

For each subscript found, locate and read its human-readable version from `scripts_sanitized/`. Use the scripts index to resolve names to paths:

```bash
grep "ScriptName" "agent/context/{solution}/scripts.index"
```

### 2c. Recurse

Each subscript may itself call further subscripts. Repeat 2a–2b for every newly loaded script until no new `Perform Script` references are found. Track visited scripts to avoid cycles.

### 2d. Present the call tree

Before starting the review, present the resolved call tree so the developer can see the full scope:

```
## Call tree: [Entry Script Name]

1. Entry Script Name
   ├── Subscript A
   │   └── Subscript A1
   ├── Subscript B
   └── Subscript C
       └── Subscript A  (already loaded)
```

Note any scripts referenced by name calculation (`Perform Script by name`) — these cannot be statically resolved. Flag them so the developer can clarify which scripts may be called.

Note any `Perform Script` references to scripts that don't exist in `scripts_sanitized/` — these may be in a different solution file, or may have been deleted. Flag them.

---

## Step 3: Analyse — entry script

Review the entry-point script against these categories:

### Error handling
- Missing `Set Error Capture [ On ]` / `Allow User Abort [ Off ]` header (especially for server-side scripts)
- Steps that can fail without an immediate `Get ( LastError )` check
- Error data captured in separate steps instead of the single-expression `$errData` pattern (see `agent/docs/knowledge/error-data-capture.md`)
- Missing cleanup path (no revert/commit on failure)

### Structure
- Deeply nested If/Else chains that should be a single-pass loop (see `agent/docs/knowledge/single-pass-loop.md`)
- Repeated logic that could be hoisted to a variable or extracted to a subscript
- Missing guard clauses (parameter validation, empty found set checks)
- Dead code (disabled steps that serve no documentation purpose)

### Naming and conventions
- Variable names that don't follow conventions (`agent/docs/CODING_CONVENTIONS.md`)
- Inconsistent naming within the script
- Magic numbers or repeated string literals that should be variables (see `agent/docs/knowledge/dry-coding.md`)

### Performance
- Unnecessary layout switches
- Commit Records inside loops (should be after the loop where possible)
- Redundant Perform Find when a constrained find or GTRR would suffice

### Parameter contract
- Is the expected parameter format documented (via `$README` or comment)?
- Does the script validate its parameter before using it?
- Does it `Exit Script` with a documented result format?

---

## Step 4: Analyse — subscripts and cross-script issues

Review each subscript using the same categories as Step 3. Additionally, look for issues that only emerge when scripts are considered together:

### Parameter contract alignment
- Does the caller pass what the callee expects? Compare the `Perform Script` parameter expression against the subscript's `Get ( ScriptParameter )` parsing.
- Does the caller check `Get ( ScriptResult )` after the call? Does the callee actually `Exit Script` with a result?
- Type mismatches — caller sends a plain string, callee expects JSON (or vice versa)

### Layout context assumptions
- Does a subscript assume it's on a specific layout without navigating there?
- Does a subscript change the layout without restoring it, breaking the caller's context?
- Does a subscript call `Go to Layout [ original layout ]` before exiting?

### Error propagation
- If a subscript encounters an error, does it report it via `Exit Script` result?
- Does the caller check the subscript's result and handle errors?
- Or does the error silently disappear at the script boundary?

### Variable scope leakage
- Does a subscript set global variables (`$$`) that the caller depends on? (This is a fragile coupling — flag it)
- Does a subscript read global variables set by the caller instead of receiving them as parameters?

### Transaction boundaries
- If the entry script opens a transaction, do subscripts commit or revert within it? (This can break the outer transaction)
- Are Commit Records calls in subscripts aware of the caller's transaction state?

---

## Step 5: Present findings

Organise the review as a single report covering the full call tree. Group by severity:

```
## Code Review: [Entry Script Name]

### Call tree
(from Step 2d)

### Critical
Issues that will cause failures or data corruption:
- [Script Name, line N] — Set Field after Perform Find with no error 401 check
- [Subscript A, line N] — Commits inside caller's transaction

### Important
Issues that affect reliability or maintainability:
- [Script Name, line N] — Error data captured in separate steps (use single-expression pattern)
- [Script Name → Subscript B] — Caller doesn't check Get(ScriptResult)

### Suggestions
Improvements that are not urgent:
- [Script Name, line N] — Magic number "30" should be a variable ($dayThreshold)
- [Subscript A] — Missing $README documentation block

### Positive
Things the script does well (acknowledge good patterns):
- Clean parameter validation with early exit
- Consistent variable naming
```

**Line number references** must always refer to the human-readable (`scripts_sanitized`) version, never the XML.

---

## Two script formats — know the difference

There are two distinct XML formats in this project. They are **not interchangeable**:

| Format | Location | Usable as output? |
|---|---|---|
| FileMaker "Save As XML" export | `agent/xml_parsed/scripts/` | **No** — read-only reference only |
| FileMaker clipboard / fmxmlsnippet | `agent/scripts/` or `agent/sandbox/` | **Yes** — this is the output format |

When applying review findings as code changes, follow the refactoring workflow:

1. **Find or create the fmxmlsnippet version** — check `agent/sandbox/` first. If none exists, convert via `python3 agent/scripts/fm_xml_to_snippet.py`.
2. **Apply only the targeted changes** — unchanged steps remain verbatim.
3. **Validate**: `python3 agent/scripts/validate_snippet.py agent/sandbox/{script_name}`
