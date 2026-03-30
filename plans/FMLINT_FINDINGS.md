# FMLint — Critical Findings

Post-implementation findings from building and testing FMLint against the agentic-fm project and 600 real-world FM Quickstart scripts. This document captures what the original plan got right, what changed during implementation, and the hard-won lessons that should inform future work.

---

## Plan vs Reality

### What the plan got right

- **Dual-format architecture** (XML + HR with shared rule logic) worked exactly as designed. The `formats/` parsers feed normalized data into rules that implement both `check_xml` and `check_hr`.
- **Three-tier progressive enhancement** (offline → context → live FM) maps cleanly to real usage. The auto-detection works.
- **Rule registry with decorator pattern** is clean and extensible. Adding a new rule is one decorated class.
- **Step catalog as the canonical reference** for step name validation (S008) was the right call over the old snippet_examples approach.

### What changed significantly

1. **Config-driven rules replaced hardcoded conventions.** The original plan baked coding conventions (variable naming, operator style, doc keywords) into the rule code. Developer feedback made clear that different FM teams have different standards. Every rule is now parameterized via `fmlint.config.json` — variable naming patterns are regex, doc keywords are strings, thresholds are numbers. This was not in the original plan and is arguably the most important architectural decision.

2. **N001 (Unicode operators) disabled by default.** The plan treated `≠ ≤ ≥` as the correct style. In practice, both ASCII and Unicode operators are valid FM. This is a filemakerstandards.org preference, not a correctness issue. Teams that want it can opt in.

3. **validate_snippet.py became a shim, not a rewrite.** The plan called for making it a thin wrapper. During implementation I initially preserved it unchanged (wrong — the plan was right). It was later converted to a proper shim that delegates to FMLint with the legacy rule set disabled to preserve output compatibility.

4. **The TypeScript linter needed full multiline statement merging.** The plan assumed the TS side would be a simple subset of rules. In practice, real FM scripts have multiline Insert Text steps with embedded JavaScript, CSS, and HTML. Without the same multiline merge logic the Python HR parser uses, the TS linter produced hundreds of false positives on continuation lines.

5. **`diagnostics.ts` had to be fully removed, not just supplemented.** The plan said "replaces current diagnostics.ts" but didn't explicitly call for deletion and consumer rewiring. Two import sites (`filemaker-script.ts` and `EditorPanel.tsx`) needed to be updated — this was missed in the initial implementation and caught in review.

---

## Critical Technical Findings

### Multiline statement merging is essential for HR linting

FileMaker's human-readable format allows bracket content to span multiple lines:

```
Insert Text [ Target: PREFERENCES::calendar.js ; "$(document).ready(function() {
    $('#calendar').fullCalendar({
      aspectRatio: ratio,
    });
});" ]
```

Without merging these into a single logical line before analysis, every continuation line gets parsed as if it were a step name. This caused:
- **S008**: 202 false positives (raw JS/CSS text flagged as "unknown step")
- **C001**: 26 false positives (odd quote counts from partial string fragments)
- **B005**: 6 false positives (`?` in JavaScript ternary operators)

Both the Python `hr_parser.py` and the TypeScript rules now implement bracket-depth-aware multiline merging. The Python parser does it once at parse time. The TypeScript rules each call a shared `mergeMultilineStatements()` helper.

**Lesson:** Any tool that processes HR format scripts must merge multiline statements as a preprocessing step, or it will be unreliable on real-world scripts.

### S008 requires uppercase filtering for HR format

After multiline merge, some text fragments can survive as parsed step names — embedded JS/CSS content that happens to be on its own line. All FM step names start with an uppercase letter, so an uppercase filter eliminates these false positives without affecting real step validation. Both the Python and TypeScript S008 implementations apply this filter.

The initial S008 parity gap (31 Python hits, 0 TypeScript) was misdiagnosed as a multiline merge difference. Root cause analysis revealed the merge algorithms were identical — the divergence was this post-merge filter, which the TS implementation had from the start and the Python side lacked. Python's `check_hr` now applies `if not name[0].isupper(): continue` to match.

Note: Python intentionally still checks disabled (`//`) step names, which the TS `isSkippable()` skips — Python's behavior is more correct (disabled steps should still have valid names).

### Insert Text and similar steps are not calculations

Steps like `Insert Text`, `Show Custom Dialog`, `Send Mail`, `Set Web Viewer`, and `Open URL` have bracket content that is literal text — URLs, HTML, JavaScript, SQL, etc. Rules that analyze calculation expressions (C001, C002, B005, N001) must skip these steps.

The `NON_CALC_STEPS` set is defined in `calculations.py` and mirrored in the TypeScript `calculations.ts`:

