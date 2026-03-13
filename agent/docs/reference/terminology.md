# FileMaker Terminology

Canonical definitions for FileMaker Pro concepts. This file ensures consistent usage across the project and alignment between human-authored docs and AI-generated output.

Terms are grouped by domain. Where a term has common aliases or is easily confused with another, a **Note** is included.

---

## Solution Architecture

| Term                      | Definition                                                                                                                                                                                                                              |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Solution                  | A FileMaker application, which may consist of one or more files. Often used interchangeably with "file" in single-file solutions.                                                                                                       |
| File                      | A single `.fmp12` document. A file contains tables, layouts, scripts, value lists, custom functions, privilege sets, and all other schema objects.                                                                                      |
| Context                   | The table occurrence assigned to a layout — the "perspective" through which fields, relationships, and related data are accessed. Scripts execute relative to the context of the frontmost layout. Context can change via Go to Layout. |
| Data Source               | A reference from one file to another, enabling cross-file relationships and script calls. Can point to FileMaker files or external SQL sources (ESS).                                                                                   |
| External SQL Source (ESS) | A live connection to an ODBC data source (MySQL, PostgreSQL, SQL Server, Oracle) that surfaces external tables as TOs inside the Relationship Graph.                                                                                    |

## Tables & Fields

| Term                         | Definition                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Table                        | A base data entity that stores records. Defined in Manage Database.                                                                                                                                                                                                                                                                                  |
| Base Table                   | The underlying table definition, as distinct from a Table Occurrence on the Relationship Graph. Each table has exactly one base table.                                                                                                                                                                                                               |
| Table Occurrence (TO)        | An instance of a base table placed on the Relationship Graph. A single base table can have many TOs, each with different relationships. All layouts and scripts function through a TO, not the base table directly.                                                                                                                                  |
| Table Occurrence Group (TOG) | A cluster of TOs connected by relationships. An organizational concept within FileMaker is to call the primary TO the anchor.                                                                                                                                                                                                                        |
| Field                        | A named column within a table that stores a single value per record.                                                                                                                                                                                                                                                                                 |
| Field Type                   | The data type assigned to a field: Text, Number, Date, Time, Timestamp, or Container.                                                                                                                                                                                                                                                                |
| Calculation Field            | A field whose value is computed from an expression. Can be stored (indexed) or unstored.                                                                                                                                                                                                                                                             |
| Summary Field                | A field that aggregates values across records (Total, Average, Count, Minimum, Maximum, Standard Deviation, Fraction of Total, List of).                                                                                                                                                                                                             |
| Global Field                 | A field with global storage — one value shared across all records. In a hosted file, each session gets its own copy; the stored value is whatever was saved before hosting. Cannot be indexed.                                                                                                                                                       |
| Container Field              | A field that holds files, images, PDFs, or other binary data. Can be embedded, stored externally (open or secure), or referenced.                                                                                                                                                                                                                    |
| Auto-Enter                   | Options that automatically populate a field value on record creation or modification: serial number, creation/modification account or timestamp, calculated value, looked-up value, or data. Auto-enter calculations run only at record creation or modification — not whenever referenced fields change. Auto-enter settings DO trigger on Imports. |
| Validation                   | Rules that constrain what values a field will accept: not empty, unique, member of value list, in range, validated by calculation, maximum length.                                                                                                                                                                                                   |
| Index                        | An internal lookup structure FileMaker maintains for a field to enable finds, relationships, and value lists. Can be None, Minimal, or All. Unstored calculations and global fields cannot be indexed.                                                                                                                                               |
| Stored vs. Unstored          | A stored calculation's result is written to disk and indexed; it updates automatically when referenced fields in the same record change. An unstored calculation is evaluated on demand, cannot be indexed, and cannot be used as the key on the "many" side of a relationship.                                                                      |
| Lookup                       | An auto-enter option that copies a value from a related record into the current field when the relationship key changes. Distinct from a relationship-based display of related data.                                                                                                                                                                 |

**Note:** "Field type" refers to the data type (Text, Number, etc.), while "field kind" is sometimes used informally to distinguish regular fields from Calculation fields, Summary fields, and Global fields. Claris documentation uses "field type" for both concepts depending on context.

