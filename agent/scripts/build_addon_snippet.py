#!/usr/bin/env python3
"""
build_addon_snippet.py - Build the agentic-fm add-on snippet from the full bundle.

The FileMaker add-on packages every script of its template file, so the template must receive only the
add-on's scripts. This tool restricts filemaker/agentic-fm.xml to the scripts listed in
filemaker/addon/manifest.json and writes filemaker/addon/agentic-fm-addon.xml, keeping the folder structure
and every script's XML byte for byte (folders left empty are dropped). Paste that file into the template.

Spec: agentic-fm-app docs/spec/2026-10-10-agfm-addon-design.md (§3, §5).

Usage:
    python3 agent/scripts/build_addon_snippet.py           # write the add-on snippet
    python3 agent/scripts/build_addon_snippet.py --check   # exit 1 if the committed snippet is stale

Exit codes: 0 ok / up to date, 1 stale (with --check) or invalid manifest.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE = REPO_ROOT / "filemaker" / "agentic-fm.xml"
MANIFEST = REPO_ROOT / "filemaker" / "addon" / "manifest.json"
OUTPUT = REPO_ROOT / "filemaker" / "addon" / "agentic-fm-addon.xml"

_NAME_RE = re.compile(r'\bname="([^"]*)"')


def _indent(line):
    return line[: len(line) - len(line.lstrip())]


def _parse(lines, start, end_marker):
    """Children of a folder as ("script", name, [lines]) / ("group", open_line, children, close_line)."""
    children, i = [], start
    while i < len(lines):
        line, stripped = lines[i], lines[i].strip()
        if end_marker is not None and line == end_marker:
            return children, i
        if stripped.startswith("<Group ") and stripped.endswith("/>"):
            i += 1                                       # an empty folder: nothing to keep
        elif stripped.startswith("<Group "):
            close = _indent(line) + "</Group>"
            sub, j = _parse(lines, i + 1, close)
            children.append(("group", line, sub, lines[j]))
            i = j + 1
        elif stripped.startswith("<Script ") and not stripped.endswith("/>"):
            close = _indent(line) + "</Script>"
            j = lines.index(close, i + 1)
            children.append(("script", _NAME_RE.search(line).group(1), lines[i:j + 1]))
            i = j + 1
        else:
            i += 1
    return children, i


def _emit(children, keep):
    out = []
    for child in children:
        if child[0] == "script":
            if child[1] in keep:
                out.extend(child[2])
        else:
            inner = _emit(child[2], keep)
            if inner:
                out.extend([child[1], *inner, child[3]])
    return out


def build(bundle_xml, manifest):
    """The bundle restricted to the manifest's scripts (folder structure kept, empty folders dropped)."""
    root = ET.fromstring(bundle_xml.encode("utf-8"))
    defined = {s.get("name") for s in root.iter("Script") if s.find("Step") is not None}
    keep = set(manifest["scripts"])
    unknown = sorted(keep - defined)
    if unknown:
        raise ValueError(f"manifest scripts not in the bundle: {', '.join(unknown)}")
    lines = bundle_xml.splitlines()
    first = next(i for i, l in enumerate(lines) if l.strip().startswith("<Group "))
    last = max(i for i, l in enumerate(lines) if l.strip() == "</fmxmlsnippet>")
    children, _ = _parse(lines[first:last], 0, None)
    return "\n".join(lines[:first] + _emit(children, keep) + lines[last:]) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed snippet is stale")
    args = parser.parse_args(argv)
    try:
        text = build(BUNDLE.read_text(encoding="utf-8"), json.loads(MANIFEST.read_text(encoding="utf-8")))
    except (ValueError, KeyError) as exc:
        print(f"invalid manifest: {exc}", file=sys.stderr)
        return 1
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT.relative_to(REPO_ROOT)} is stale: run python3 agent/scripts/build_addon_snippet.py")
            return 1
        print("add-on snippet up to date")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
