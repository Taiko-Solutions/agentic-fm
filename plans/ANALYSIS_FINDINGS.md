# Analysis Performance Optimization Findings

Findings from the autoresearch-style optimization of `agent/scripts/analyze.py`, conducted 2026-03-29.

## Summary

Applied Karpathy's autoresearch methodology (single metric, iterative keep/revert, constrained edit surface) to optimize the solution analysis script. Achieved a **39% wall-clock reduction** on UnnamedSolution (1.19s to 0.72s) and **34%** on FM_Quickstart (0.64s to 0.42s).

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

**Result:** Actually _slower_ (+2% for UnnamedSolution, +12% for FM_Quickstart) AND produced different output. The regex compilation cost for 610 escaped patterns exceeded the savings, and `findall` with overlapping patterns behaves differently than individual `in` checks.

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

6. **Test against multiple solutions.** UnnamedSolution (610 CFs, O(n^2) bottleneck) and FM_Quickstart (122 CFs, I/O bottleneck) have different profiles. An optimization that helps one may hurt the other.

7. **`--update` is part of the loop.** When a change intentionally corrects output (e.g., resolving script names through the index instead of parsing filenames), the baseline must be updated. The harness should distinguish "output changed, is it better or worse?" from "output corrupted."

---

## Files Modified

| File                             | Changes                                                                                                                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent/scripts/analyze.py`       | Script cache, memoized CF chains, sorted deps, status output, `--format all` default, `--status-json` flag                                                                                     |
| `agent/scripts/bench_analyze.py` | New: autoresearch benchmark harness                                                                                                                                                            |
| `fmparse.sh`                     | Bug fix: corrected removal directories for custom functions (`custom_function_calcs/` and `custom_functions_sanitized/` instead of non-existent `custom_functions/`) and added `script_stubs/` |

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