## Records & Found Sets

| Term                | Definition                                                                                                                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Record              | A single row of data in a table.                                                                                                                                                                        |
| Found Set           | The subset of records currently active in a window. Script steps and many menu commands operate on the found set. Scoped to exactly one window — there is no file-level found set.                      |
| Show All Records    | Replaces the current found set with every record in the table.                                                                                                                                          |
| Omit                | Exclude specific records from the found set without deleting them.                                                                                                                                      |
| Constrain Found Set | Narrow the current found set by performing a find within it.                                                                                                                                            |
| Extend Found Set    | Add records to the current found set by performing a find on the full table and merging results.                                                                                                        |
| Sort Order          | The sequence in which records appear in the found set. Sort orders can be ascending, descending, or by value list. Persists until explicitly changed, a new find is performed, or records are unsorted. |
| Commit              | Save pending changes to the current record. Triggered by clicking outside fields, changing records, changing layouts, or the Commit Records/Requests script step. Not the same as Commit Transaction.   |
| Revert              | Discard all uncommitted changes to the current record, restoring it to its last committed state.                                                                                                        |
| Record Locking      | FileMaker uses optimistic locking — a record is locked for editing only when a user begins modifying it. Other users can read but not edit a locked record. The lock is released on commit or revert.   |
| Snapshot Link       | A `.fmpsl` file that captures a found set (as record IDs), sort order, layout, and mode. Opening it restores that state.                                                                                |

## Layouts

| Term               | Definition                                                                                                                                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Layout             | A view that defines how data from a table occurrence is displayed and interacted with. Every layout is assigned to exactly one TO.                                                                               |
| Layout Part        | A horizontal band on a layout that controls what data appears and how it repeats: Header, Leading Grand Summary, Sub-Summary (when sorted by), Body, Trailing Grand Summary, Footer, Title Header, Title Footer. |
| Form View          | Displays one record at a time.                                                                                                                                                                                   |
| List View          | Displays multiple records vertically, each in its own Body part. A custom-designed layout for viewing multiple records.                                                                                          |
| Table View         | Displays records in a spreadsheet-like grid. A dynamic view that does not render all layout objects.                                                                                                             |
| Layout Theme       | A collection of styles (fonts, colors, spacing) applied to a layout. Themes can be customized and saved.                                                                                                         |
| Layout Object      | Any element placed on a layout: field, text, button, portal, tab control, slide control, popover, web viewer, chart, button bar, etc. Layout objects cannot exist without a layout.                              |
| Layout Object Name | A developer-assigned name for a layout object, used by script steps like `Go to Object` and functions like `GetLayoutObjectAttribute`.                                                                           |

## Layout Objects

| Term                   | Definition                                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Portal                 | A layout object that displays a list of related records from a related TO. Portals can be sorted, filtered, and allow record creation.                                                    |
| Button                 | A layout object that triggers a single script step or a script when clicked.                                                                                                              |
| Button Bar             | A segmented control containing multiple buttons (segments) displayed as a single bar. Each segment can trigger its own action.                                                            |
| Popover                | A layout object consisting of a Popover Button and a Popover Panel. Clicking the button reveals the panel, which can contain other layout objects.                                        |
| Tab Control            | A layout object with multiple named panels (tabs). Only one panel is visible at a time.                                                                                                   |
| Slide Control          | A layout object with multiple panels navigated by swiping or dots. Similar to a tab control but without visible tab labels.                                                               |
| Web Viewer             | A layout object that renders HTML/CSS/JavaScript content, either from a URL or from a calculated HTML expression.                                                                         |
| Chart                  | A layout object that displays data graphically (bar, line, area, pie, scatter, bubble).                                                                                                   |
| Merge Field            | A placeholder (`<<FieldName>>`) embedded in a text object that displays field data. Cannot be entered or edited directly.                                                                 |
| Merge Variable         | A placeholder (`<<$variable>>` or `<<$$variable>>`) embedded in a text object that displays a variable's value.                                                                           |
| Conditional Formatting | Rules applied to a layout object that change its appearance (fill color, text color, font style, etc.) when a boolean condition evaluates to true. Does not alter data — only appearance. |
| Hide Condition         | A boolean calculation on a layout object that, when true, makes the object invisible in Browse and Find modes. Evaluated per object per record.                                           |
| Tooltip                | A calculation-driven text label that appears when a user hovers over a layout object.                                                                                                     |
| Placeholder Text       | Dimmed text displayed inside an empty field to indicate expected input. Disappears when the user starts typing.                                                                           |

