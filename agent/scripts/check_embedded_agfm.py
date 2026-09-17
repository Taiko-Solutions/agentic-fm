#!/usr/bin/env python3
"""
check_embedded_agfm.py

Detect whether the agentic-fm scripts and the Context custom function that are
*embedded* in a host FileMaker solution have drifted from the canonical bundled
reference shipped with this repository.

Why this exists
---------------
The agentic-fm scripts (AGFMScriptBridge, AGFMEvaluation, Push Context, the
menu, etc.) and the Context custom function are *pasted* into each host
solution during setup. Bug fixes to those objects (see the AGFM_Bridge issues)
do NOT propagate automatically -- someone has to re-paste them. Over time an
embedded copy can silently fall behind the version bundled in `filemaker/`,
which leads to confusing failures. This tool surfaces that drift.

Sources
-------
Canonical (source of truth, versioned in this repo):
    filemaker/agentic-fm.xml   -- fmxmlsnippet containing every agentic-fm script
    filemaker/Context.fmfn     -- the Context custom function

Embedded (produced by "Explode XML" against a host solution):
    agent/xml_parsed/scripts/<Solution>/<folder>/<ScriptName> - ID <n>.xml
    agent/xml_parsed/custom_function_stubs/<Solution>/Context - ID <n>.xml

Both are searched recursively. The exporter mirrors the solution layout -- one
directory per file, then the Script Workspace folder tree -- and appends
" - ID <n>" to every filename, so a flat glob on a fixed folder name finds
nothing at all.

How it compares
---------------
Both sides are rendered to human-readable script text with the same tool
(snippet_to_hr.py) and diffed line by line. Comparing raw step signatures does
not work: the canonical side is fmxmlsnippet while the embedded side is SaXML
put through fm_xml_to_snippet.py, and the two disagree on detail that carries
no meaning (the <Repetition> block FileMaker adds to Set Variable on save,
element order, enum values rendered as raw value on one side and HR label on
the other).

Differences that survive are classified, because the converter drops
parameters it does not model (the destination of Save a Copy as XML, the body
of Perform AppleScript, the arguments of Get Folder Path). Such a loss only
ever REMOVES text; genuine drift adds or changes it. An object whose only
differences are removals -- or the engine's own case rewriting of function
names, e.g. GetAsTimestamp -> GetAsTimeStamp -- is reported OK~ rather than
STALE.

Read the diff before acting on a STALE verdict (--diff). An embedded object may
carry a deliberate local change, and re-pasting the bundle would destroy it.

Usage
-----
    python3 agent/scripts/check_embedded_agfm.py [options]

Options:
    --repo-root PATH   Project root (default: two levels up from this file)
    --json             Emit machine-readable JSON instead of a table
    --advisory         Always exit 0 (report only; do not signal drift)
    -h, --help         Show this help

Exit codes:
    0  all embedded objects match, OR no agentic-fm objects were found
    1  at least one object is STALE or MISSING (unless --advisory)
"""

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Signature extraction
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")


def _norm(text):
    """Collapse all whitespace so reformatting does not look like a logic change."""
    return _WS_RE.sub(" ", (text or "")).strip()


def _signature_from_steps(steps):
    """Build a semantic signature from an iterable of <Step> elements.

    The signature captures, in document order:
      * each step's name attribute (structural shape of the script)
      * every <Calculation> CDATA payload (the actual logic)
      * every comment <Text> payload (doc-block / inline comments)

    Volatile data (ids, GUIDs, field/TO references rendered as <Field>) is
    deliberately excluded, so the signature is stable across solutions.
    """
    parts = []
    for step in steps:
        parts.append("S:" + _norm(step.get("name", "")))
        for calc in step.iter("Calculation"):
            if calc.text and calc.text.strip():
                parts.append("C:" + _norm(calc.text))
        for txt in step.iter("Text"):
            if txt.text and txt.text.strip():
                parts.append("T:" + _norm(txt.text))
    blob = "\x1f".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _canonical_signatures(reference_path):
    """Return {script_name: signature} for the bundled fmxmlsnippet reference.

    The reference lists some scripts multiple times (0-step entries are just
    Perform-Script references); we keep, per name, the definition with the most
    steps.
    """
    root = ET.parse(reference_path).getroot()
    best = {}  # name -> (step_count, signature)
    for script in root.findall(".//Script"):
        name = script.get("name")
        if not name:
            continue
        steps = script.findall(".//Step")
        if not steps:
            continue
        if name not in best or len(steps) > best[name][0]:
            best[name] = (len(steps), _signature_from_steps(steps))
    return {name: sig for name, (_, sig) in best.items()}


