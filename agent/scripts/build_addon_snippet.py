#!/usr/bin/env python3
"""
build_addon_snippet.py - Build the agentic-fm add-on snippet from the full bundle.

The FileMaker add-on packages every script of its template file, so the template must receive only the
add-on's scripts. This tool restricts filemaker/agentic-fm.xml to the scripts listed in
filemaker/addon/manifest.json and writes filemaker/addon/agentic-fm-addon.xml, keeping the folder structure
and every script's XML byte for byte (folders left empty are dropped). Paste that file into the template.

Spec: agentic-fm-app docs/spec/2026-10-10-agfm-addon-design.md (§3, §5).

After FileMaker builds the package (Save a Copy as Add-on Package), --package imports it from AddonModules,
replaces FileMaker's default metadata (Attribution "Claris", placeholder description and category) with the
manifest's, and repacks the distributable .fmaddon (xar) from the edited folder.

Usage:
    python3 agent/scripts/build_addon_snippet.py           # write the add-on snippet
    python3 agent/scripts/build_addon_snippet.py --check   # exit 1 if the committed snippet is stale
    python3 agent/scripts/build_addon_snippet.py --package # import + metadata + repack the built package

Exit codes: 0 ok / up to date, 1 stale (with --check) or invalid manifest.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE = REPO_ROOT / "filemaker" / "agentic-fm.xml"
MANIFEST = REPO_ROOT / "filemaker" / "addon" / "manifest.json"
OUTPUT = REPO_ROOT / "filemaker" / "addon" / "agentic-fm-addon.xml"
WEBVIEWER_OUTPUT = REPO_ROOT / "filemaker" / "addon" / "agentic-fm-webviewer.xml"
PACKAGE = REPO_ROOT / "filemaker" / "addon" / "agentic-fm"
ARCHIVE = REPO_ROOT / "filemaker" / "addon" / "agentic-fm.fmaddon"
ADDON_MODULES = Path.home() / "Library" / "Application Support" / "FileMaker" / "Extensions" / "AddonModules"

_NAME_RE = re.compile(r'\bname="([^"]*)"')


def _indent(line):
    return line[: len(line) - len(line.lstrip())]


def _opens_object(stripped):
    return stripped.startswith("<Group ") or (stripped.startswith("<Script ") and not stripped.endswith("/>"))


def _malformed(kind, line, number, close):
    name = _NAME_RE.search(line)
    return ValueError(f"bundle: <{kind}> {name.group(1)!r} at line {number} has no matching {close} at the same "
                      f"indentation")


def _parse(lines, start, end_marker, offset=0, owner=None):
    """Children of a folder as ("script", name, [lines]) / ("group", open_line, children, close_line).
    A sibling or outer object opening before a script's or folder's close tag means that tag is missing."""
    children, i = [], start
    level = len(end_marker) - len(end_marker.lstrip()) if end_marker is not None else -1
    while i < len(lines):
        line, stripped = lines[i], lines[i].strip()
        if end_marker is not None and line == end_marker:
            return children, i
        indent = len(line) - len(line.lstrip())
        if owner is not None and indent <= level and (_opens_object(stripped) or stripped == "</Group>"):
            raise _malformed("Group", owner[0], owner[1], "</Group>")
        if stripped.startswith("<Group ") and stripped.endswith("/>"):
            i += 1                                       # an empty folder: nothing to keep
        elif stripped.startswith("<Group "):
            close = _indent(line) + "</Group>"
            sub, j = _parse(lines, i + 1, close, offset, (line, offset + i + 1))
            children.append(("group", line, sub, lines[j]))
            i = j + 1
        elif stripped.startswith("<Script ") and not stripped.endswith("/>"):
            close = _indent(line) + "</Script>"
            j = i + 1
            while j < len(lines) and lines[j] != close:
                inner = lines[j]
                if len(inner) - len(inner.lstrip()) <= indent and (_opens_object(inner.strip())
                                                                   or inner.strip() == "</Group>"):
                    raise _malformed("Script", line, offset + i + 1, "</Script>")
                j += 1
            if j == len(lines):
                raise _malformed("Script", line, offset + i + 1, "</Script>")
            children.append(("script", _NAME_RE.search(line).group(1), lines[i:j + 1]))
            i = j + 1
        else:
            i += 1
    if owner is not None:
        raise _malformed("Group", owner[0], owner[1], "</Group>")
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
    try:
        root = ET.fromstring(bundle_xml.encode("utf-8"))
    except ET.ParseError as exc:
        raise ValueError(f"bundle is not well-formed XML: {exc}") from exc
    defined = {s.get("name") for s in root.iter("Script") if s.find("Step") is not None}
    keep = set(manifest["scripts"])
    unknown = sorted(keep - defined)
    if unknown:
        raise ValueError(f"manifest scripts not in the bundle: {', '.join(unknown)}")
    lines = bundle_xml.splitlines()
    first = next(i for i, l in enumerate(lines) if l.strip().startswith("<Group "))
    last = max(i for i, l in enumerate(lines) if l.strip() == "</fmxmlsnippet>")
    children, _ = _parse(lines[first:last], 0, None, offset=first)
    return "\n".join(lines[:first] + _emit(children, keep) + lines[last:]) + "\n"


def web_viewer_scripts(bundle_xml, manifest):
    """The bundle's scripts outside the add-on (the web viewer): pasted by hand next to the add-on."""
    root = ET.fromstring(bundle_xml.encode("utf-8"))
    defined = {s.get("name") for s in root.iter("Script") if s.find("Step") is not None}
    return defined - set(manifest["scripts"])