## Windows

| Term                     | Definition                                                                                                                                                      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Document Window          | A standard window that can be resized, minimized, and moved. Each document window maintains its own found set, sort order, and layout.                          |
| Card Window              | A modal child window that floats above its parent. The parent window is dimmed and non-interactive while the card is open. Cards cannot be resized by the user. |
| Floating Document Window | A window that stays above all document windows but does not block interaction with them. Useful for palettes and utilities.                                     |

## Modes

| Term         | Definition                                                                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Browse Mode  | The default mode for viewing and editing data.                                                                                                                     |
| Find Mode    | A mode where field entry creates find criteria (requests) rather than editing data. Performing the find switches back to Browse mode with the resulting found set. |
| Layout Mode  | A design mode for modifying layouts. Only available in FileMaker Pro, not in Go or WebDirect.                                                                      |
| Preview Mode | Displays the layout as it would appear when printed, including sliding, sub-summaries, and page breaks.                                                            |

## Scripting

| Term                            | Definition                                                                                                                                                                                                                                                                       |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Script                          | A named sequence of script steps that automates tasks. Scripts are stored in the file and organized in folders. Scripts are not bound to a layout but execute in layout context.                                                                                                 |
| Script Step                     | A single instruction within a script (e.g., Set Field, Go to Layout, Perform Find).                                                                                                                                                                                              |
| Subscript                       | A script called from another script via Perform Script or Perform Script on Server. Not a distinct object type — any script can be a subscript.                                                                                                                                  |
| Script Parameter                | A single text value passed to a script at invocation via `Get ( ScriptParameter )`. Compound values are typically passed as JSON, return-delimited lists, or Let-formatted text.                                                                                                 |
| Script Result                   | A value returned by a script via `Exit Script [ Result: ... ]`. Retrieved by the caller with `Get ( ScriptResult )`. Retrievable only by the calling script.                                                                                                                     |
| Script Trigger                  | An event-driven hook that executes a script when a specified action occurs. Triggers can be attached to layout objects (e.g., OnObjectEnter, OnObjectExit, OnObjectKeystroke, OnObjectValidate) or to layouts (e.g., OnLayoutEnter, OnLayoutExit, OnRecordLoad, OnRecordCommit). |
| Script Folder                   | An organizational container for scripts in the script workspace. Folders can be nested.                                                                                                                                                                                          |
| Error Capture                   | `Set Error Capture [ On ]` suppresses FileMaker's default error dialogs, allowing the script to handle errors programmatically via `Get ( LastError )`.                                                                                                                          |
| Perform Script on Server (PSOS) | Executes a script on FileMaker Server rather than the client. The server-side session has no access to the client's windows, found set, globals, or UI.                                                                                                                          |

## Variables

| Term                   | Definition                                                                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Local Variable (`$`)   | A variable scoped to the currently executing script. It is destroyed when the script ends. Not visible to subscripts or other scripts.                                        |
| Global Variable (`$$`) | A variable scoped to the current file session. Visible to all scripts and calculations in the file. Destroyed when the file is closed. Not shared across files in a solution. |
| Let Variable (`~`)     | A variable scoped to a single `Let()` expression. Exists only during evaluation of that expression. The `~` prefix is a naming convention, not a FileMaker-enforced scope.    |

