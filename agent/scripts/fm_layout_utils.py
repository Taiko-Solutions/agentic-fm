#!/usr/bin/env python3
"""
fm_layout_utils.py — Shared utilities for the Layout Modernization Pipeline.

Provides:
  - ThemeReader: reads theme tokens from agent/context/{solution}/ files
  - classify_layout_type(summary): classify layout purpose from its summary dict
  - inject_fm_bridge(html, field_bindings): inject FileMaker bridge JS into HTML
"""

import json
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# ThemeReader
# ---------------------------------------------------------------------------

class ThemeReader:
    """Read theme tokens from the extracted theme files for a solution."""

    def __init__(self, solution_name: str, context_dir: str = "agent/context"):
        self.solution_name = solution_name
        self.context_dir = context_dir

    def _solution_dir(self) -> Path:
        """Return the absolute path to the solution context directory."""
        # Resolve relative to the repo root (two levels up from this script)
        here = Path(__file__).resolve().parent
        agent_root = here.parent
        base = Path(self.context_dir)
        if not base.is_absolute():
            base = agent_root.parent / base
        return base / self.solution_name

    def available(self) -> bool:
        """Return True if theme-manifest.json exists for this solution."""
        return (self._solution_dir() / "theme-manifest.json").is_file()

    def read(self) -> dict:
        """Return theme tokens dict. Values are None if source files are missing."""
        sol_dir = self._solution_dir()
        result = {
            "name": None,
            "colors": None,
            "fonts": None,
            "spacing": None,
            "classes": None,
            "css_raw": None,
        }

        # theme-manifest.json
        manifest_path = sol_dir / "theme-manifest.json"
        if manifest_path.is_file():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                result["name"] = manifest.get("theme", {}).get("name")
                cp = manifest.get("colorPalette")
                if cp:
                    result["colors"] = cp
                lb = manifest.get("layoutBuilder")
                if lb:
                    result["spacing"] = lb
            except (json.JSONDecodeError, OSError):
                pass

        # theme-classes.json — collect class names
        classes_path = sol_dir / "theme-classes.json"
        if classes_path.is_file():
            try:
                with open(classes_path, "r", encoding="utf-8") as f:
                    classes_data = json.load(f)
                result["classes"] = list(classes_data.keys()) if classes_data else []
            except (json.JSONDecodeError, OSError):
                pass

        # theme.css — raw CSS and font extraction
        css_path = sol_dir / "theme.css"
        if css_path.is_file():
            try:
                with open(css_path, "r", encoding="utf-8") as f:
                    css_raw = f.read()
                result["css_raw"] = css_raw
                result["fonts"] = _extract_fonts_from_css(css_raw)
            except OSError:
                pass

        return result


def _extract_fonts_from_css(css_text: str) -> "dict | None":
    """Parse heading and body fonts from the first 300 lines of CSS.

    Looks for font-family: declarations and tries to classify them as heading
    or body based on proximity to heading/body selectors.
    """
    lines = css_text.split("\n")[:300]
    fonts = {"heading": None, "body": None}

    current_selector = ""
    for line in lines:
        stripped = line.strip()
        # Track selectors
        if stripped and not stripped.startswith("/*") and "{" in stripped:
            current_selector = stripped.lower()

        # Extract font-family values
        if "font-family:" in stripped:
            # Match standard CSS or FM-specific font declaration
            m = re.search(r'font-family\s*:\s*([^;]+)', stripped)
            if m:
                font_val = m.group(1).strip().strip("'\"")
                # Classify by selector context
                if any(k in current_selector for k in ("h1", "h2", "h3", "heading", "title")):
                    if fonts["heading"] is None:
                        fonts["heading"] = font_val
                elif fonts["body"] is None:
                    fonts["body"] = font_val

            # FM-specific: -fm-font-family(Name,Variant)
            m2 = re.search(r'-fm-font-family\(([\w-]+)', stripped)
            if m2:
                raw = m2.group(1)
                family = raw.split("-")[0] if "-" in raw else raw
                if any(k in current_selector for k in ("h1", "h2", "h3", "heading", "title")):
                    if fonts["heading"] is None:
                        fonts["heading"] = family
                elif fonts["body"] is None:
                    fonts["body"] = family

    return fonts if (fonts["heading"] or fonts["body"]) else None


# ---------------------------------------------------------------------------
# classify_layout_type
# ---------------------------------------------------------------------------

