# Analysis Performance Optimization Findings

Findings from the autoresearch-style optimization of `agent/scripts/analyze.py`, conducted 2026-03-29.

## Summary

Applied Karpathy's autoresearch methodology (single metric, iterative keep/revert, constrained edit surface) to optimize the solution analysis script. Achieved a **39% wall-clock reduction** on UnnamedSolution (1.19s to 0.72s) and **34%** on SmallSolution (0.64s to 0.42s).

---

## Methodology: Autoresearch Applied to Script Optimization

### Core Principles (from Karpathy's autoresearch)

1. **Single metric**: wall-clock time. No subjective judgments.
2. **Fixed evaluation**: same command, same solutions, median of 3 runs.
3. **Correctness gate**: SHA256 hash of normalized JSON output must match baseline. Any output change = automatic REVERT regardless of speed gain.
4. **One change at a time**: each optimization is independently testable.
5. **Keep or revert**: if faster AND correct, keep. Otherwise revert.
6. **Human sets direction, agent does empirical work**: the agent iterates; the human reviews.

### The Benchmark Harness (`bench_analyze.py`)

The harness (`agent/scripts/bench_analyze.py`) implements the loop:

```
--baseline    Capture reference measurements (time + output hash)
--check       Run and compare against baseline (KEEP/REVERT verdict)
--update      Accept a known-good output change and reset baseline
--label       Tag each attempt for the JSONL log
```

**Critical detail: output normalization.** The JSON contains a `generated_at` timestamp that changes every run. The harness strips this before hashing. Any other volatile fields (paths, dates) would need similar treatment.

**Gotcha discovered:** The harness must run `--update` when a change intentionally improves output correctness (e.g., fixing a script name from `HTTP ( _request} )` to `HTTP ( {request} )`). The baseline hash is a snapshot of the _old_ behavior, not a definition of correctness.

---

## Profiling Results (Baseline)

### Tool: cProfile + manual section timing

```python
python3 -c "
import time, sys
# ... manually wrap each phase with time.monotonic() ...
"
```

cProfile gave function-level granularity (799,800 calls, 3,557 file opens) but manual section timing was more actionable for identifying which _phase_ was slow.

### Baseline Phase Breakdown (UnnamedSolution: 696 scripts, 610 CFs)

| Phase            | Time   | %   | Root Cause                                       |
| ---------------- | ------ | --- | ------------------------------------------------ |
| Custom functions | 0.273s | 24% | O(n^2) dep check + no memoization in chain depth |
| Health metrics   | 0.213s | 19% | Re-reads all 696 script files                    |
| Integrations     | 0.202s | 18% | Re-reads all 696 script files                    |
| Layouts          | 0.196s | 17% | Re-reads all 696 script files                    |
| Scripts analysis | 0.179s | 16% | First read of all 696 script files               |
| Everything else  | 0.068s | 6%  | Index loading, data model, naming, multi-file    |

**Key insight:** 4 of 8 phases independently called `find_script_files()` and re-read every file. For 696 scripts, that's 2,784 redundant file opens. File I/O was 40% of total execution time despite only 1.1s total.

---

## Optimizations: What Worked

### 1. Script File Cache (biggest win: -49% on I/O phases)

**Pattern:** Read-once, share-many. A single `load_script_cache()` function reads all script files once into a list of dicts, pre-computes common derived data (line counts, regex matches, emptiness), and passes the cache to all four consumers.

**Before:** Each phase opens/reads/closes 696 files independently = 2,784 file opens.
**After:** 696 file opens total. Phases that previously took 0.2s each now take 0.001-0.01s.

**Architectural lesson:** When multiple analysis passes need the same source data, a shared cache is the single highest-impact optimization. The cache should preserve the original iteration order (list, not dict) to avoid changing output due to key collision when multiple files map to the same logical name.

### 2. Pre-extracted Metadata (incremental win on top of cache)

During cache load, pre-compute everything that multiple consumers need:

- `calls`: `RE_PERFORM_SCRIPT.findall(text)` (used by scripts analysis)
- `layout_refs`: `RE_LAYOUT_REF.findall(text)` (used by layouts analysis)
- `has_insert_from_url`, `has_send_mail`, etc.: boolean flags (used by integrations)
- `is_empty`: boolean (used by health)