def _steps_from_embedded(path, converter):
    """Parse an embedded per-script file into <Step> elements.

    Accepts either fmxmlsnippet (used directly) or SaXML (converted first via
    the repo's fm_xml_to_snippet.py). Returns a list of Step elements, or None
    if the file cannot be understood.
    """
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    if root.tag == "fmxmlsnippet":
        return root.findall(".//Step")

    # Assume SaXML -> convert to fmxmlsnippet with the bundled converter.
    try:
        out = subprocess.run(
            [sys.executable, str(converter), str(path)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        conv = ET.fromstring(out.stdout)
    except ET.ParseError:
        return None
    return conv.findall(".//Step")


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

def _key(name):
    """Normalize a script name for filename matching (case/punctuation-insensitive)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


_ID_SUFFIX_RE = re.compile(r"\s*-\s*ID\s*\d+$")


def _stem_without_id(path):
    """Strip the exporter's ' - ID <n>' suffix from a filename stem."""
    return _ID_SUFFIX_RE.sub("", path.stem)


def _index_embedded_scripts(scripts_dir):
    """Return {normalized_name: Path} for every script file under the scripts dir.

    The exporter does not write a flat directory of ``<ScriptName>.xml``. It
    mirrors the solution layout, so a real tree looks like::

        scripts/<Solution>/<Script Workspace folder>/<ScriptName> - ID <n>.xml

    Hence the recursive walk and the ' - ID <n>' suffix strip: a non-recursive
    glob on ``scripts/`` finds nothing at all, which is how this check silently
    reported "nothing to check" on every exploded solution.
    """
    index = {}
    if not scripts_dir.is_dir():
        return index
    for p in sorted(scripts_dir.rglob("*.xml")):
        index.setdefault(_key(_stem_without_id(p)), p)
    return index


# ---------------------------------------------------------------------------
# Context custom function
# ---------------------------------------------------------------------------

def _context_signature(text, fold_case=False):
    """Signature of the Context custom function calculation text.

    With fold_case, case is ignored: FileMaker rewrites function names when a
    custom function is pasted (GetAsTimestamp becomes GetAsTimeStamp), which is
    a cosmetic rewrite by the engine, not a change to the function's logic.
    """
    norm = _norm(text)
    if fold_case:
        norm = norm.lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _embedded_context_text(xml_parsed):
    """Locate the embedded Context CF text.

    Tries, in order: the sanitized text folder, then any XML folder holding
    custom function definitions. All are searched recursively because the
    exporter nests them per solution (``<folder>/<Solution>/Context - ID 3.xml``),
    and ``custom_function_stubs`` is what fm-xml-export-exploder 0.5.1 actually
    produces -- the two names tried previously simply do not exist.
    """
    san = xml_parsed / "custom_functions_sanitized"
    if san.is_dir():
        for p in sorted(san.rglob("*")):
            if p.is_file() and "context" in _stem_without_id(p).lower():
                try:
                    return p.read_text(encoding="utf-8")
                except OSError:
                    pass
    for folder in ("custom_function_calcs", "custom_function_stubs"):
        calcs = xml_parsed / folder
        if not calcs.is_dir():
            continue
        for p in sorted(calcs.rglob("*.xml")):
            if "context" in _stem_without_id(p).lower():
                    try:
                        root = ET.parse(p).getroot()
                    except ET.ParseError:
                        continue
                    # Grab the largest text payload in the file.
                    texts = [e.text for e in root.iter() if e.text and e.text.strip()]
                    if texts:
                        return max(texts, key=len)
    return None


# ---------------------------------------------------------------------------
# Human-readable rendering + noise classification
# ---------------------------------------------------------------------------
#
# Comparing raw step signatures across the two formats does not work. The
# canonical side is fmxmlsnippet; the embedded side is SaXML that has to be run
# through fm_xml_to_snippet.py first, and the two disagree on things that carry
# no meaning:
#
#   * FileMaker adds <Repetition><Calculation>1</Calculation></Repetition> to
#     Set Variable steps when it saves, so the embedded side has extra "1"
#     calculations everywhere.
#   * Element order and duplication differ for some steps (Go to Layout emits
#     its calculation twice on one side, once on the other).
#
# Rendering BOTH sides through the same HR generator collapses all of that.
# What it does not collapse is fm_xml_to_snippet.py dropping parameters it does
# not model (the destination of Save a Copy as XML, the body of Perform
# AppleScript, the arguments of Get Folder Path). Those losses only ever REMOVE
# text, never add it -- which is exactly what _looks_like_converter_loss()
# keys on, so real drift (which adds or changes text) still surfaces.

def _hr_from_steps(steps, hr_tool, workdir):
    """Render <Step> elements to human-readable text via snippet_to_hr.py."""
    snippet = ET.Element("fmxmlsnippet", {"type": "FMObjectList"})
    for st in steps:
        snippet.append(st)
    tmp = workdir / "hr_input.xml"
    try:
        ET.ElementTree(snippet).write(tmp, encoding="utf-8", xml_declaration=True)
        out = subprocess.run(
            [sys.executable, str(hr_tool), "--raw", str(tmp)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError, ET.ParseError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _enum_label_map(repo_root):
    """Build {raw_xml_enum_value: human_readable_label} from the step catalog.

    The canonical side renders some enums with their raw XML value while the
    converted side renders the HR label for the same option (SaveType
    "BrowsedRecords" vs "Records being browsed"). Mapping both sides onto the
    label removes that difference without hardcoding any step. Only values of
    6+ characters are mapped, so short generic ones (True/False -> On/Off)
    cannot corrupt unrelated text.
    """
    catalog = repo_root / "agent" / "catalogs" / "step-catalog-en.json"
    mapping = {}
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mapping
    steps = data if isinstance(data, list) else data.get("steps", data)
    if isinstance(steps, dict):
        steps = list(steps.values())
    if not isinstance(steps, list):
        return mapping
    for step in steps:
        if not isinstance(step, dict):
            continue
        for param in step.get("params") or []:
            for raw, label in (param.get("hrEnumValues") or {}).items():
                if not isinstance(raw, str) or not isinstance(label, str):
                    continue
                if len(raw) >= 6 and raw.lower() != label.lower():
                    mapping[raw.lower()] = label.lower()
    return mapping


def _apply_enum_labels(text, mapping):
    """Rewrite raw enum values to their HR label (case-insensitive, whole word)."""
    for raw, label in mapping.items():
        text = re.sub(r"\b" + re.escape(raw) + r"\b", label, text, flags=re.IGNORECASE)
    return text


def _is_subsequence(needle, haystack):
    """True if every character of needle appears in haystack, in order."""
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _looks_like_converter_loss(canon_line, emb_line, enum_map=None):
    """True when emb_line is canon_line with material removed (not changed).

    A dropped parameter shortens the rendered step; genuine drift edits or adds
    text. Case is ignored because FileMaker rewrites function names when a
    script is pasted (Get ( CurrentTimestamp ) becomes Get ( CurrentTimeStamp )).
    """
    a = _norm(canon_line).lower()
    b = _norm(emb_line).lower()
    if enum_map:
        a = _apply_enum_labels(a, enum_map)
        b = _apply_enum_labels(b, enum_map)
    if a == b:
        return True
    return len(b) < len(a) and _is_subsequence(b, a)


def _compare_hr(canon_hr, emb_hr, enum_map=None):
    """Compare two HR renderings. Returns (status, diff_text).

    status is "OK" (identical), "OK~" (differs only by known converter noise)
    or "STALE" (real drift).
    """
    a = canon_hr.splitlines()
    b = emb_hr.splitlines()
    if a == b:
        return "OK", ""

    def key(lines):
        out = [_norm(l).lower() for l in lines]
        return [_apply_enum_labels(l, enum_map) for l in out] if enum_map else out

    real_drift = False
    matcher = difflib.SequenceMatcher(None, key(a), key(b))
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            if all(_looks_like_converter_loss(a[i], b[j], enum_map)
                   for i, j in zip(range(i1, i2), range(j1, j2))):
                continue
        elif tag == "delete" and all(not _norm(l) for l in a[i1:i2]):
            continue  # blank-line-only difference
        elif tag == "insert" and all(not _norm(l) for l in b[j1:j2]):
            continue
        real_drift = True
        break

    diff = "\n".join(difflib.unified_diff(a, b, "bundled", "embedded",
                                          lineterm="", n=2))
    return ("STALE" if real_drift else "OK~"), diff


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _explode_present(xml_parsed):
    """True when the directory holds an actual explode, not just an empty shell.

    The setup procedure creates agent/xml_parsed/ up front, and macOS drops a
    .DS_Store into it, so "the directory is non-empty" is not evidence of an
    explode. Requiring at least one .xml keeps a freshly created repo reporting
    the honest "nothing to check" instead of a spurious alarm.
    """
    if not xml_parsed.is_dir():
        return False
    return next(xml_parsed.rglob("*.xml"), None) is not None


def _canonical_steps(reference_path):
    """Return {script_name: [<Step>]} for the bundled fmxmlsnippet reference.

    The reference lists some scripts multiple times -- the 0-step entries are
    the <Script> references inside Perform Script steps -- so we keep, per name,
    the definition with the most steps.
    """
    root = ET.parse(reference_path).getroot()
    best = {}
    for script in root.findall(".//Script"):
        name = script.get("name")
        if not name:
            continue
        steps = script.findall(".//Step")
        if not steps:
            continue
        if name not in best or len(steps) > len(best[name]):
            best[name] = steps
    return best


def check(repo_root):
    """Compare embedded objects against the canonical reference.

    Returns a dict with:
      objects           [{name, kind, status, diff}]  status in
                        OK / OK~ / STALE / MISSING / UNREADABLE
      checked           True when at least one embedded object was recognised
      explode_present   True when an explode exists on disk. explode_present
                        without checked means the explode could not be read --
                        a bug in this tool, not an absence of data, and it must
                        not be reported as a silent "nothing to check".
    """
    reference = repo_root / "filemaker" / "agentic-fm.xml"
    context_fmfn = repo_root / "filemaker" / "Context.fmfn"
    xml_parsed = repo_root / "agent" / "xml_parsed"
    converter = repo_root / "agent" / "scripts" / "fm_xml_to_snippet.py"
    hr_tool = repo_root / "agent" / "scripts" / "snippet_to_hr.py"
    scripts_dir = xml_parsed / "scripts"

    results = []
    explode_present = _explode_present(xml_parsed)

    enum_map = _enum_label_map(repo_root)
    canonical = _canonical_steps(reference) if reference.exists() else {}
    embedded_index = _index_embedded_scripts(scripts_dir)

    with tempfile.TemporaryDirectory(prefix="agfm-freshness-") as tmp:
        workdir = Path(tmp)
        for name in sorted(canonical):
            embedded_path = embedded_index.get(_key(name))
            diff = ""
            if embedded_path is None:
                status = "MISSING"
            else:
                emb_steps = _steps_from_embedded(embedded_path, converter)
                canon_hr = _hr_from_steps(canonical[name], hr_tool, workdir)
                emb_hr = (_hr_from_steps(emb_steps, hr_tool, workdir)
                          if emb_steps is not None else None)
                if canon_hr is None or emb_hr is None:
                    status = "UNREADABLE"
                else:
                    status, diff = _compare_hr(canon_hr, emb_hr, enum_map)
            results.append({"name": name, "kind": "script",
                            "status": status, "diff": diff})

    # --- Context custom function ------------------------------------------
    if context_fmfn.exists():
        canon_text = context_fmfn.read_text(encoding="utf-8")
        emb_ctx = _embedded_context_text(xml_parsed)
        if emb_ctx is None:
            status = "MISSING"
        elif _context_signature(emb_ctx) == _context_signature(canon_text):
            status = "OK"
        elif (_context_signature(emb_ctx, fold_case=True)
              == _context_signature(canon_text, fold_case=True)):
            status = "OK~"  # differs only in the engine's own case rewriting
        else:
            status = "STALE"
        results.append({"name": "Context", "kind": "custom_function",
                        "status": status, "diff": ""})

    any_embedded = bool(embedded_index) or _embedded_context_text(xml_parsed) is not None
    return {"objects": results, "checked": any_embedded,
            "explode_present": explode_present}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_table(report, show_diff=False):
    objs = report["objects"]
    if not report["checked"]:
        if report.get("explode_present"):
            print("An explode exists but no agentic-fm object could be read from it.")
            print("That is a fault in this check, not an absence of data — verify the")
            print("layout of agent/xml_parsed/ against _index_embedded_scripts().")
        else:
            print("No agentic-fm objects found in the exploded solution — nothing to check.")
            print("(Run 'Explode XML' on a solution that has agentic-fm installed to enable this check.)")
        return
    drift = [o for o in objs if o["status"] in ("STALE", "MISSING", "UNREADABLE")]
    noise = [o for o in objs if o["status"] == "OK~"]
    width = max((len(o["name"]) for o in objs), default=4)
    print("Embedded agentic-fm code vs bundled reference:\n")
    for o in objs:
        mark = {"OK": "✓", "OK~": "✓", "STALE": "✗",
                "MISSING": "•", "UNREADABLE": "?"}.get(o["status"], "?")
        print(f"  {mark} {o['name']:<{width}}  {o['status']:<10} ({o['kind']})")
    print()
    if noise:
        print(f"   {len(noise)} object(s) marked OK~ match once the known parameter losses")
        print("   of fm_xml_to_snippet.py are discounted. Re-run with --diff to inspect.")
        print()
    if drift:
        print(f"⚠  {len(drift)} object(s) out of date. Re-deploy the agentic-fm scripts /")
        print("   Context custom function into this solution from filemaker/ to resync.")
        print("   Review the diff first (--diff): an embedded object may carry a")
        print("   deliberate local change that a blind re-paste would destroy.")
    else:
        print("All embedded agentic-fm objects match the bundled reference.")
    if show_diff:
        for o in objs:
            if o.get("diff"):
                print(f"\n--- {o['name']} ({o['status']}) " + "-" * 40)
                print(o["diff"])


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=True, description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--advisory", action="store_true", help="always exit 0")
    parser.add_argument("--diff", action="store_true",
                        help="show the human-readable diff for every object that differs")
    args = parser.parse_args(argv)

    report = check(args.repo_root)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_table(report, show_diff=args.diff)

    if args.advisory:
        return 0
    if not report["checked"]:
        # An unreadable explode is a failure; a missing one is not.
        return 1 if report.get("explode_present") else 0
    drift = any(o["status"] in ("STALE", "MISSING", "UNREADABLE")
                for o in report["objects"])
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
