# Silent-discard params — the full reference (enforced by fmlint X001–X003)

FileMaker's fmxmlsnippet parser **silently discards** child elements whose tag name does not match what the step parser expects. The step imports successfully, but the parameter quietly falls back to its default value. The symptom is invisible at the XML level and only manifests at runtime (loops that never advance, windows that open wrong, script references that don't resolve).

**These traps are machine-enforced**: fmlint's param-fidelity family (`agent/fmlint/rules/param_fidelity.py`) validates every `<Step>`'s child elements against the step catalog (`params[].xmlElement`, `discriminator`). Running `python3 -m agent.fmlint` (mandatory step 6 of the core workflow) catches them before paste. This document is the detailed reference behind those rules.

| Rule | What it catches |
|------|-----------------|
| **X001** | Child element not recognized by the step's catalog params (silently discarded) |
| **X002** | Param present without its governing discriminator (silently ignored) |
| **X003** | Known combinations: Card without `Styles` bitmask; `FileReference` nested/incomplete |

---

## X001 — Parameter element names must match the catalog exactly

- ❌ `<Step ... name="Set Error Capture"><State state="True"/></Step>` — wrong tag, parameter ignored → `Set Error Capture` ends up OFF (default).
- ✅ `<Step ... name="Set Error Capture"><Set state="True"/></Step>` — matches catalog's `xmlElement: "Set"`.

Same rule applies to `Allow User Abort` (also `<Set state="…"/>`) and any step with boolean parameters. Always check the catalog's `params[].xmlElement` before hand-writing a step.

### Go to Record/Request/Page — `<RowPageLocation>` and `<Exit>`

The common-sense tag names `<Option value="First"/>` and `<ExitAfterLast state="True"/>` are **silently discarded** — the step imports with **no parameters**, producing a Go to Record that does nothing. Loops go infinite or iterate once without advancing.

Correct child elements:

- `<RowPageLocation value="First|Last|Previous|Next|By Calculation"/>` — **NOT** `<Option>`.
- `<Exit state="True|False"/>` — "Exit after last". **NOT** `<ExitAfterLast>`.
- `<NoInteract state="True|False"/>` — "With dialog: off".

```xml
<!-- First record, no dialog -->
<Step enable="True" id="16" name="Go to Record/Request/Page">
  <NoInteract state="True"/>
  <RowPageLocation value="First"/>
</Step>

<!-- Next record, exit loop after last -->
<Step enable="True" id="16" name="Go to Record/Request/Page">
  <NoInteract state="True"/>
  <Exit state="True"/>
  <RowPageLocation value="Next"/>
</Step>
```

## X002 — Discriminator-governed params

### Go to Layout

Step id `6`; the destination enum is `LayoutDestination` and the `<Layout>` ref is its **sibling**, governed by it:

```xml
<!-- Layout by literal name from list -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="SelectedLayout"/>
  <Layout id="28" name="Clientes"></Layout>
</Step>

<!-- Layout by name calculated at runtime -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="LayoutNameByCalc"/>
  <Layout>
    <Calculation><![CDATA[$LayoutName]]></Calculation>
  </Layout>
</Step>

<!-- Return to the layout where the script started -->
<Step enable="True" id="6" name="Go to Layout">
  <LayoutDestination value="OriginalLayout"/>
</Step>
```

Prefer `OriginalLayout` over capturing `Get(LayoutName)` at the start and restoring manually. Note `<Layout>` must use explicit open/close tags — the self-closing form is dropped on paste.

### New Window — explicit `<LayoutDestination>` before `<NewWndStyles>`

Without `<LayoutDestination value="SelectedLayout"/>` (or `LayoutNameByCalc`, etc.) as the **first** child of the Step, FM defaults to `CurrentLayout` and **silently ignores** the `<Layout id name>` even when present and well-formed. The sanitized output shows `Layout: ""` (empty).

```xml
<Step enable="True" id="122" name="New Window">
  <LayoutDestination value="SelectedLayout"/>
  <NewWndStyles .../>
  <Name><Calculation><![CDATA["..."]]></Calculation></Name>
  <Layout id="X" name="LayoutNameReal"></Layout>
</Step>
```

## X003 — Known silent-discard combinations

### New Window with `Style="Card"` requires the `Styles` bitmask

Without the `Styles="…"` attribute, FileMaker ignores `Style="Card"` and opens the window as `Document` regardless of the other style flags. The `Styles` attribute is a bitmask encoding the same flags numerically — it is what FM actually reads.

- ❌ `<NewWndStyles DimParentWindow="Yes" Toolbars="No" MenuBar="No" Style="Card" Close="Yes" Minimize="No" Maximize="No" Resize="No"/>` — opens as **Document**.
- ✅ Same + `Styles="3222339600"` — opens as **Card**.

Known values:
- `3222339600` — Card: DimParentWindow=Yes, Toolbars=No, MenuBar=No, Close=Yes, Minimize=No, Maximize=No, Resize=No.
- `3222274064` — Card without chrome Close (forces Cancel/Save buttons).
- `3606018` — Document with Close/Minimize/Maximize/Resize=Yes.

Reuse `Styles="3222339600"` verbatim for new Card selectors unless the flags actually differ.

### Perform Script cross-file — `<FileReference>` sibling with `<UniversalPathList>`

When `Perform Script` (step id 1) calls a script in another file, `<FileReference>` must be a **sibling** of `<Calculation>` and `<Script>` — NOT nested inside `<Script>` — and needs a `<UniversalPathList>` child with `file:<FilenameWithoutExtension>`.

- ❌ Nested inside `<Script>`, no UniversalPathList — FM imports the step but the reference does not resolve ("guión desconocido" in Script Workspace).
- ✅ Correct form:

```xml
<Step enable="True" id="1" name="Perform Script">
  <FileReference id="10" name="Controlador">
    <UniversalPathList>file:Borneo-Controller</UniversalPathList>
  </FileReference>
  <Calculation><![CDATA[$param]]></Calculation>
  <Script id="1363" name="ContactosClientes | Alta Modificar ContactoCliente {json}"/>
</Step>
```

The `FileReference id`/`name` match the external data source entry in the caller file (**File > Manage > External Data Sources…**). For same-file Perform Script, omit `<FileReference>` entirely.

---

## Provenance

These rules originated as prose "CRITICAL" blocks in `.claude/CLAUDE.md` (Taiko layer), distilled from real-world failures (Borneo 944.x among others). They were converted to fmlint enforcement in July 2026 so the linter catches them mechanically; this document preserves the full examples and context. If the upstream PR adopting the X-family rules is merged, this knowledge doc travels with it.