```
Insert Text, Insert File, Insert Picture, Insert Audio/Video,
Insert PDF, Insert From URL, Insert From Device,
Show Custom Dialog, Send Mail, Send Event,
Set Web Viewer, Export Field Contents,
Open URL, Open File, Dial Phone
```

**Risk:** This set was built from observed false positives on the FM Quickstart corpus, not from a systematic audit of all FM steps. Steps with non-calculation bracket content that aren't listed here (e.g., `Execute SQL` has SQL expressions, not FM calculations) will produce false positives on C001/C002/B005. The set should be extended as new false positive sources are encountered. A definitive list could be derived from the step catalog by flagging steps whose bracket content is documented as literal text rather than a FM calculation.

**Lesson:** Not all bracket content in HR format is a FM calculation. Calculation-analysis rules must be aware of step type.

### FileMaker repetition variables need special handling

FM supports repetition variables like `$var[1]`, `$$global[3]`. The original N002 regex patterns didn't account for the `[N]` suffix, causing 3,926 false positives on the FM Quickstart solution (83% of all warnings). Adding `(?:\[\d+\])?` as an optional suffix reduced N002 hits to 667 — all genuine convention violations.

The `allow_repetition_suffix` config flag controls this behavior so it can be disabled if a team doesn't use repetitions.

### Custom functions dominate C003 noise

C003 (known function names) flagged 1,212 warnings on FM Quickstart — nearly all custom functions like `fmErrorMessage`, `getLayoutID`, `dateFormatForQBO`. Every real FM solution has custom functions that the built-in list can't know about.

The `extra_known_functions` config array solves this: a team adds their custom function names once and the noise disappears. This is the single most impactful config setting for real solutions.

However, requiring manual configuration is friction. The linter could auto-discover custom functions from `xml_parsed/custom_functions_sanitized/` when that data is available (see Known Gaps, item 1). This would eliminate nearly all C003 noise without any config.

### Config must be shared between Python and TypeScript

The original plan had separate config systems for Python (file-based) and TypeScript (in-memory defaults). This meant N001 was disabled in Python but active in TypeScript — the same file would get different results depending on which linter ran.

The fix: the webviewer server exposes `GET /api/lint-config` which loads and merges the same config files the Python side reads. The TypeScript `diagnostics-adapter.ts` fetches this on init. One config file, one set of rules, both environments.

### R001 false positives on multi-layout scripts

CONTEXT.json is scoped to a single layout. Scripts that navigate to a different layout with `Go to Layout` and then reference fields from that layout's table produced false R001 warnings — those fields aren't in the context snapshot.

R001 now detects `Go to Layout` steps that navigate away from the current CONTEXT.json layout and stops validating field references after that point. R009 (previously a stub) emits an INFO diagnostic at the scope boundary explaining that field references past this point cannot be validated, with a fix_hint suggesting Push Context on the target layout.

### B001 (error-capture-paired) redesigned for real-world usage

The original B001 used a step-count lookahead (default: 10 steps) to check that `Set Error Capture [On]` was followed by `Get(LastError)`. This produced false positives in two common patterns: (1) error capture at the top of a script with error checks many steps later, and (2) intentional silent failure where the developer enables error capture specifically to suppress dialogs with no intent to check.

B001 now scans the entire script for any `Get(LastError)` call. It only fires when error capture is enabled but zero error checks exist anywhere. Severity was changed from WARNING to INFO — error capture usage varies widely across FM teams and silent suppression is a valid pattern. The message explicitly acknowledges this, asking the developer to verify the omission is deliberate rather than asserting it's a bug.

### B002 (commit-before-nav) is a blunt instrument

B002 flags any script that has `Go to Layout` but zero `Commit Records/Requests` steps. This is directionally correct but too coarse — it fires on utility scripts that navigate to data-entry layouts, card windows, report layouts, etc., where there's no active record edit. It produced 137 hits on FM Quickstart, most of which are noise.

A smarter version would check whether the script modifies records (Set Field, New Record, etc.) before the navigation. For now it's INFO severity and can be disabled.

---

## Testing Methodology

### FM Quickstart as test corpus

The FM Quickstart solution (600 scripts, 1–1021 lines each) served as the stress test. Key scripts:

| Script | Lines | What it tests |
|--------|------:|---------------|
| File - Open | 1,021 | Embedded JS/CSS in Insert Text, deep nesting, multiline statements |
| Quickbooks - Gather Data Variables | 379 | Heavy Set Variable usage, repetition variables, custom functions |
| Quote - Create Order | 273 | Business logic, error handling, transactions, navigation |
| Work Order - Delete Portal Row | 25 | Baseline — minimal script |