This means each regex runs exactly once per file, ever.

### 3. Memoized CF Chain Depth (fixed exponential complexity)

**Before:** `_chain_depth()` used `visited.copy()` on every recursive branch. For a function with 5 deps each having 5 deps, this creates 5^depth branches. Called 610 times with no caching.

**After:** Single `memo` dict. Two-state cycle detection (PENDING=-1, DONE=cached). Each function's depth computed exactly once = O(V+E).

```python
PENDING = -1
memo = {}

def _chain_depth(name):
    if name in memo:
        return max(memo[name], 0)  # PENDING -> 0 (cycle)
    if name not in functions:
        return 0
    memo[name] = PENDING
    deps = functions[name].get("dependencies", [])
    if not deps:
        memo[name] = 1
        return 1
    depth = 1 + max(_chain_depth(d) for d in deps)
    memo[name] = depth
    return depth
```

### 4. Single-Pass CF File Reading

Merged the two-pass pattern (pass 1: collect names from filenames, pass 2: read content) into a single-pass: collect names from `stem` (no I/O), store `(name, id, text)` tuples, then process.

### 5. Sorted Dependencies for Deterministic Output

The original code iterated `all_cf_names` (a `set`) which has non-deterministic order in Python. Dependencies were appended in whatever order the set gave them. This caused output hash mismatches between runs. Fix: `sorted()` the dependency list.

**Lesson:** Any analysis that iterates over sets and produces ordered output (JSON arrays) must sort explicitly.

---

## Optimizations: What Failed

### Token-Based CF Dependency Detection (REVERTED)

**Idea:** Replace O(n^2) substring checks with set intersection. Tokenize each function text into identifiers (`\b\w+\b`), intersect with the CF name set.

**Result:** 23% faster but lost 228 of 907 dependencies. Multi-word CF names and names that appear as substrings within identifiers were missed. Output hash mismatch = automatic REVERT.

**Lesson:** Python's `in` operator does substring matching, not word-boundary matching. Switching to token extraction changes semantics. For FileMaker CFs, many names like "TableName", "FieldName", "LayoutID" legitimately appear as substrings within other identifiers.

### Regex Alternation for CF Dependencies (REVERTED)

**Idea:** Build a compiled `re.compile('name1|name2|...')` alternation from all 610 CF names. Single `findall()` per function.

**Result:** Actually _slower_ (+2% for UnnamedSolution, +12% for SmallSolution) AND produced different output. The regex compilation cost for 610 escaped patterns exceeded the savings, and `findall` with overlapping patterns behaves differently than individual `in` checks.

**Lesson:** Regex alternation scales poorly with pattern count. For 610+ patterns, the compilation overhead dominates. Python's built-in `in` operator on strings is highly optimized (Boyer-Moore-Horspool) and hard to beat for simple substring existence checks.

### Hybrid Token + Substring Approach (REVERTED)

**Idea:** Use set intersection for single-word CF names (fast), substring check only for multi-word names (small set, usually empty for FM).

**Result:** Faster but different output. Even single-word names like "Bye" appear as substrings within "GoodBye" — the `in` operator matches them, token intersection does not.

**Lesson:** Any change to the matching semantics of `in` will change dependency graphs. The O(n^2) substring approach, while theoretically suboptimal, is the correct behavior and runs in ~0.3s which is acceptable.

---

## Status Output Design

### Human-Readable (default)

```
==> Analyzing solution: UnnamedSolution
  Loading script files......
    0.300s (696 items)
  Analyzing data model......
    0.001s
  ...
==> Analysis complete. (0.703s)
  Phase timing:
    index_loading................. 0.003s
    script_cache.................. 0.300s
    ...
```

### Machine-Readable (`--status-json`)

JSONL to stderr, one line per event:

```json
{"status": "phase_start", "phase": "script_cache", "t": 0.003, "label": "Loading script files..."}
{"status": "phase_end", "phase": "script_cache", "t": 0.303, "elapsed": 0.300, "items": 696}
{"status": "phase_complete", "phase": "complete", "t": 0.703, "phases": {"script_cache": 0.300, ...}}
```

**Design decisions:**