def _set(text, key, value):
    """Replace one "Key" : "value" pair in FileMaker's own JSON layout (kept as is, BOM included)."""
    # the value may hold escaped quotes written by an earlier run: match a whole JSON string, not up to the first "
    new, count = re.subn(rf'("{key}"\s*:\s*)"(?:[^"\\]|\\.)*"',
                         lambda m: m.group(1) + json.dumps(value, ensure_ascii=False), text)
    if count != 1:
        raise ValueError(f"{key!r} not found exactly once")
    return new


def apply_metadata(package_dir, manifest):
    """Write the manifest's attribution, URL, category and per-language description into info*.json."""
    package_dir = Path(package_dir)
    version = manifest["version"]
    descriptions = manifest["description"]
    info = package_dir / "info.json"
    text = info.read_text(encoding="utf-8-sig")
    text = _set(_set(text, "Attribution", manifest["attribution"]), "URL", manifest["url"])
    info.write_text("\ufeff" + text, encoding="utf-8")
    for path in sorted(package_dir.glob("info_*.json")):
        lang = path.stem.split("_", 1)[1]
        text = path.read_text(encoding="utf-8-sig")
        text = _set(text, "Description", descriptions.get(lang, descriptions["en"]).format(version=version))
        text = _set(text, "Category", manifest["category"])
        path.write_text("\ufeff" + text, encoding="utf-8")


def check_package_version(package_dir, manifest):
    """The built package must carry the manifest version (AGFM Version's literal, kept in en.xml's strings)."""
    strings = (Path(package_dir) / "en.xml").read_text(encoding="utf-8-sig")
    if f"<SourceText>{manifest['version']}</SourceText>" not in strings:
        raise ValueError(f"the built package is not version {manifest['version']}: rebuild it in FileMaker "
                         f"(AGFM Version and manifest.json must match)")


def xar_command(archive_name, folder_name):
    """xar invocation for the .fmaddon: --distribution keeps only the properties a distributed archive needs (no
    user, group, extended attributes or times from the maintainer's Mac)."""
    return ["xar", "-cf", archive_name, "--compression=gzip", "--distribution", folder_name]


def package(manifest):
    """Import the built package from AddonModules, apply the metadata, repack the .fmaddon (xar)."""
    source = ADDON_MODULES / manifest["name"]
    if not source.is_dir():
        raise ValueError(f"no built package at {source}: run the builder in FileMaker first")
    check_package_version(source, manifest)
    if shutil.which("xar") is None:
        raise ValueError("xar not found (macOS only): cannot repack the .fmaddon")
    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    shutil.copytree(source, PACKAGE)
    apply_metadata(PACKAGE, manifest)
    ARCHIVE.unlink(missing_ok=True)
    subprocess.run(xar_command(ARCHIVE.name, PACKAGE.name), cwd=PACKAGE.parent, check=True)
    # Refresh this Mac's copy so the install dialog shows the same metadata (after a FileMaker restart).
    for path in PACKAGE.glob("info*.json"):
        shutil.copy2(path, source / path.name)
    shutil.copy2(ARCHIVE, ADDON_MODULES / ARCHIVE.name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed snippet is stale")
    parser.add_argument("--package", action="store_true",
                        help="import the built package from AddonModules, apply the metadata, repack the .fmaddon")
    args = parser.parse_args(argv)
    if args.package:
        try:
            package(json.loads(MANIFEST.read_text(encoding="utf-8")))
        except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
            print(f"package: {exc}", file=sys.stderr)
            return 1
        print(f"packaged {PACKAGE.relative_to(REPO_ROOT)} and {ARCHIVE.relative_to(REPO_ROOT)}")
        return 0
    try:
        bundle = BUNDLE.read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        outputs = {OUTPUT: build(bundle, manifest),
                   WEBVIEWER_OUTPUT: build(bundle, {"scripts": sorted(web_viewer_scripts(bundle, manifest))})}
    except (ValueError, KeyError) as exc:
        print(f"invalid bundle or manifest: {exc}", file=sys.stderr)
        return 1
    if args.check:
        stale = [path for path, text in outputs.items()
                 if (path.read_text(encoding="utf-8") if path.exists() else "") != text]
        for path in stale:
            print(f"{path.relative_to(REPO_ROOT)} is stale: run python3 agent/scripts/build_addon_snippet.py")
        if stale:
            return 1
        print("add-on and web viewer snippets up to date")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
