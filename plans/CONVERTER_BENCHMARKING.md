# Converter Benchmarking Guide

Reference for measuring and validating the Python converters documented in `agent/docs/CONVERTERS.md`.

---

## Converters Under Test

| # | Script | Conversion | Location |
|---|--------|-----------|----------|
| 1 | `fm_xml_to_snippet.py` | SaXML → fmxmlsnippet | `agent/scripts/` |
| 2 | `snippet_to_hr.py` | fmxmlsnippet → HR | `agent/scripts/` |
| 3 | `saxmlpreview.py` | SaXML → HR | `.claude/skills/script-preview/scripts/` |

## Performance Profile

### Where time is spent

The converters are fast. On a corpus of ~1,400 scripts (25 MB, ~58K steps), all three finish in under 1 second in-process. The time breakdown for the largest files (~700 KB, ~170 steps):

| Component | Time | % | Optimizable? |
|-----------|------|---|-------------|
| XML parsing (C-level expat) | ~7ms | 70% | No — this is compiled C code |
| Translator logic (per-step) | ~2.5ms | 24% | Marginal gains only |
| String escaping | ~0.5ms | 5% | Fast-path check helps slightly |
| Output assembly (join) | ~0.01ms | <1% | Already optimal |

### Subprocess vs in-process

When invoked via `subprocess.run()` (the normal CLI path), Python interpreter startup adds ~30ms per invocation. This dwarfs the actual conversion time:

| Mode | Avg per file | Bottleneck |
|------|-------------|-----------|
| Subprocess (CLI) | 30–42ms | Python startup + imports |
| In-process (module import) | 0.1–2.5ms | XML parsing |

For benchmarking the converter code itself, always measure **in-process** to isolate conversion logic from interpreter overhead. Use subprocess timing only when measuring real-world CLI latency.

### In-process benchmarking pattern

```python
import importlib.util, sys, time, statistics
from pathlib import Path

sys.path.insert(0, REPO_ROOT)

# Load module once
spec = importlib.util.spec_from_file_location(
    "fm_xml_to_snippet",
    "agent/scripts/fm_xml_to_snippet.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Time the conversion function directly
timings = []
for _ in range(N):
    start = time.perf_counter()
    result = mod.translate_script(Path(input_path))
    timings.append(time.perf_counter() - start)

median_ms = statistics.median(timings) * 1000
```

For `snippet_to_hr`, call `mod.snippet_to_hr(xml_string)` (importable function).
For `saxmlpreview`, call `mod.render_step(step_element)` per step (no single entry point that returns a string — the `convert()` function prints to stdout).

## Selecting a Test Corpus

Pick scripts spanning multiple size tiers for meaningful benchmarks:

| Tier | Size range | Purpose |
|------|-----------|---------|
| XS | < 5 KB | Edge cases, single-step scripts |
| M | 5–50 KB | Typical working scripts |
| L | 50–100 KB | Complex business logic |
| S (stress) | > 100 KB | Worst-case performance |

Source files: `agent/xml_parsed/scripts/`. Use 2–3 files per tier across multiple solutions. Sort by file size to find candidates:

```bash
find agent/xml_parsed/scripts/ -name "*.xml" -exec wc -c {} + | sort -rn | head -20
```

## Validation

### Automated checks (run after every conversion)

1. **XML well-formedness** — parse `fm_xml_to_snippet` output with `ET.fromstring()`
2. **Step catalog coverage** — extract all `<Step>` `name`/`id` attributes and verify against `agent/catalogs/step-catalog-en.json`
3. **Zero errors on full corpus** — run all ~1,400 scripts through each converter; any crash or exception is a regression

### Ground truth validation