- Status goes to stderr, not stdout, so output files are unaffected.
- Each phase emits start/end pairs with wall-clock timestamps and elapsed durations.
- Item counts are included where meaningful (script count, CF count, layout count).
- The completion message includes a full phase timing dict.

---

## Remaining Bottlenecks

After optimization, the two dominant phases are:

| Phase            | Time  | What it does                         | Why it's slow                                 |
| ---------------- | ----- | ------------------------------------ | --------------------------------------------- |
| script_cache     | 0.30s | Read 696 files from disk             | I/O bound (696 opens, ~55% CPU idle)          |
| custom_functions | 0.30s | Read 610 CF files + O(n^2) dep check | I/O (610 opens) + CPU (372K substring checks) |

### Potential future optimizations

1. **Parallel file I/O** (`concurrent.futures.ThreadPoolExecutor`): Since the bottleneck is I/O wait (55% CPU idle), threading could overlap file reads. Expected ~30-40% reduction on cache loading. Adds stdlib dependency only.

2. **Persistent cache** (pickle/JSON): Cache the parsed script/CF data to disk. Invalidate by checking mtime of the `scripts_sanitized/` directory. Would make repeat runs near-instant (~0.05s) at the cost of stale data risk.

3. **Aho-Corasick for CF dependency matching**: The `pyahocorasick` library can match all 610 patterns simultaneously in O(n) where n = text length. But it's a non-stdlib dependency and the current 0.3s is acceptable.

4. **Incremental analysis**: Only re-analyze scripts/CFs that changed since last run. Requires storing previous state and diffing against current file mtimes.

5. **Lazy loading**: Don't read CF files until the custom_functions phase. Currently all script files are read upfront (good for the 4 consumers), but CF files are read separately. If CF analysis isn't needed, this I/O could be skipped.

---

## Key Lessons for Future Optimization Work

1. **Profile first, optimize second.** The manual section timing revealed that 4 phases were doing the same I/O — this wasn't visible from function-level profiling alone.

2. **The correctness gate is non-negotiable.** Three of five optimization attempts produced different output. Without the hash check, these would have silently shipped as "improvements."

3. **Set iteration order is non-deterministic.** Any code that iterates a `set` and produces ordered output must sort explicitly. This caused the most confusing debugging session (output "changed" between runs of the same code).

4. **Python's `in` operator is surprisingly fast.** For substring matching, it uses a variant of Boyer-Moore that's hard to beat with regex or tokenization. Don't assume algorithmic improvements will translate to wall-clock improvements for string operations.

5. **List vs dict for caches matters.** Switching from file-path iteration to dict-keyed iteration changed the script count from 696 to 695 (one script name collision). Using a list preserved the original per-file semantics.

6. **Test against multiple solutions.** UnnamedSolution (610 CFs, O(n^2) bottleneck) and SmallSolution (122 CFs, I/O bottleneck) have different profiles. An optimization that helps one may hurt the other.

7. **`--update` is part of the loop.** When a change intentionally corrects output (e.g., resolving script names through the index instead of parsing filenames), the baseline must be updated. The harness should distinguish "output changed, is it better or worse?" from "output corrupted."

---

---

## Multi-File Solution Analysis (2026-03-30)

### Problem Statement

FileMaker solutions often use a "data separation model" where a UI file references tables stored in a separate data file via external data sources (EDS). The analysis tool originally treated each file independently — the ERD, HTML graph, and JSON profile had no concept of which file owns a table or where relationships cross file boundaries.

### Architecture of a Multi-File FM Solution

A typical data separation model (4-file example):

```
UI File (Solution)
  ├─ Local tables: utility/UI (Globals, Defaults, Startup)
  ├─ 144 External TOs → data file via EDS "Cloud Data Source"
  ├─ 4 External TOs → document file via EDS "Solution_Doc"
  └─ EDS "Solution_Logic" → script execution only (0 TOs)

Data File (Solution_Data)
  ├─ 36 base tables (domain entities)
  ├─ 39 Local TOs (all @-prefixed)
  └─ Minimal startup scripts

Logic File (Solution_Logic)
  ├─ 4 local tables (Defaults, Startup)
  ├─ 34 External TOs → Solution_Data
  └─ Business logic scripts (server-side execution)

Doc File (Solution_Doc)
  ├─ 3 local tables (Documents)
  └─ No external data sources
```