def classify_layout_type(summary: dict) -> str:
    """Classify layout purpose from its summary dict.

    Returns one of: "detail", "list", "card", "dashboard", "print", "utility"

    Rules (evaluated in priority order):
      1. Has TopNav or TitleHeader part type → "dashboard"
      2. Layout width > 1200 and no portals → "print"
      3. Body object count < 6 and no portals → "card"
      4. Has SubSummary parts → "list"
      5. Has portals AND field_count > 8 → "detail"
      6. Has portals AND field_count <= 8 → "list"
      7. Body object count > 20 → "dashboard"
      8. Default → "detail"
    """
    parts = summary.get("parts", [])
    width = summary.get("width", 0)

    part_types = [p.get("type", "") for p in parts]

    # Count body objects and portals/fields across all parts
    body_object_count = 0
    portal_count = 0
    field_count = 0

    for part in parts:
        objects = part.get("objects", [])
        p_type = part.get("type", "")
        is_body = p_type in ("Body", "")

        for obj in objects:
            if is_body:
                body_object_count += 1
            obj_type = obj.get("type", "")
            if obj_type == "Portal":
                portal_count += 1
                # Count fields inside the portal
                for child in obj.get("objects", []):
                    if "field" in child:
                        field_count += 1
            elif "field" in obj:
                field_count += 1

    # Rule 1: TopNav or TitleHeader → dashboard
    if any(t in ("TopNav", "TitleHeader") for t in part_types):
        return "dashboard"

    # Rule 2: wide and no portals → print
    if width > 1200 and portal_count == 0:
        return "print"

    # Rule 3: sparse body, no portals → card
    if body_object_count < 6 and portal_count == 0:
        return "card"

    # Rule 4: SubSummary parts → list
    if any(t == "SubSummary" for t in part_types):
        return "list"

    # Rule 5/6: portals
    if portal_count > 0:
        return "detail" if field_count > 8 else "list"

    # Rule 7: busy body → dashboard
    if body_object_count > 20:
        return "dashboard"

    # Default
    return "detail"


# ---------------------------------------------------------------------------
# inject_fm_bridge
# ---------------------------------------------------------------------------

_FM_BRIDGE_JS = """\
<script>
// FileMaker Bridge — auto-injected by agentic-fm
(function() {
  window.fmCallback = function(scriptName, param) {
    if (typeof FileMaker !== 'undefined' && FileMaker.PerformScript) {
      FileMaker.PerformScript(scriptName, typeof param === 'string' ? param : JSON.stringify(param));
    } else {
      console.log('[FM Bridge] PerformScript:', scriptName, param);
    }
  };
  window.fmLoadData = function(data) {
    console.log('[FM Bridge] Data received:', data);
  };
  document.addEventListener('DOMContentLoaded', function() {
    window.fmCallback('WebViewer Ready', {layout: document.title});
  });
})();
</script>"""


def inject_fm_bridge(html: str, field_bindings: dict = None) -> str:
    """Inject FileMaker bridge JS into an HTML string before </body>.

    If field_bindings is provided (dict of {css_selector: "TO::FieldName"}),
    a second script block is added that sets data-fm-field attributes on
    DOMContentLoaded.

    If </body> is not found, the script(s) are appended to the end.
    If the bridge has already been injected (detected by marker comment),
    this is a no-op.
    """
    # Guard against double-injection
    if "FileMaker Bridge — auto-injected by agentic-fm" in html:
        return html

    bridge = _FM_BRIDGE_JS

    # Build optional field-bindings script
    bindings_block = ""
    if field_bindings:
        bindings_js_lines = [
            "<script>",
            "// FileMaker field bindings — auto-injected by agentic-fm",
            "document.addEventListener('DOMContentLoaded', function() {",
            "  var bindings = " + json.dumps(field_bindings, ensure_ascii=False) + ";",
            "  Object.keys(bindings).forEach(function(sel) {",
            "    var els = document.querySelectorAll(sel);",
            "    els.forEach(function(el) { el.setAttribute('data-fm-field', bindings[sel]); });",
            "  });",
            "});",
            "</script>",
        ]
        bindings_block = "\n" + "\n".join(bindings_js_lines)

    inject = bridge + bindings_block + "\n"

    close_body = "</body>"
    idx = html.lower().rfind(close_body.lower())
    if idx != -1:
        # Find the actual case of </body> in the original string
        return html[:idx] + inject + html[idx:]
    else:
        return html + "\n" + inject