SaXML (from FileMaker's Save a Copy as XML) is the only machine-exported ground truth. The other two formats must be captured manually from Script Workspace:

| Format | How to capture |
|--------|---------------|
| **HR text** | Select all steps in Script Workspace → copy (via MBS plug-in or manual) |
| **fmxmlsnippet** | Select all steps in Script Workspace → `python3 agent/scripts/clipboard.py read output.xml` |

#### MBS plug-in artifacts

When using the MBS plug-in to copy HR text from Script Workspace, be aware:

- **Blank lines** — MBS outputs `#` (hash only) where Script Workspace actually displays an empty line. Normalize standalone `#` lines to empty lines when comparing.
- **Trailing whitespace** — editors may strip trailing spaces from MBS output. The `# ` (hash + space) that MBS uses for blank lines may become just `#`.

#### Known SaXML-to-clipboard divergences

These are inherent differences between what SaXML stores and what FileMaker puts on the clipboard. They are not converter bugs:

| Difference | Detail |
|-----------|--------|
| Function name casing | SaXML may store `CurrentTimeStamp` where clipboard has `CurrentTimestamp`. FM is case-insensitive for function names. |
| Em dash encoding | SaXML stores `&#x2014;` (XML entity); clipboard stores the raw `—` character. |
| Import Records profile | Complex `<Profile>` and `<InputField>` structures in Import Records steps are not fully represented in SaXML ParameterValues. |
| Show Custom Dialog InputFields | Dialog input field definitions appear in clipboard XML but are not present in SaXML ParameterValues. |
| Go to Layout by calculation | SaXML uses `LayoutNumberByCalc` / `LayoutNameByCalc`; clipboard uses `SelectedLayout` with a nested `<Layout>` calc. |
| Close Window current | SaXML stores `type="current"` (lowercase); clipboard uses `<Window value="Current"/>` (capitalized). |

## Optimization Guidance

### What NOT to try

These approaches were benchmarked and found slower or equivalent:

| Approach | Result |
|----------|--------|
| `str.translate()` for XML escaping | 35× slower than chained `.replace()` |
| `xml.etree.ElementTree.iterparse` | 17% slower than `ET.parse()` (Python event overhead) |
| Pre-read file bytes + `ET.fromstring()` | No gain (file I/O is 0.3ms vs 7ms parse) |
| `io.StringIO` buffer for output | 47% slower than list + `'\n'.join()` |
| `re.sub()` for whitespace collapse | 5× slower than `split()` + `join()` |
| Pre-building param dict per step | Max 5 params per step — linear scan is already fast |

### What does help

- **Fast-path checks** — for functions like `escape_xml`, check if the input contains any special characters before doing replacements. Most FM script text is clean.
- **Case-insensitive comparisons** — SaXML attribute values may have unexpected casing (e.g., `type="current"` vs `type="Current"`). Use `.lower()` when matching.
- **Catalog-driven generic fallback** — handles all step types without per-step code. Keep hand-coded translators only for structurally unique steps.

### The hard wall

XML parsing via expat (the C parser behind `xml.etree.ElementTree`) accounts for 70% of conversion time and cannot be optimized from Python. The only ways past this wall would be:
- Using `lxml` (C library, not stdlib — violates the stdlib-only constraint)
- Rewriting the converter in a compiled language
- Caching parsed trees (only helps if converting the same file multiple times)

None of these are worth pursuing given that the full corpus converts in under 1 second.

## HR Accuracy Reference

### Three HR sources, three behaviors

| Aspect | saxmlpreview | snippet_to_hr | fm-xml-export-exploder |
|--------|-------------|--------------|------------------------|
| Input format | SaXML | fmxmlsnippet | SaXML |
| Calc display | Single line (collapses whitespace) | Multi-line (preserves formatting) | Multi-line (each line separate) |
| Set Variable | `Value:` prefix | `Value:` prefix | No prefix |
| Exit Script | `Text Result:` label | `Text Result:` label | Varies |
| Disabled step prefix | `// ` | `// ` | `// ` |
| Blank lines | Empty line | Empty line | Empty line |
| Doc blocks | Collapsed to single line | Multi-line with continuation | Multi-line (each line separate) |

**Script Workspace ground truth:**
- Calculations display on a **single line** regardless of how they're stored in XML
- Long values are truncated with `…`
- Blank lines are **empty**, not `#`
- Set Variable shows `Value:` prefix
- Exit Script shows `Text Result:` label
