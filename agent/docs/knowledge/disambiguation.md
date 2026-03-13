# FileMaker Disambiguation & Invariants

Commonly confused term pairs and non-negotiable structural rules. These are the cases most likely to produce incorrect script logic or broken references if misapplied.

For the full glossary of FileMaker terminology, see `agent/docs/reference/terminology.md`.

---

## Commonly Confused Terms

| Often confused                                | Distinction                                                                                                                                                                                                                       |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Table vs. Table Occurrence                    | A table is the data container. A TO is a reference to that table on the Relationship Graph. Layouts and relationships connect through TOs, not directly to tables.                                                                |
| Field Type vs. Field Storage                  | Field type is the data type (Text, Number, etc.). Storage refers to how the value is held: regular, global, or container storage options (embedded, external open, external secure).                                              |
| Script Parameter vs. Script Variable          | A parameter is a single value passed at invocation. Variables are created within the script. Parameters arrive via `Get ( ScriptParameter )`; variables via `Set Variable`.                                                       |
| Script Parameter vs. Script Result            | Parameters go in via `Get ( ScriptParameter )`. Results come out via `Exit Script [ Result: ... ]` and are read with `Get ( ScriptResult )`.                                                                                      |
| Commit (Record) vs. Commit Transaction        | Committing a record saves that record's changes. Committing a transaction saves all records modified since Open Transaction.                                                                                                      |
| fmxmlsnippet vs. Save a Copy as XML           | fmxmlsnippet is the clipboard exchange format. Save a Copy as XML is a full-schema export. Different XML structures, different purposes.                                                                                          |
| Layout Context vs. Script Context             | Layout context is the TO assigned to a layout. Script context is the layout (and therefore TO) the script is currently operating on, which can change via Go to Layout.                                                           |
| Custom Function vs. Get() Function            | Custom Functions are developer-defined and reusable. Get() functions are built-in and return environment/state information.                                                                                                       |
| Stored Calculation vs. Auto-Enter Calculation | A stored calculation field recalculates automatically when referenced fields change. An auto-enter calculation runs only at record creation or modification and can be overridden by the user (if "Do not replace" is unchecked). |
| List View vs. Table View                      | List view is a custom-designed layout for multiple records. Table view is a dynamic, spreadsheet-like grid that does not render all layout objects.                                                                               |

---

## Key Invariants

Non-negotiable system rules. These prevent common errors in scripting and AI-generated code.

**Structural**

- A layout references exactly one table occurrence.
- A table occurrence references exactly one base table.
- A field belongs to exactly one base table.
- A relationship connects exactly two table occurrences.
- A found set is scoped to exactly one window — there is no file-level found set.
- A transaction cannot span multiple files.
- Global variables are scoped per file session, not per solution.
- Layout objects cannot exist without a layout.

**Context & Indexing**

- Field resolution is relative to layout context unless fully qualified with a TO name.
- Unstored calculations cannot be indexed.
- Global fields cannot be indexed.
- Indexing is required for relationship matching (except Cartesian joins) and efficient finds.
- ExecuteSQL() ignores the found set and layout context.
- Server-side scripts (PSOS) have context but no UI state, client windows, or client globals.

**Security & Execution**

- Security is governed by privilege sets, not by layouts.
- Run with Full Access elevates a script only during its execution.
- Record-Level Access is evaluated per record using a boolean calculation.
- Extended privileges enable features but do not grant data access on their own.
- Commit Record ≠ Commit Transaction.
- Script Result is retrievable only by the directly calling script.