**Key insight**: The EDS name often does NOT match the physical filename. A UI file's primary data source might be named "Cloud Data Source" but point to `file:Solution_Data.fmp12`. The mapping algorithm must not rely on name matching.

### Index Layer: table_occurrences.index

Added two columns to the TO index generated by `fmcontext.sh`:

```
# TOName|TOID|BaseTableName|BaseTableID|Type|DataSource
@Startup|1065089|Startup|129|Local|
Orders|1065136|Orders|157|External|Cloud Data Source
```

- **Type**: `Local` or `External` (from `@type` attribute on `<TableOccurrence>`)
- **DataSource**: name of the external data source (from `<DataSourceReference @name>`, empty for Local)
- **Backward compatible**: `_parse_index()` returns `""` for missing columns, so old 4-column indexes still work.

### EDS-to-Solution Mapping Algorithm

The mapping uses a multi-level resolution strategy, run from the perspective of one primary file:

**Level 1 — Literal path resolution** (deterministic, preferred):
- Parse each EDS XML's `<UniversalPathList>` for `file:` and `fmnet:` entries
- Strip `.fmp12` extensions and extract the bare filename
- Match against solutions that exist in `agent/context/`
- Example: `file:Solution_Data.fmp12` → `Solution_Data`

**Level 2 — Base table overlap** (heuristic fallback for variable-based paths):
- Only runs for EDS entries where the path is entirely `$$VARIABLE` with no literal fallback
- Groups the primary file's External TOs by their `DataSource` column
- Loads each candidate solution's local base tables (from TO index + fields index)
- Highest set intersection wins
- Example: SolutionApp's `$$DATA.FILEPATH` → overlap matching finds `SolutionData`

**Level 3 — Bootstrap chain trace** (not yet implemented):
- For variable-only paths, trace `OnFirstWindowOpen` trigger → startup script → `Set Variable` → custom function → filename
- Example: `$$DATA.FILEPATH` ← `DataFilename` CF ← returns `"SolutionData" & FMPFileExtension`
- This would resolve the mapping deterministically for solutions where Level 1 produces no match

### Critical Bug: Cross-Solution Contamination

**Symptom**: Analyzing a multi-file solution showed an unrelated solution name in its relationship graph legend. A table with a common name ("Startup") was attributed to the wrong solution.

**Root cause**: `detect_multi_file()` listed ALL solutions in the repo as candidates for correlation, not just those referenced by an EDS. The `data_source_map` was correctly narrowed, but `correlated_solutions` and the data loaded in `build_profile()` included every solution with a context directory. When `analyze_data_model()` added correlated tables to the graph, tables from unrelated solutions with matching names bled in.

**Fix**: After building `data_source_map`, narrow `correlated` to `sorted(set(data_source_map.values()))`. Only solutions that were actually matched via Level 1 or Level 2 are loaded.

**Lesson**: Any heuristic that scans the full repo for candidate matches must be scoped to the solution's actual EDS references. Base table IDs are file-specific (FM assigns sequential IDs per file) — name collisions like "Startup" are extremely common across unrelated solutions.

### EDS Path Patterns Observed

| Pattern | Example | Resolution |
|---------|---------|------------|
| `file:Name.fmp12` | `file:Solution_Data.fmp12` | Level 1: direct filename match |
| `file:Name` (no ext) | `file:Updater` | Level 1: direct filename match |
| `fmnet:/host/Name` | `fmnet:/server.filemaker-cloud.com/Solution_Data` | Level 1: extract after last `/` |
| `$$VARIABLE` only | `$$DATA.FILEPATH` | Level 2: base table overlap |
| Multi-line fallback | `$$VAR\nfile:Name.fmp12` | Level 1: parse each line, skip `$` lines |
| `$local_var` + `$$global` + `file:` | `$pfad\n$$EXTERN.PFAD\nfile:Solution` | Level 1: `file:Solution` matches |

**Key finding**: Most solutions include a `file:` literal as a fallback entry in the multi-line `UniversalPathList`, even when the primary connection uses a variable. This means Level 1 resolves the majority of EDS entries without any heuristics.

### Bootstrap Chain for Variable-Only Paths

When `UniversalPathList` contains only `$$VARIABLE` entries with no `file:` fallback, the variable is typically populated by a startup script:

1. A layout's `OnFirstWindowOpen` trigger fires a bootstrap script
2. The bootstrap script calls a subscript or custom function to determine the path
3. The custom function returns the filename (e.g., `"SolutionData" & FMPFileExtension`)
4. `Set Variable [ $$DATA.FILEPATH ; ... ]` stores the result

This chain can be traced statically by:
- Finding `OnFirstWindowOpen` triggers in layout XML
- Reading the triggered script from `scripts_sanitized/`
- Grepping custom functions for the variable name or filename patterns

This is Level 3 and not yet implemented — Level 2 (base table overlap) handles these cases adequately for now.

### Script-Only File References

Logic/script-execution files (e.g., Solution_Logic) appear in EDS but have **zero TOs** referencing them for table data from the UI file. They are referenced only for `Perform Script` calls (server-side script execution). These files:

- Are detected at Level 1 (literal `file:Solution_Logic.fmp12` in EDS path)
- Appear in `multi_file.files` with their own table/TO counts
- Do NOT contribute tables to the data model graph (no TOs reference their tables)
- Their `role` is currently set to "data" which is inaccurate — a "logic" or "scripts" role would be more appropriate but is not yet implemented

### Output Format Enrichments

**JSON** (for agents):
- `multi_file.file_architecture`: `"data_separation"` / `"multi_file"` / `"single"`
- `multi_file.data_source_map`: EDS name → solution name (e.g., `{"Cloud Data Source": "Solution_Data"}`)
- `multi_file.files`: per-file summary with role, local table count, TO counts
- `multi_file.data_sources[*].filenames`: extracted filenames from EDS paths
- `multi_file.data_sources[*].has_variable`: whether the path uses `$$` variables
- `data_model.tables[*].source_file`: which FM file owns each base table
- `data_model.tables[*].is_external`: `true` for tables from correlated solutions
- `data_model.base_table_edges[*]`: changed from `[a, b]` to `{left, right, cross_file}`
- `data_model.to_classification`: `{local: N, external: N, by_data_source: {...}}`
- `data_model.local_tables` / `data_model.external_tables`: grouped by ownership

**HTML**:
- Graph nodes colored by source file (blue = local, orange = data file, green/purple for additional files)
- Cross-file edges rendered as dashed orange lines
- Legend showing file-to-color mapping with roles
- "Source" column in the All Tables DataTable
- Multi-File Architecture highlight card in Overview tab

**Markdown**:
- ERD uses Mermaid `flowchart LR` with `subgraph` blocks per file (single-file keeps `erDiagram`)
- Cross-file edges use `-.->` (dashed), same-file edges use `---` (solid)
- Subgraph styling: blue background for UI file, brown for data files
- "Multi-File Architecture" section with pattern label, per-file table, and table ownership listing
- Base Tables table gains a "Source" column

### Table Name Collisions

Both files in a solution may define a table with the same name (e.g., "Startup", "Defaults"). These are distinct tables with different base table IDs and different fields. The analysis handles this by:

- Attributing based on the TO's `Type` column: if a Local TO in the primary file references "Startup", it belongs to the primary file
- If only correlated data defines "Startup" (and it has zero fields in the primary file), it gets attributed to the correlated solution
- Empty tables (zero fields, `membercount="0"` in XML) don't appear in `fields.index` and may be misattributed — this is a known edge case with minimal impact

### Layout Classification and Topology (2026-03-30)

Layouts are now classified by purpose (UI, Output, Utility, Developer) using a decision tree that combines naming patterns with `<Button>` element counts from layout XML. The button count signal provides a near-perfect separation:

| Classification | Avg Buttons | Has 2+ Buttons |
|---|---|---|
| UI | 20.7 | 97% |
| Output | 25.4 | 93% |
| Utility | 1.4 | 0% |
| Developer | 0.2 | 12% |

Decision tree (applied in order):
1. `@` prefix → developer (100% accurate)
2. `Blank ` prefix → utility (100% accurate)
3. `JSON `/ `Export ` prefix → utility
4. PDF script or output naming → output
5. `buttons >= 2` → UI
6. `buttons <= 1` → utility

**Validated** against developer-provided ground truth (150 layouts): developer exact (33/33), output within 1 (31 vs 30), UI 55 vs 59 (93%), utility 31 vs 25 (accounting for the 4 low-button UI layouts that fall below threshold).

