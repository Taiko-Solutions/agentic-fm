#!/usr/bin/env python3
"""
layout_to_brief.py — Design Brief Enricher for FileMaker layouts.

Enriches a layout summary JSON with semantic context: layout type classification,
field types from the index, relationship context for portals, spatial groupings,
and theme tokens. Output is a structured "design brief" JSON for downstream use
by layout modernisation tools.

Usage:
  python3 agent/scripts/layout_to_brief.py <layout_name_or_json_path> --solution "Solution Name"
  python3 agent/scripts/layout_to_brief.py "Invoices Details" --solution "MyApp" -o brief.json
  python3 agent/scripts/layout_to_brief.py path/to/summary.json --solution "MyApp" --compact
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_agent_root() -> Path:
    """Return the absolute path to the agent/ directory."""
    return Path(__file__).resolve().parent.parent


def get_repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return get_agent_root().parent


# ---------------------------------------------------------------------------
# Step A — Locate summary JSON
# ---------------------------------------------------------------------------

def locate_summary(layout_arg: str, solution: str, agent_root: Path) -> dict:
    """Locate and return the layout summary JSON.

    Priority:
      1. If layout_arg looks like an existing file path, read it directly.
      2. Glob agent/context/{solution}/layouts/ for matching JSON files.
      3. Invoke layout_to_summary.py as a subprocess and read the output.
    """
    # Direct file path
    candidate = Path(layout_arg)
    if candidate.suffix.lower() == ".json" and candidate.exists():
        with open(candidate, "r", encoding="utf-8") as f:
            return json.load(f)

    # Glob in context layouts directory
    layouts_dir = agent_root / "context" / solution / "layouts"
    if layouts_dir.is_dir():
        pattern = str(layouts_dir / f"*{layout_arg}*.json")
        matches = glob.glob(pattern, recursive=False)
        if not matches:
            # Case-insensitive fallback
            matches = [
                str(p) for p in layouts_dir.iterdir()
                if layout_arg.lower() in p.name.lower() and p.suffix == ".json"
            ]
        if matches:
            with open(matches[0], "r", encoding="utf-8") as f:
                return json.load(f)

    # Fall back to running layout_to_summary.py
    summarise_script = agent_root / "scripts" / "layout_to_summary.py"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(summarise_script),
                "--solution", solution,
                "--layout", layout_arg,
                "-o", tmp_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"Error: layout_to_summary.py failed for '{layout_arg}':\n{result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)
        with open(tmp_path, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Step C — Field types from index
# ---------------------------------------------------------------------------

def load_field_types(solution: str, agent_root: Path) -> dict:
    """Parse fields.index and return {table::field_name: field_type} dict."""
    index_path = agent_root / "context" / solution / "fields.index"
    if not index_path.is_file():
        return {}

    with open(index_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse header comment to find column positions
    # Header format: # table|field_name|field_type|...
    col_table = 0
    col_name = 1
    col_type = 2

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip()
            cols = [c.strip().lower() for c in header.split("|")]
            if "table" in cols:
                col_table = cols.index("table")
            for name_alias in ("field_name", "field", "name"):
                if name_alias in cols:
                    col_name = cols.index(name_alias)
                    break
            for type_alias in ("field_type", "type", "data_type"):
                if type_alias in cols:
                    col_type = cols.index(type_alias)
                    break
            break

    fields = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("|")
        if len(parts) <= max(col_table, col_name, col_type):
            continue
        table = parts[col_table].strip()
        name = parts[col_name].strip()
        ftype = parts[col_type].strip().lower()
        if table and name:
            fields[f"{table}::{name}"] = ftype

    return fields


_FM_TO_WEB_TYPE = {
    "text": "text",
    "number": "number",
    "date": "date",
    "timestamp": "datetime-local",
    "time": "time",
    "container": "file",
    "calculation": "text",
    "summary": "text",
}


def collect_layout_fields(summary: dict) -> list:
    """Walk all summary objects (including portal children) and collect field values."""
    fields = []

    def walk_objects(objects):
        for obj in objects:
            if "field" in obj:
                fields.append(obj["field"])
            # Portal children
            if obj.get("type") == "Portal":
                walk_objects(obj.get("objects", []))
            # Button bar children
            for child in obj.get("buttons", []):
                walk_objects([child])

    for part in summary.get("parts", []):
        walk_objects(part.get("objects", []))

    return fields


def build_field_types(summary: dict, solution: str, agent_root: Path) -> dict:
    """Return {field_ref: web_input_type} for all fields used on the layout."""
    index = load_field_types(solution, agent_root)
    layout_fields = collect_layout_fields(summary)
    result = {}
    for ref in layout_fields:
        fm_type = index.get(ref, "text").lower()
        result[ref] = _FM_TO_WEB_TYPE.get(fm_type, "text")
    return result


# ---------------------------------------------------------------------------
# Step D — Relationship context
# ---------------------------------------------------------------------------

def load_portal_relationships(summary: dict, solution: str, agent_root: Path) -> dict:
    """Return relationship info for each portal's relatedTO."""
    index_path = agent_root / "context" / solution / "relationships.index"
    if not index_path.is_file():
        return {}

    with open(index_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse header comment for column positions
    # Common format: # from_to|to_to|from_field|to_field|...
    col_from_to = 0
    col_to_to = 1
    col_from_field = 2
    col_to_field = 3

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip()
            cols = [c.strip().lower() for c in header.split("|")]
            for alias in ("from_to", "from_table_occurrence", "from"):
                if alias in cols:
                    col_from_to = cols.index(alias)
                    break
            for alias in ("to_to", "to_table_occurrence", "to"):
                if alias in cols:
                    col_to_to = cols.index(alias)
                    break
            for alias in ("from_field", "left_field"):
                if alias in cols:
                    col_from_field = cols.index(alias)
                    break
            for alias in ("to_field", "right_field"):
                if alias in cols:
                    col_to_field = cols.index(alias)
                    break
            break

    # Index all relationships
    rel_index = {}  # {to_to: [{from_to, from_field, to_field}]}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("|")
        max_needed = max(col_from_to, col_to_to, col_from_field, col_to_field)
        if len(parts) <= max_needed:
            continue
        from_to = parts[col_from_to].strip()
        to_to = parts[col_to_to].strip()
        from_field = parts[col_from_field].strip() if col_from_field < len(parts) else ""
        to_field = parts[col_to_field].strip() if col_to_field < len(parts) else ""
        if to_to:
            rel_index.setdefault(to_to, []).append({
                "from": from_to,
                "from_field": from_field,
                "to_field": to_field,
            })

    # Collect portals from summary
    portals = []
    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            if obj.get("type") == "Portal":
                related_to = obj.get("relatedTO", "")
                if related_to:
                    portals.append(related_to)

    result = {}
    for related_to in portals:
        rels = rel_index.get(related_to, [])
        if rels:
            r = rels[0]
            join_str = (
                f"{r['from_field']} = {r['to_field']}"
                if r["from_field"] and r["to_field"]
                else ""
            )
            result[related_to] = {
                "from": r["from"],
                "join": join_str,
            }
        else:
            result[related_to] = {"from": "", "join": ""}

    return result


# ---------------------------------------------------------------------------
# Step C2 — Background / structural objects
# ---------------------------------------------------------------------------

# --- Generalized role inference ---
#
# FileMaker developers use wildly different naming conventions across solutions.
# Role inference must work without relying on any specific naming scheme.
# We use three signal layers, in priority order:
#
#   1. Explicit semantic names (developer-assigned object names)
#   2. Style displayName patterns (theme class human-readable names)
#   3. Geometric / structural inference (position, size, stacking order, type)


def infer_role(obj: dict, layout_width: int = 0, layout_height: int = 0) -> str:
    """Infer the semantic role of a layout object using multiple signal layers.

    Returns a role string: 'background', 'sidebar-bg', 'header-bg', 'overlay',
    'developer', 'divider', 'card', 'navigation', 'top-nav', or ''.
    """
    name = obj.get("name", "").lower()
    style_name = obj.get("styleName", "").lower()
    obj_type = obj.get("type", "")
    bounds = obj.get("bounds", [0, 0, 0, 0])
    top, left, bottom, right = bounds
    width = right - left
    height = bottom - top
    hide = obj.get("conditions", {}).get("hideWhen", "").strip()

    # --- Layer 1: Explicit developer names ---
    for source in (name, style_name):
        if not source:
            continue

        # Developer / debug elements (should be excluded from design output)
        if any(kw in source for kw in ("developer", "debug", "dev portal",
                                        "dev field", "dev container")):
            return "developer"

        # Overlay patterns
        if "overlay" in source or "shade" == source:
            return "overlay"

        # Explicit navigation
        if "nav" in source and "background" not in source:
            return "navigation"

        # Explicit sidebar
        if "sidebar" in source:
            return "sidebar-bg"

        # Explicit header
        if "header" in source and obj_type in ("Rectangle", "Group"):
            return "header-bg"

        # Explicit card / panel
        if "card" in source and obj_type == "Rectangle":
            return "card"

        # Explicit background
        if "background" in source:
            return "background"

    # --- Layer 2: Style name patterns ---
    if style_name:
        # Color-named styles (e.g. "c_color_g1", "Color EAB464", "White")
        if (style_name.startswith("c_color") or
                style_name.startswith("color ") or
                style_name in ("white", "black", "gray", "grey")):
            return "background"

        # Shadow / shade patterns
        if any(kw in style_name for kw in ("shadow box", "shade box", "shade")):
            if obj_type == "Rectangle":
                return "background"

    # --- Layer 3: Geometric / structural inference ---
    if obj_type == "Rectangle":
        # Always-hidden rectangles are markers
        if hide == "1":
            return "marker"

        # Full-width rectangle at the top → header background
        if layout_width and width >= layout_width * 0.9 and top == 0 and height < 120:
            return "header-bg"

        # Tall narrow rectangle pinned to left edge → sidebar background
        if left == 0 and width < 300 and layout_height and height > layout_height * 0.6:
            return "sidebar-bg"

        # Full-layout rectangle → background or overlay
        if (layout_width and layout_height and
                width >= layout_width * 0.9 and height >= layout_height * 0.9):
            return "background"

    # Full-layout button with overlay/dismiss script → overlay
    if obj_type in ("Button", "Grouped Button"):
        if (layout_width and layout_height and
                width >= layout_width * 0.8 and height >= layout_height * 0.8):
            return "overlay"

    return ""


def build_structural_objects(summary: dict) -> list:
    """Identify background/structural objects and developer elements.

    Classifies objects using generalized role inference (geometry, stacking,
    style patterns). Works across any FileMaker solution regardless of naming
    conventions.
    """
    structural = []
    layout_width = summary.get("width", 0)
    # Estimate layout height from parts
    layout_height = sum(p.get("height", 0) for p in summary.get("parts", []))

    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            obj_type = obj.get("type", "")

            # Check any object type — overlays can be Buttons, backgrounds can be Rectangles
            role = infer_role(obj, layout_width, layout_height)

            if not role:
                # Only keep rectangles/groups that are large enough to be structural
                if obj_type not in ("Rectangle", "Group", "Line"):
                    continue
                bounds = obj.get("bounds", [0, 0, 0, 0])
                w = bounds[3] - bounds[1]
                h = bounds[2] - bounds[0]
                if w < 30 and h < 30:
                    continue
                # Unclassified but potentially structural — include without a role
            elif role == "marker":
                continue  # Skip always-hidden markers

            entry = {
                "type": obj_type,
                "bounds": obj.get("bounds", []),
            }
            if obj.get("name"):
                entry["name"] = obj["name"]
            if obj.get("styleName"):
                entry["styleName"] = obj["styleName"]
            if obj.get("key"):
                entry["key"] = obj["key"]
            if role:
                entry["role"] = role

            structural.append(entry)

    # Sort by key (stacking order) — lower key = further back = more likely background
    structural.sort(key=lambda o: o.get("key", 9999))

    return structural


# ---------------------------------------------------------------------------
# Step D2 — Navigation inventory
# ---------------------------------------------------------------------------

def build_navigation(summary: dict) -> list:
    """Extract all navigation elements: Button Bars with segments and named nav buttons.

    Returns a list of nav groups, each with a label, position, and items.
    Uses styleName for zone classification when available.
    """
    nav_groups = []

    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            obj_type = obj.get("type", "")

            # Button Bars are navigation structures
            if obj_type == "Button Bar" and obj.get("buttons"):
                bounds = obj.get("bounds", [0, 0, 0, 0])
                items = []
                for btn in obj["buttons"]:
                    label = btn.get("label", "").strip('"')
                    item = {"label": label}
                    if btn.get("script"):
                        item["script"] = btn["script"]
                    if btn.get("name"):
                        item["name"] = btn["name"]
                    hide = btn.get("conditions", {}).get("hideWhen")
                    if hide:
                        item["hideWhen"] = hide
                    items.append(item)

                # Classify using geometry — this is universal regardless of naming
                top, left, bottom, right = bounds
                height = bottom - top
                bar_width = right - left

                # Narrow vertical bar at left edge → sidebar nav
                if left == 0 and right < 120 and height > bar_width:
                    zone = "sidebar"
                # Wide bar near the top → top nav / section switcher
                elif bar_width > height and top < 150:
                    zone = "top-nav"
                # Tall bar in the left portion → sidebar tabs
                elif height > bar_width and right < 300:
                    zone = "sidebar-tabs"
                # Wide bar below the header → toolbar
                elif bar_width > height:
                    zone = "toolbar"
                else:
                    zone = "toolbar"

                group = {
                    "zone": zone,
                    "bounds": bounds,
                    "items": items,
                }
                if obj.get("styleName"):
                    group["styleName"] = obj["styleName"]
                hide_bar = obj.get("conditions", {}).get("hideWhen")
                if hide_bar:
                    group["hideWhen"] = hide_bar
                nav_groups.append(group)

    return nav_groups


# ---------------------------------------------------------------------------
# Step D3 — Action buttons
# ---------------------------------------------------------------------------

def build_action_buttons(summary: dict) -> list:
    """Extract standalone buttons with script triggers (not inside Button Bars or portals).

    Returns a list of button descriptors with label, script, position, and conditions.
    """
    buttons = []

    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            obj_type = obj.get("type", "")

            # Skip portal children and button bar segments — handled elsewhere
            if obj_type in ("Button", "Grouped Button") and obj.get("script"):
                label = obj.get("label", "") or obj.get("name", "")
                if not label:
                    # Use script name as fallback label
                    label = obj["script"]
                btn = {
                    "label": label,
                    "script": obj["script"],
                }
                if obj.get("param"):
                    btn["param"] = obj["param"]
                if obj.get("hasIcon"):
                    btn["hasIcon"] = True
                if obj.get("bounds"):
                    btn["bounds"] = obj["bounds"]
                hide = obj.get("conditions", {}).get("hideWhen")
                if hide:
                    btn["hideWhen"] = hide
                buttons.append(btn)

    return buttons


# ---------------------------------------------------------------------------
# Step D4 — Portal detail
# ---------------------------------------------------------------------------

def build_portal_detail(summary: dict) -> list:
    """Extract detailed portal information including columns and per-row actions."""
    portals = []

    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            if obj.get("type") != "Portal":
                continue

            columns = []
            row_actions = []
            for child in obj.get("objects", []):
                child_type = child.get("type", "")
                if "field" in child:
                    col = {
                        "field": child["field"],
                        "type": child_type,
                    }
                    if child.get("displayStyle"):
                        col["displayStyle"] = child["displayStyle"]
                    if child.get("valueList"):
                        col["valueList"] = child["valueList"]
                    if child.get("conditions", {}).get("conditionalFormats"):
                        col["hasConditionalFormat"] = True
                    columns.append(col)
                elif child_type == "Button" and child.get("script"):
                    row_actions.append({
                        "label": child.get("label", ""),
                        "script": child["script"],
                        "hasIcon": child.get("hasIcon", False),
                    })

            portal = {
                "name": obj.get("name", ""),
                "relatedTO": obj.get("relatedTO", ""),
                "visibleRows": obj.get("visibleRows", 0),
                "bounds": obj.get("bounds", []),
                "columns": columns,
            }
            if row_actions:
                portal["rowActions"] = row_actions
            portals.append(portal)

    return portals


# ---------------------------------------------------------------------------
# Step D5 — Conditional visibility zones
# ---------------------------------------------------------------------------

def build_conditional_zones(summary: dict) -> list:
    """Collect all objects with hideWhen conditions, excluding trivially hidden markers."""
    zones = []
    seen = set()

    def process_obj(obj, context=""):
        hide = obj.get("conditions", {}).get("hideWhen")
        if not hide:
            return
        # Skip objects that are always hidden (markers)
        if hide.strip() == "1":
            return
        label = obj.get("label", "") or obj.get("name", "") or obj.get("text", "") or obj.get("type", "")
        key = f"{label}|{hide}"
        if key in seen:
            return
        seen.add(key)
        entry = {
            "element": label,
            "type": obj.get("type", ""),
            "condition": hide,
        }
        if context:
            entry["context"] = context
        zones.append(entry)

    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            process_obj(obj)
            # Button bar segments
            for btn in obj.get("buttons", []):
                process_obj(btn, context=f"segment of {obj.get('type', 'Button Bar')}")
            # Portal children
            if obj.get("type") == "Portal":
                for child in obj.get("objects", []):
                    process_obj(child, context=f"row of portal {obj.get('name', '')}")

    return zones


# ---------------------------------------------------------------------------
# Step D6 — Layout zones
# ---------------------------------------------------------------------------

def build_layout_zones(summary: dict, navigation: list = None,
                       structural: list = None) -> dict:
    """Identify spatial layout zones from navigation bars, structural objects,
    and their semantic roles.

    Priority for zone detection:
      1. Structural objects with inferred roles (from name/styleName)
      2. Navigation bar positions and classifications
      3. Action button positions for toolbar detection
      4. Text object positions for footer detection

    Returns a dict with identified zones.
    """
    width = summary.get("width", 0)
    parts = summary.get("parts", [])
    if not parts:
        return {}

    body_height = parts[0].get("height", 0) if parts else 0
    zones = {}

    # 1. Use structural objects with roles to seed zones
    for obj in (structural or []):
        role = obj.get("role", "")
        bounds = obj.get("bounds", [0, 0, 0, 0])
        top, left, bottom, right = bounds
        obj_width = right - left
        obj_height = bottom - top
        label = obj.get("name") or obj.get("styleName") or ""

        if role == "sidebar-bg" and "sidebar" not in zones:
            zones["sidebar"] = {
                "width": obj_width,
                "left": left,
                "height": obj_height,
                "description": f"Left sidebar background ({label}), {obj_width}px wide",
            }
        elif role == "header-bg" and "header" not in zones:
            zones["header"] = {
                "height": obj_height,
                "left": left,
                "description": f"Header background ({label}), {obj_height}px tall",
            }
        elif role == "card" and "content_card" not in zones:
            zones["content_card"] = {
                "bounds": bounds,
                "description": f"Content card ({label}), {obj_width}x{obj_height}px at ({top}, {left})",
            }
        elif role == "overlay" and "overlay" not in zones:
            zones["overlay"] = {
                "bounds": bounds,
                "description": f"Overlay backdrop ({label}) — modal/popover shade",
            }

    # 2. Use navigation bars to refine zones
    nav_bars = navigation or []
    sidebar_right = zones.get("sidebar", {}).get("width", 0)
    if "sidebar" in zones:
        sidebar_right = zones["sidebar"].get("left", 0) + zones["sidebar"].get("width", 0)

    header_bottom = zones.get("header", {}).get("height", 0)

    for nav in nav_bars:
        zone = nav.get("zone", "")
        bounds = nav.get("bounds", [0, 0, 0, 0])
        top, left, bottom, right = bounds
        style = nav.get("styleName", "")

        if zone == "sidebar":
            sidebar_right = max(sidebar_right, right)
            if "sidebar" not in zones:
                zones["sidebar"] = {
                    "width": right,
                    "height": bottom,
                    "description": f"Left sidebar navigation ({style}), {right}px wide",
                }
        elif zone == "sidebar-tabs":
            sidebar_right = max(sidebar_right, right)
            if "sidebar" not in zones:
                zones["sidebar"] = {
                    "width": right,
                    "left": left,
                    "height": bottom - top,
                    "description": f"Left sidebar with tabs ({style}), {right}px wide",
                }
            else:
                # Expand sidebar to cover tab bars
                existing = zones["sidebar"]
                new_right = max(existing.get("left", 0) + existing.get("width", 0), right)
                existing["width"] = new_right - existing.get("left", 0)
                sidebar_right = new_right
        elif zone == "top-nav":
            header_bottom = max(header_bottom, bottom)
            if "top_nav" not in zones:
                zones["top_nav"] = {
                    "height": bottom - top,
                    "left": left,
                    "items": len(nav.get("items", [])),
                    "description": f"Top navigation bar ({style}), {bottom - top}px tall, {len(nav.get('items', []))} items",
                }

    # Header zone (combines top_nav and explicit header)
    if header_bottom > 0 and "header" not in zones:
        zones["header"] = {
            "height": header_bottom,
            "left": sidebar_right,
            "description": f"Header area, {header_bottom}px tall, starts at x={sidebar_right}",
        }

    # 3. Toolbar: action buttons between header and content
    toolbar_top = max(header_bottom, 0)
    action_btns_in_toolbar = []
    for part in parts:
        for obj in part.get("objects", []):
            if obj.get("type") in ("Button", "Grouped Button") and obj.get("script"):
                b = obj.get("bounds", [0, 0, 0, 0])
                if toolbar_top <= b[0] < toolbar_top + 80 and b[1] >= sidebar_right:
                    action_btns_in_toolbar.append(obj)
    if action_btns_in_toolbar:
        tb_bottom = max(o["bounds"][2] for o in action_btns_in_toolbar)
        zones["toolbar"] = {
            "top": toolbar_top,
            "height": tb_bottom - toolbar_top,
            "left": sidebar_right,
            "description": f"Toolbar area, {toolbar_top}px to {tb_bottom}px",
        }

    # Content area
    content_top = max(
        zones.get("toolbar", {}).get("top", 0) + zones.get("toolbar", {}).get("height", 0),
        header_bottom,
    )
    if "content" not in zones:
        zones["content"] = {
            "top": content_top,
            "left": sidebar_right,
            "width": width - sidebar_right,
            "description": f"Main content area at ({content_top}, {sidebar_right}), {width - sidebar_right}px wide",
        }

    # 4. Footer: text objects in the bottom 40px
    if body_height and "footer" not in zones:
        footer_objs = [
            obj for part in parts for obj in part.get("objects", [])
            if obj.get("bounds") and obj["bounds"][0] > body_height - 40
            and obj.get("type") in ("Text",)
        ]
        if footer_objs:
            footer_top = min(o["bounds"][0] for o in footer_objs)
            zones["footer"] = {
                "top": footer_top,
                "height": body_height - footer_top,
                "description": f"Footer area, {body_height - footer_top}px tall",
            }

    return zones


# ---------------------------------------------------------------------------
# Step E — Spatial groupings
# ---------------------------------------------------------------------------

def build_spatial_groupings(summary: dict) -> list:
    """Group fields spatially within each layout part.

    Within each part:
      - Collect objects that have a 'field' binding, sorted by top bound.
      - Start a new group when the vertical gap between consecutive objects > 40px.
      - Try to find a label (Text or Button without a field) whose bottom bound
        is within 20px above the group's first field's top bound.
      - Only include groups with 2+ fields.
    """
    groupings = []

    for part in summary.get("parts", []):
        objects = part.get("objects", [])

        # Separate field objects from potential labels
        field_objs = []
        label_objs = []
        for obj in objects:
            if "field" in obj and obj.get("bounds"):
                field_objs.append(obj)
            elif obj.get("type") in ("Text", "Button") and "field" not in obj and obj.get("bounds"):
                label_objs.append(obj)

        if not field_objs:
            continue

        # Sort field objects by top bound
        field_objs.sort(key=lambda o: o["bounds"][0])

        # Group by vertical gap > 40px
        groups = []
        current_group = [field_objs[0]]
        for obj in field_objs[1:]:
            prev_top = current_group[-1]["bounds"][0]
            this_top = obj["bounds"][0]
            if this_top - prev_top > 40:
                groups.append(current_group)
                current_group = [obj]
            else:
                current_group.append(obj)
        groups.append(current_group)

        group_num = 0
        for group in groups:
            if len(group) < 2:
                continue

            group_top = group[0]["bounds"][0]

            # Try to find a label within 20px above the group's first field
            label = None
            for lbl in label_objs:
                lbl_bottom = lbl["bounds"][2]  # [top, left, bottom, right]
                if 0 <= (group_top - lbl_bottom) <= 20:
                    text = lbl.get("text") or lbl.get("label", "")
                    if text:
                        label = text
                        break

            group_num += 1
            if not label:
                label = f"Group {group_num}"

            groupings.append({
                "label": label,
                "fields": [obj["field"] for obj in group],
            })

    return groupings


# ---------------------------------------------------------------------------
# Step F — Theme tokens
# ---------------------------------------------------------------------------

def build_theme(summary: dict, solution: str, agent_root: Path) -> dict:
    """Return theme token dict using ThemeReader, falling back gracefully."""
    # Import from sibling module
    sys.path.insert(0, str(agent_root / "scripts"))
    try:
        from fm_layout_utils import ThemeReader
    except ImportError:
        return {
            "name": summary.get("theme", "unknown"),
            "note": "Run extract_theme.py to populate theme tokens",
        }

    reader = ThemeReader(solution_name=solution, context_dir=str(agent_root / "context"))
    if not reader.available():
        return {
            "name": summary.get("theme", "unknown"),
            "note": "Run extract_theme.py to populate theme tokens",
        }

    tokens = reader.read()
    # Remove css_raw from the brief output (too large)
    tokens.pop("css_raw", None)
    return tokens


# ---------------------------------------------------------------------------
# Step G — Assemble output
# ---------------------------------------------------------------------------

def detect_layout_pattern(summary: dict, portal_detail: list) -> str:
    """Detect common layout patterns from spatial analysis.

    Returns a pattern string: 'master-detail', 'form-with-subrecords',
    'list-only', 'dashboard', or '' (unknown).
    """
    width = summary.get("width", 0)
    if not width or not portal_detail:
        return ""

    # Check for master-detail: a portal on the left (<40% width) with
    # form fields filling the right side
    left_portals = []
    right_portals = []
    for p in portal_detail:
        bounds = p.get("bounds", [0, 0, 0, 0])
        mid_x = (bounds[1] + bounds[3]) / 2
        if mid_x < width * 0.35:
            left_portals.append(p)
        elif mid_x > width * 0.5:
            right_portals.append(p)

    # Count non-portal fields to the right of any left portal
    if left_portals:
        left_right_edge = max(p["bounds"][3] for p in left_portals)
        right_fields = 0
        for part in summary.get("parts", []):
            for obj in part.get("objects", []):
                if obj.get("field") and obj.get("bounds", [0, 0, 0, 0])[1] > left_right_edge:
                    right_fields += 1
        if right_fields >= 4:
            return "master-detail"

    # Form with subrecords: form fields above, portal(s) below
    if right_portals and not left_portals:
        return "form-with-subrecords"

    return ""


def build_intent(layout_type: str, summary: dict,
                 portal_detail: list = None) -> str:
    """Generate a natural-language intent string."""
    base_table = summary.get("table", "Unknown")

    field_refs = collect_layout_fields(summary)
    field_count = len(set(field_refs))

    portal_count = 0
    for part in summary.get("parts", []):
        for obj in part.get("objects", []):
            if obj.get("type") == "Portal":
                portal_count += 1

    portal_str = ""
    if portal_count == 1:
        portal_str = ", 1 portal"
    elif portal_count > 1:
        portal_str = f", {portal_count} portals"

    pattern = detect_layout_pattern(summary, portal_detail or [])
    pattern_str = f" [{pattern}]" if pattern else ""

    field_str = "1 field" if field_count == 1 else f"{field_count} fields"
    return f"{layout_type.title()} view for {base_table} ({field_str}{portal_str}){pattern_str}"


# ---------------------------------------------------------------------------
# Step H — Design prompt generation
# ---------------------------------------------------------------------------

def build_design_prompt(brief: dict) -> str:
    """Generate a constraint-based natural language prompt for a design service.

    The prompt preserves every element from the original layout and asks only
    for visual modernization — not structural reimagination.
    """
    lines = []
    name = brief.get("layout_name", "Unknown")
    layout_type = brief.get("layout_type", "detail")
    width = brief.get("summary", {}).get("width", 0)

    # 1. Intent declaration
    intent = brief.get("intent", "")
    # Extract pattern from intent if present
    pattern = ""
    if "[master-detail]" in intent:
        pattern = "This is a master-detail layout: a record list on the left, detail form on the right. Preserve this split-panel structure."
    elif "[form-with-subrecords]" in intent:
        pattern = "This is a form with subrecord portals below. Preserve the form-above, table-below structure."

    lines.append(
        f"Modernize the visual styling of an existing {layout_type} layout called "
        f'"{name}" ({width}px wide). '
        "Preserve ALL elements, their labels, and their approximate spatial "
        "relationships. Do not remove, consolidate, or reorganize elements. "
        "Only improve typography, spacing, color palette, and component styling "
        "to achieve a clean, modern SaaS aesthetic."
    )
    if pattern:
        lines.append(f"\n{pattern}")
    lines.append("")

    # 2. Layout zones
    zones = brief.get("layout_zones", {})
    if zones:
        lines.append("## Layout Zones")
        for zone_name, zone_info in zones.items():
            lines.append(f"- **{zone_name.replace('_', ' ').title()}**: {zone_info.get('description', '')}")
        lines.append("")

    # 2b. Background / structural objects (inform the color/styling context)
    structural = brief.get("structural_objects", [])
    # Separate developer elements from user-facing structural objects
    dev_objs = [s for s in structural if s.get("role") == "developer"]
    bg_objs = [s for s in structural
               if s.get("role") and s["role"] not in ("developer", "marker")]
    if bg_objs:
        lines.append("## Background & Structural Elements (preserve color zones)")
        for obj in bg_objs:
            label = obj.get("name") or obj.get("styleName") or obj["type"]
            role = obj.get("role", "")
            bounds = obj.get("bounds", [])
            role_str = f" [{role}]" if role else ""
            lines.append(f'- "{label}"{role_str} at {bounds}')
        lines.append("")
    if dev_objs:
        lines.append(f"## Developer Elements ({len(dev_objs)} objects — exclude from design)")
        lines.append("_These are developer/debug tools not visible to end users._")
        lines.append("")

    # 3. Navigation
    navigation = brief.get("navigation", [])
    if navigation:
        lines.append("## Navigation (preserve all items and labels)")
        for nav in navigation:
            zone = nav.get("zone", "unknown")
            items = nav.get("items", [])
            labels = [item.get("label", "?") for item in items]
            lines.append(f"- **{zone.replace('-', ' ').title()}** ({len(items)} items): {', '.join(labels)}")
            if nav.get("hideWhen"):
                lines.append(f"  - _Conditional: this bar is hidden when {nav['hideWhen']}_")
            # Note any conditionally hidden segments
            hidden_items = [i for i in items if i.get("hideWhen")]
            if hidden_items:
                for hi in hidden_items:
                    lines.append(f"  - _\"{hi['label']}\" is hidden when {hi['hideWhen']}_")
        lines.append("")

    # 4. Action buttons
    action_buttons = brief.get("action_buttons", [])
    if action_buttons:
        lines.append("## Action Buttons (preserve all)")
        for btn in action_buttons:
            label = btn.get("label", "(icon only)")
            icon = " [has icon]" if btn.get("hasIcon") else ""
            hide = f" — hidden when {btn['hideWhen']}" if btn.get("hideWhen") else ""
            lines.append(f'- "{label}"{icon}{hide}')
        lines.append("")

    # 5. Non-portal fields, grouped by spatial zone
    # Determine which fields are in the content area vs header/toolbar
    portal_fields = set()
    for p in brief.get("portal_detail", []):
        for col in p.get("columns", []):
            portal_fields.add(col.get("field", ""))

    # Walk the summary to get field positions
    content_top = brief.get("layout_zones", {}).get("content", {}).get("top", 0)
    header_area_fields = []
    content_area_fields = []
    for part in brief.get("summary", {}).get("parts", []):
        for obj in part.get("objects", []):
            field_ref = obj.get("field", "")
            if not field_ref or field_ref in portal_fields:
                continue
            bounds = obj.get("bounds", [0, 0, 0, 0])
            field_entry = field_ref
            # Try to find a nearby label (Text object above this field)
            for lbl_obj in part.get("objects", []):
                if lbl_obj.get("type") != "Text" or not lbl_obj.get("text"):
                    continue
                lb = lbl_obj.get("bounds", [0, 0, 0, 0])
                # Label should be directly above or overlapping horizontally
                if (0 <= bounds[0] - lb[2] <= 40 and
                        abs(lb[1] - bounds[1]) < 50):
                    field_entry = f"{field_ref} (label: \"{lbl_obj['text']}\")"
                    break
            if bounds[0] < content_top:
                header_area_fields.append(field_entry)
            else:
                content_area_fields.append(field_entry)

    if header_area_fields:
        lines.append("## Header/Toolbar Fields")
        for ref in header_area_fields:
            lines.append(f"- {ref}")
        lines.append("")
    if content_area_fields:
        lines.append("## Content Area Fields (form fields)")
        for ref in content_area_fields:
            lines.append(f"- {ref}")
        lines.append("")

    # 6. Portal / data table
    portal_detail = brief.get("portal_detail", [])
    if portal_detail:
        lines.append("## Data Tables (portals — preserve column order and row actions)")
        for portal in portal_detail:
            pname = portal.get("name", "")
            if not pname:
                # Derive name from relatedTO or first field
                related = portal.get("relatedTO", "")
                if related:
                    pname = f"[{related}]"
                elif portal.get("columns"):
                    first_field = portal["columns"][0].get("field", "")
                    table = first_field.split("::")[0] if "::" in first_field else "unnamed"
                    pname = f"[{table} list]"
                else:
                    pname = "[unnamed portal]"
            rows = portal.get("visibleRows", 0)
            lines.append(f"### {pname} ({rows} visible rows)")
            lines.append("Columns:")
            for col in portal.get("columns", []):
                field = col["field"].split("::")[-1] if "::" in col["field"] else col["field"]
                ctype = col.get("type", "")
                extras = []
                if col.get("displayStyle"):
                    extras.append(col["displayStyle"])
                if col.get("valueList"):
                    extras.append(f"value list: {col['valueList']}")
                if col.get("hasConditionalFormat"):
                    extras.append("has conditional formatting")
                extra_str = f" ({', '.join(extras)})" if extras else ""
                lines.append(f"  - {field} [{ctype}]{extra_str}")
            if portal.get("rowActions"):
                lines.append("Per-row actions:")
                for action in portal["rowActions"]:
                    label = action.get("label", "(icon)")
                    icon = " [icon]" if action.get("hasIcon") else ""
                    lines.append(f'  - "{label}"{icon}')
            lines.append("")

    # 7. Conditional visibility summary
    conditional = brief.get("conditional_zones", [])
    if conditional:
        lines.append("## Conditional Visibility (design must accommodate mode switching)")
        for cz in conditional:
            lines.append(f"- {cz['type']} \"{cz['element']}\" — hidden when: {cz['condition']}")
        lines.append("")

    # 8. Theme guidance
    theme = brief.get("theme", {})
    if isinstance(theme, dict) and theme.get("colors"):
        lines.append("## Theme")
        if theme.get("name"):
            lines.append(f"- Theme name: {theme['name']}")
        colors = theme.get("colors", {})
        if colors:
            color_items = [f"{k}: {v}" for k, v in list(colors.items())[:6]]
            lines.append(f"- Colors: {', '.join(color_items)}")
        fonts = theme.get("fonts", {})
        if fonts:
            lines.append(f"- Fonts: heading={fonts.get('heading', 'inherit')}, body={fonts.get('body', 'inherit')}")
        lines.append("")

    # 9. Design direction
    lines.append("## Modernization Direction")
    lines.append("- Clean, modern SaaS aesthetic (Notion/Linear/Asana style)")
    lines.append("- Improve visual hierarchy with better typography and spacing")
    lines.append("- Use subtle hover states on interactive elements")
    lines.append("- Apply consistent border radii and shadow depths")
    lines.append("- Maintain the existing layout structure — sidebar, header tabs, content area")
    lines.append("- Do NOT add new elements, remove existing elements, or reorganize the layout")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrich a FileMaker layout summary with semantic design context."
    )
    parser.add_argument(
        "layout",
        help="Layout name or path to an existing summary JSON file",
    )
    parser.add_argument(
        "--solution",
        required=True,
        help="Solution name (used to locate context files)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: agent/context/{solution}/layouts/{layout_name}_brief.json)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Minimal JSON (no indentation)",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Also generate the constraint-based design prompt (written to {output}_prompt.txt)",
    )
    args = parser.parse_args()

    agent_root = get_agent_root()
    indent = None if args.compact else 2

    # Step A — Locate summary
    summary = locate_summary(args.layout, args.solution, agent_root)

    layout_name = summary.get("layout", args.layout)
    layout_id = summary.get("id", 0)

    # Step B — Classify layout type
    sys.path.insert(0, str(agent_root / "scripts"))
    try:
        from fm_layout_utils import classify_layout_type
    except ImportError:
        def classify_layout_type(s):
            return "detail"

    layout_type = classify_layout_type(summary)

    # Step C — Field types
    field_types = build_field_types(summary, args.solution, agent_root)

    # Step D — Portal relationships
    portal_relationships = load_portal_relationships(summary, args.solution, agent_root)

    # Step C2 — Structural / background objects
    structural = build_structural_objects(summary)

    # Step D2 — Navigation inventory
    navigation = build_navigation(summary)

    # Step D3 — Action buttons
    action_buttons = build_action_buttons(summary)

    # Step D4 — Portal detail
    portal_detail = build_portal_detail(summary)

    # Step D5 — Conditional visibility
    conditional_zones = build_conditional_zones(summary)

    # Step D6 — Layout zones (uses navigation + structural objects for zone detection)
    layout_zones = build_layout_zones(summary, navigation, structural)

    # Step E — Spatial groupings
    groupings = build_spatial_groupings(summary)

    # Step F — Theme tokens
    theme = build_theme(summary, args.solution, agent_root)

    # Step G — Assemble
    intent = build_intent(layout_type, summary, portal_detail)

    brief = {
        "generated_by": "layout_to_brief.py",
        "layout_name": layout_name,
        "layout_id": layout_id,
        "solution": args.solution,
        "layout_type": layout_type,
        "intent": intent,
        "theme": theme,
        "layout_zones": layout_zones,
        "structural_objects": structural,
        "navigation": navigation,
        "action_buttons": action_buttons,
        "portal_detail": portal_detail,
        "conditional_zones": conditional_zones,
        "field_types": field_types,
        "portal_relationships": portal_relationships,
        "groupings": groupings,
        "summary": summary,
    }

    output_str = json.dumps(brief, indent=indent, ensure_ascii=False)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        safe_name = layout_name.replace("/", "-").replace("\\", "-")
        out_dir = agent_root / "context" / args.solution / "layouts"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{safe_name}_brief.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_str + "\n")

    print(f"Brief written to {out_path}")
    print(f"  Layout type: {layout_type}")
    print(f"  Intent: {intent}")
    print(f"  Navigation groups: {len(navigation)}  Action buttons: {len(action_buttons)}")
    print(f"  Portals: {len(portal_detail)}  Conditional zones: {len(conditional_zones)}")
    print(f"  Fields: {len(field_types)}  Groups: {len(groupings)}")

    # Step H — Generate design prompt
    if args.prompt:
        prompt_text = build_design_prompt(brief)
        prompt_path = out_path.with_suffix(".prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_text + "\n")
        print(f"  Design prompt written to {prompt_path}")


if __name__ == "__main__":
    main()