### Three-pass test pattern

1. **Full rules** — see everything the linter catches
2. **Structure + calculations only** — disable convention rules to focus on real errors
3. **JSON aggregate** — count rule hits across all 600 scripts to find noise vs signal

### Python/TypeScript parity testing

Both implementations were run against all 600 scripts. Results for overlapping rules must match:

| Rule | Python | TypeScript |
|------|-------:|-----------:|
| D001 | 33 | 33 |
| C001 | 2 | 2 |
| S005 | 1 | 1 |
| S008 | 0 | 0 |
| Errors | 3 | 3 |

C002 (unbalanced parens) has been ported to TypeScript and should be added to future parity runs.

---

## Architecture Decisions Worth Preserving

### Why config is JSON, not Python/TOML

The project requires stdlib-only Python (no pip dependencies). Python's `tomllib` is only available in 3.11+. JSON is universally supported, readable by both Python and TypeScript, and editable by developers who aren't programmers.

### Why config has load-time validation

The config system validates rule IDs, severity strings, boolean fields, numeric thresholds, regex patterns (N002), and list fields (C003) at load time via `_validate_rules_config()`. Warnings are stored on `LintConfig.config_warnings` and surfaced by the CLI to stderr. This catches typos (e.g., `"S00l"` instead of `"S001"`, `"warnnig"` instead of `"warning"`) before they silently cause rules to use defaults instead of the intended override.

### Why the TS linter is a subset, not a full port

The TypeScript linter runs in the browser on every keystroke (debounced 300ms). It must be fast and small. Only tier 1 rules that provide immediate feedback are implemented: block pairing (S005/S006/S007), known steps (S008), unclosed strings (C001), unbalanced parens (C002), purpose comment (D001), and unicode operators (N001).

Tier 2 (references) and tier 3 (live eval) require server-side data (CONTEXT.json, OData) and are accessed via the companion server's `POST /lint` endpoint when needed.

### Why rules self-register via decorator

The `@rule` decorator pattern means adding a rule is a single file with a single class. No central manifest to update. The `rules/__init__.py` imports all modules to trigger registration. This is the same pattern used for step converters in the webviewer (`step-registry.ts`).

The registry includes a dedup guard (`_registered_ids` set) to prevent double-registration on module reload, and a `clear_registry()` function for test isolation.

### Why the linter doesn't modify CODING_CONVENTIONS.md

The config file and the conventions doc are intentionally separate systems. `CODING_CONVENTIONS.md` is documentation for humans and agents — it describes intent and rationale. `fmlint.config.json` is machine-readable enforcement. They may diverge: a team might document conventions they aspire to but only enforce a subset via the linter.

---

## Known Gaps and Future Work

### High impact

1. **C003 auto-discovery of custom functions.** Instead of requiring manual `extra_known_functions` config, the linter could auto-discover custom functions from `xml_parsed/custom_functions_sanitized/` when that data is available. C003 produced 1,212 warnings on FM Quickstart — nearly all custom functions. Auto-discovery would eliminate this noise without any configuration, making C003 useful out of the box for established solutions.

2. **B002 record-modification awareness.** B002 fires on any script with `Go to Layout` but no `Commit Records/Requests`. A smarter version would check whether the script actually modifies records (Set Field, New Record, Delete Record, etc.) before the navigation. This would eliminate the 137 false positives seen on FM Quickstart.

3. **NON_CALC_STEPS completeness.** The exclusion set for calculation-analysis rules was built from observed false positives, not a systematic audit. Steps like `Execute SQL` (bracket content is SQL, not FM calc) may produce false positives on C001/C002/B005 and should be added as they're encountered. A definitive list could be derived from the step catalog.

### Medium impact

4. **TypeScript rule coverage.** The TS linter doesn't implement N002, N003–N007, B001–B005, D002–D003, or C003. These are available server-side via `POST /lint`. The next most impactful TS addition would be N002 (variable naming) for immediate convention feedback during editing.

5. **No auto-fix capability yet.** The `fix_hint` field is informational only. A future version could support `--fix` to auto-apply safe fixes (e.g., replacing `<>` with `≠` for N001).

### Low impact (stubs)

6. **B003 (parameter validation)** is a stub. A real implementation would track whether `Get(ScriptParameter)` is assigned to a variable and then validated (e.g., `IsEmpty`, `JSONGetElement` type checking) before use.

7. **C005 (live eval warnings)** is a stub. Could detect deprecated functions, implicit type coercions, or context-dependent evaluation differences when AGFMEvaluation returns success but with caveats.