**Key finding**: Card window layouts are user-facing UI, not utility. The initial name/folder heuristic misclassified 26 card layouts as utility. The button count signal corrects this — card windows that show data and accept interaction have 2+ buttons.

**Impact on topology**: Using UI-only layout concentration (excluding utility/developer/output) provides a clearer signal for topology classification:

- Anchor-buoy (SolutionApp, confirmed): `ui_top_to_pct = 0.11` — UI layouts spread across many entity TOs
- Tiered-hub (SolutionApp UI file): `ui_top_to_pct = 0.25` — Events TO dominates with 25% of UI layouts
- This signal correctly distinguishes the two patterns even when structural metrics (degree distribution) are similar

See `references/layout-classifications.md` for the full classification framework and `references/relationship-graph-topologies.md` for how it integrates with topology detection.

### Performance Impact

Multi-file detection adds minimal overhead:

| Phase | Time | Notes |
|-------|------|-------|
| `multi_file` | 0.024s | Parse EDS XML, extract paths, match filenames |
| `correlated` | 0.002-0.010s | Load 1-3 correlated solutions' index files |
| `data_model` | +0.001s | Source file attribution loop |

Total: ~0.03s additional on a 4-file solution. The Level 2 overlap matching is the most expensive part (loads candidate TO/field indexes), but it only runs for unresolved variable-based EDS entries.

---

## Files Modified

| File                             | Changes                                                                                                                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent/scripts/analyze.py`       | Script cache, memoized CF chains, sorted deps, status output, `--format all` default, `--status-json` flag. Multi-file: `detect_multi_file()` rewritten with Level 1/2 resolution, `_extract_filenames_from_path()`, `load_correlated_tables()`, `analyze_data_model()` source_file attribution, `base_table_edges` object format, `--correlated` CLI flag, markdown flowchart ERD with subgraphs, multi-file architecture section. Per-file graphs: `_build_file_graph()`, `build_per_file_graphs()`, ERD classification (`_classify_tables`, `_classify_relationship`). Layout classification: `classify_layouts()`, `_classify_layout_purpose()`, `_count_layout_buttons()`, `_find_pdf_layouts()`. Topology: `_classify_topology()` rewritten with multi-signal heuristics including UI layout concentration |
| `agent/scripts/bench_analyze.py` | New: autoresearch benchmark harness                                                                                                                                                            |
| `fmparse.sh`                     | Bug fix: corrected removal directories for custom functions (`custom_function_calcs/` and `custom_functions_sanitized/` instead of non-existent `custom_functions/`) and added `script_stubs/` |
| `fmcontext.sh`                   | Added `Type` and `DataSource` columns to `table_occurrences.index` generation (2 new `xval` extractions)                                                                                      |
| `.cursor/skills/solution-analysis/assets/report_template.html` | Graph nodes colored by source file, cross-file edge dashing, legend, Source column in DataTable, multi-file highlight card in Overview |
| `.cursor/skills/solution-analysis/SKILL.md` | Replaced 3-line multi-file section with comprehensive documentation: detection levels, workflow, profile enrichments, output format differences, narrative guidance |
| `.claude/CLAUDE.md`              | Added documentation conventions section: use generic placeholder names (SolutionApp/SolutionData) instead of real solution names                                                               |
| `.cursor/skills/solution-analysis/references/relationship-graph-topologies.md` | New: Classification framework for FM relationship graph topologies (anchor-buoy, star, tiered-hub, spider-web, flat, hybrid) with heuristic signals and decision matrix |
| `.cursor/skills/solution-analysis/references/layout-classifications.md` | New: Layout purpose classification (UI/Output/Utility/Developer) with button-count signal, decision tree, and validated accuracy data |

## Reproduction

To re-run the optimization loop on a future change:

```bash
# 1. Capture baseline
python3 agent/scripts/bench_analyze.py --baseline

# 2. Make a change to analyze.py

# 3. Test
python3 agent/scripts/bench_analyze.py --check --label "description_of_change"

# 4. If KEEP: update baseline for next iteration
python3 agent/scripts/bench_analyze.py --update

# 5. If REVERT: undo the change, try something else
```