**Note:** The `~` prefix for Let variables is a community convention (codified in this project's CODING_CONVENTIONS.md), not a syntactic requirement. FileMaker's Let() function will accept any valid variable name.

## Calculation Engine

| Term            | Definition                                                                                                                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Calculation     | An expression that evaluates to a value. Used in calculation fields, auto-enter options, script step parameters, conditional formatting, hide conditions, tooltips, and many other contexts. |
| Custom Function | A reusable, named calculation defined in Manage Custom Functions. Can accept parameters and call itself recursively. Not the same as a Get() function.                                       |
| Get() Function  | A family of built-in functions (e.g., `Get ( AccountName )`, `Get ( FoundCount )`, `Get ( LastError )`) that return information about the current environment, session, or state.            |
| GetField()      | A function that returns the value of a field specified by name (as a string), enabling dynamic field references.                                                                             |
| Evaluate()      | A function that parses and evaluates a string as a calculation at runtime. Powerful but opaque to static analysis.                                                                           |
| ExecuteSQL()    | A function that runs a SQL SELECT query against FileMaker tables. Ignores the current found set and layout context entirely. Uses the SQL-92 dialect with FileMaker-specific limitations.    |
| Let()           | A function that defines temporary variables within a calculation. Variables are evaluated sequentially and can reference earlier variables in the same Let block.                            |
| While()         | A function that performs iterative (looping) calculation without recursion. Available since FileMaker 18.                                                                                    |
| Case()          | A function that evaluates a series of conditions and returns the result paired with the first true condition.                                                                                |
| If()            | A calculation function (distinct from the If script step) that evaluates a condition and returns one of two results.                                                                         |
| List()          | An aggregate function that returns a return-delimited list of non-empty values. Can accept fields (aggregates across related or found set records), variables, or literal values.            |

## Relationships

| Term                 | Definition                                                                                                                                                                                                                                          |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Relationship Graph   | The visual workspace (Manage Database > Relationships tab) where table occurrences are placed and connected by relationships.                                                                                                                       |
| Relationship         | A connection between two table occurrences defined by one or more predicates (field comparisons). Controls which related records are accessible. A relationship connects exactly two TOs.                                                           |
| Predicate            | A single comparison criterion in a relationship (e.g., `Table1::id = Table2::id_Table1`). A relationship can have multiple predicates (all must be true).                                                                                           |
| Equi-join            | A relationship where the operator is `=`. The most common type.                                                                                                                                                                                     |
| Cartesian Join       | A relationship using the `×` (cross-product) operator. Every record on one side matches every record on the other. Often used with global fields for utility relationships. Does not require an index.                                              |
| Self-Join            | A relationship from a table occurrence to another occurrence of the same base table. Used for hierarchies, sequencing, and same-table lookups.                                                                                                      |
| Allow Creation       | A relationship option that permits creating related records by entering data in an empty portal row or a related field on the layout.                                                                                                               |
| Delete Related       | A relationship option that cascading-deletes related records when the parent record is deleted.                                                                                                                                                     |
| Sort Related Records | A relationship option that controls the default sort order of related records as seen through that TO.                                                                                                                                              |
| Anchor-Buoy          | A relationship graph methodology where each base table has one "anchor" TO (used by layouts) with chains of "buoy" TOs branching off it. Keeps the graph organized and prevents ambiguous paths. Not a FileMaker feature — a community methodology. |

## Security

| Term                      | Definition                                                                                                                                                                                                                                                                          |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Account                   | A set of credentials (account name + password, or external authentication) that grants access to a file.                                                                                                                                                                            |
| Privilege Set             | A named collection of permissions (record access, layout access, script access, extended privileges, etc.) assigned to one or more accounts. Security is governed by privilege sets, not layouts.                                                                                   |
| Extended Privilege        | A keyword-based permission that controls access to specific features: `fmapp` (FileMaker Pro access), `fmwebdirect` (WebDirect), `fmrest` (Data API), `fmreauthenticate` (idle timeout), and others. Extended privileges enable features but do not grant data access on their own. |
| Record-Level Access (RLA) | Per-record security defined by a boolean calculation on each privilege set. Allows restricting view, edit, create, and delete on a record-by-record basis.                                                                                                                          |
| Full Access               | The built-in privilege set with unrestricted permissions. At least one account must have Full Access.                                                                                                                                                                               |
| Run with Full Access      | A script option that elevates the script's privilege to Full Access regardless of the current user's account, for the duration of that script only.                                                                                                                                 |

## Value Lists

| Term                   | Definition                                                                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Value List             | A named list of values used by fields (pop-up menus, radio buttons, checkboxes, drop-down lists) and by the Sort step.                                           |
| Custom Value List      | A value list with manually entered, static values.                                                                                                               |
| Field-Based Value List | A value list that draws values dynamically from a field. Can include all values or only related values. Can optionally show a second field and sort differently. |

## Custom Menus

| Term            | Definition                                                                                                                                           |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Custom Menu     | A developer-defined menu that replaces or extends a default FileMaker menu. Each menu item can be mapped to a script, a default command, or nothing. |
| Custom Menu Set | A collection of custom menus that replaces the entire menu bar. Can be assigned to specific layouts or installed by script.                          |

## Data Interchange Formats

| Term                         | Definition                                                                                                                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| fmxmlsnippet                 | The XML format used by FileMaker's clipboard for scripts, script steps, layout objects, custom functions, and other schema elements. The primary input/output format for this project. |
| Save a Copy as XML           | A FileMaker feature that exports the entire file's schema (tables, fields, relationships, scripts, layouts, etc.) as a single XML document. Structurally different from fmxmlsnippet.  |
| DDR (Database Design Report) | An HTML or XML report of a file's schema, generated from Manage Database. Now largely superseded by Save a Copy as XML.                                                                |

**Note:** fmxmlsnippet and Save a Copy as XML are structurally different formats. This project uses fmxmlsnippet as its output format and Save a Copy as XML as an input for understanding an existing solution.

## Hosting & Deployment

| Term                | Definition                                                                                                                                                                             |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FileMaker Server    | Server software that hosts `.fmp12` files for multi-user access. Provides scheduling, backups, Data API, WebDirect, and server-side scripting.                                         |
| FileMaker Cloud     | Claris-managed cloud hosting for FileMaker files. Integrates with Claris ID for authentication.                                                                                        |
| FileMaker Go        | The iOS/iPadOS client for accessing hosted or local FileMaker files. Supports device-specific features (GPS, camera, signatures, etc.).                                                |
| FileMaker WebDirect | Browser-based access to hosted files. Renders layouts in HTML5 without requiring FileMaker Pro on the client.                                                                          |
| FileMaker Data API  | A REST API exposed by FileMaker Server/Cloud for CRUD operations, script execution, and container data access. Requires the `fmrest` extended privilege.                               |
| OData               | A read-only REST-based protocol supported by FileMaker Server for exposing FileMaker data to external consumers.                                                                       |
| Session             | The period from when a user opens a hosted file until they close it. Global fields and global variables (`$$`) are session-scoped — their values do not persist once the session ends. |
| Schedule            | A server-defined task that runs a script, backup, or message at specified times or intervals.                                                                                          |

## Transactions

| Term               | Definition                                                                                                                                                                                                        |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Transaction        | A group of record changes that are committed or reverted as a single atomic unit. FileMaker has implicit single-record transactions and, since version 2024, explicit multi-record transactions via script steps. |
| Open Transaction   | Script step that begins an explicit transaction. All subsequent record changes are held in a pending state. Scoped to one session and one file — cannot span multiple files.                                      |
| Commit Transaction | Script step that commits all pending changes in the current transaction as an atomic unit. Not the same as committing a record.                                                                                   |
| Revert Transaction | Script step that discards all pending changes in the current transaction.                                                                                                                                         |

**Note:** Prior to explicit transactions, developers simulated multi-record atomicity using record-level undo loops or staging tables.

## AI & Machine Learning (FileMaker 2024+)

| Term                | Definition                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AI Account          | A configuration linking FileMaker to an AI model provider (OpenAI, Anthropic, custom endpoint). Defined via Configure AI Account script step.          |
| RAG Account         | A configuration linking FileMaker to a retrieval-augmented generation service. Defined via Configure RAG Account.                                      |
| Model Configuration | Settings for a machine learning or AI model (model name, temperature, etc.) defined via Configure Machine Learning Model or Configure Prompt Template. |
| Embedding           | A vector representation of text, generated by Insert Embedding or Insert Embedding in Found Set, used for semantic search and similarity matching.     |
| Semantic Find       | A find operation that matches records by meaning rather than exact text, using embeddings.                                                             |

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
