# FileMaker Setup

This folder contains the FileMaker artifacts that connect your solution to the agentic-fm toolchain.

| File               | Purpose                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| `Context.fmfn`     | Custom function source — install into your FileMaker solution                                           |
| `context.xml`      | fmxmlsnippet format of the `Context` custom function — alternative install via `clipboard.py`           |
| `agentic-fm.fmp12` | Pre-built FileMaker file containing the companion script group — open and copy/paste into your solution |
| `agentic-fm.xml`   | Companion script group in fmxmlsnippet format — alternative install via `clipboard.py`                  |

---

## Dependencies

### FileMaker Pro 21.0+

The minimum version is **21.0**. Earlier versions lack:

- `GetTableDDL` — used by `Context.fmfn` to discover foreign key relationships
- `While` — used by `Context.fmfn` for iteration
- `Create Data File` / `Open Data File` / `Write to Data File` / `Close Data File` — used by the **Push Context** script to write `CONTEXT.json` to disk

### Companion Server

The **Explode XML** companion script calls `agent/scripts/companion_server.py` — a lightweight HTTP server — to run shell commands from FileMaker without any third-party plugin. FileMaker communicates with it via `Insert from URL`.

**Start the server before running Explode XML:**

```bash
python3 agent/scripts/companion_server.py
```

The server listens on port 8765 by default and uses only Python stdlib — no virtualenv is required. Keep it running in a terminal while you work.

The other two companion scripts (**Get agentic-fm path** and **Push Context**) use only native FileMaker steps and do not require the companion server.

### fm-xml-export-exploder

A Rust binary that parses FileMaker XML exports into individual files. Used by both the **Explode XML** companion script and by `fmparse.sh` when called from the terminal.

**Installation:**

1. Download the macOS binary from the [releases page](https://github.com/bc-m/fm-xml-export-exploder/releases/latest). Bleeding edge versions can be found [here](https://github.com/petrowsky/fm-xml-export-exploder/releases)
2. On first run, macOS Gatekeeper will block it. Right-click the binary and choose **Open** once to clear the restriction. You will need to authorize its execution within **System Settings -> Privacy & Security**.
3. Create `~/bin/` if it does not exist:
   ```bash
   mkdir -p ~/bin
   ```
4. Move the binary there and make it executable:
   ```bash
   mv fm-xml-export-exploder ~/bin/
   chmod +x ~/bin/fm-xml-export-exploder
   ```

> **Why `~/bin`?** The **Explode XML** companion script passes `~/bin/fm-xml-export-exploder` as the `FM_XML_EXPLODER_BIN` environment variable to `fmparse.sh`. If you want to place the binary elsewhere, open the **Explode XML** script in FileMaker and update the `Set Variable [$payload ; JSONSetElement ( "{}" ;[ "exploder_bin_path" ;  ...]` step to reflect your actual path.

When calling `fmparse.sh` directly from the terminal you can also override the path via the environment variable:

```bash
FM_XML_EXPLODER_BIN=/your/path/fm-xml-export-exploder ./fmparse.sh -s "My Solution" /path/to/export.xml
```

### Python 3

Required for `agent/scripts/clipboard.py` (loading snippets onto the FileMaker clipboard), `agent/scripts/validate_snippet.py` (post-generation validation), and `agent/scripts/companion_server.py` (shell execution server). All three use Python stdlib only — no virtualenv is required.

> Note: You are not required to use the clipboard.py with python3. If you are already using another tool such as the MBS or BaseElements plug-in then those methods will still function. The convenience of the clipboard.py and python3 method is such that the agent will automatically put the code it creates onto the clipboard.

Python 3 ships with macOS or can be installed via [Homebrew](https://brew.sh):

```bash
brew install python
```

Run scripts directly — no activation step needed:

```bash
python3 agent/scripts/clipboard.py write filemaker/agentic-fm.xml
python3 agent/scripts/companion_server.py
```

### xmllint

Required by `fmcontext.sh` to extract data from the exploded XML. Ships with macOS as part of libxml2. On Linux:

```bash
apt-get install libxml2-utils
```

---

## Install as an add-on (recommended)

The explode and OData parts of the bundle ship as one FileMaker add-on, `agentic-fm`: the package folder
`filemaker/addon/agentic-fm/` (what FileMaker loads from `AddonModules`) and the same package as one file,
`filemaker/addon/agentic-fm.fmaddon` (double-click to install it on a Mac). It holds `Get agentic-fm path`, `AGFM Start`, `AGFM Explode`, `AGFM Version`,
`AGFM Choose Folder`, `Explode XML`, `Push Context` with the `Context` custom function, the `OData` folder and
`Agentic-fm Debug`, and since 1.1.0 `AGFM Explode Solution` and `AGFM Agent` (list in `filemaker/addon/manifest.json`). The web viewer scripts are not in the add-on; if you use the editor, paste
`filemaker/addon/agentic-fm-webviewer.xml` (only `Agentic-fm Webviewer`, `Menu` and `Paste`; their calls into the
add-on are by name) — never the full `agentic-fm.xml` on top of the add-on, which would duplicate its scripts. Updating a solution is uninstall + install; nothing is
pasted by hand.

Building the package (maintainers): `python3 agent/scripts/build_addon_snippet.py` writes
`filemaker/addon/agentic-fm-addon.xml` (the bundle restricted to the manifest). Paste `filemaker/context.xml`
and that snippet into the template `filemaker/addon/template/agentic-fm.fmp12` (a blank file: the add-on takes the
file's name; table `AGFM` with `PrimaryKey` only, no other layout), do the template steps below (layout `AGFM Explode`, draggable button), and run `Save a Copy as Add-on Package` (Replace UUIDs off) from a script
prefixed `__FMAddonTemplateDirectives_`. Then `python3 agent/scripts/build_addon_snippet.py --package` imports
the built package from `AddonModules`, replaces FileMaker's default metadata ("Created by Claris", placeholder
description) with the manifest's and repacks `agentic-fm.fmaddon` (`xar --distribution`: no user, group or extended
attributes). It also writes into **your** `AddonModules`: the edited `info*.json` go back into
`AddonModules/agentic-fm/` and the archive is copied next to it, so this Mac's install dialog shows the same metadata
after a FileMaker restart. Bump `AGFM Version` and `manifest.json` together.

### Template steps for 1.1.0 (maintainers, in FileMaker)

After pasting the snippet, the template needs two layouts:

1. **Layout `AGFM Explode`** on table `AGFM`, with one web viewer named `agfm` (Inspector → Position → Name).
   Turn **Allow JavaScript to perform FileMaker scripts** ON; leave its URL empty, `AGFM Explode Solution` sets it.
   The script opens this layout by name in a card window, so it must be named exactly that.
2. **Layout `__FMAddonTemplateDirectives_en`** with exactly **one** object group: a button «agentic-fm» whose
   action is `Perform Script [ AGFM Explode Solution ]` (no parameter). That group is the add-on's draggable
   object; the layout itself is not packaged.

Then run `Save a Copy as Add-on Package` and `python3 agent/scripts/build_addon_snippet.py --package`. The
package step now fails with «the package has no draggable object» when the built `template.xml` has an empty
`<Directives/>`. It only checks that `<Directives>` holds a layout object; make sure the layout has exactly one group.

### One add-on per solution (user guide)

A solution can span several FileMaker files. You install the add-on **once**, in the main file; every other file
carries only the script `AGFM Agent`.

- **Main file** = the file where you install the add-on. Drag the add-on from the Add-ons tab onto a developer
  layout: you get the button «agentic-fm», which opens the card (list of files, Export, Check).
- **Each secondary file** needs `AGFM Agent`: in Agentic-FM-APP use «Copiar AGFM Agent» (to update it later,
  «Copiar pasos (actualizar)»: select all the steps of the existing script and paste). Nothing else is pasted.
- **Authorise the main file in each secondary file**: Manage Security → Security Settings → File Access
  (add the main file). Without it the card reports error 825 for that file.
- **Data sources:** the main file must have a FileMaker data source for every secondary file. The card lists any
  file that has none: add a data source with that name in the main file (Manage → External Data Sources).
- **Debug in secondary files:** point your Debug callers at `AGFM Agent` by name with
  `{"mode": "debug", …}` (`Perform Script` by calculated name, parameter JSON).
- `AGFM Agent` needs full-access privileges in each file (card error 9: «sin acceso total»).

### Install steps

1. **Make the package available on this Mac.** Agentic-FM-APP copies it to
   `~/Library/Application Support/FileMaker/Extensions/AddonModules/`. Without the app, double-click
   `filemaker/addon/agentic-fm.fmaddon`.
2. **Coming from a pasted copy? Delete it first.** Remove the pasted `agentic-fm` script folder and the
   `Context` custom function **before** installing. Installed over a pasted copy, the add-on's scripts arrive
   renamed (`Explode XML 2`, …) and the old `Context` is kept instead of the add-on's.
3. **Install.** Layout mode → Add-ons tab → Install Add-on → **select `agentic-fm` and press Return**. With
   several add-ons in the list, clicking one and pressing *Choose* can install the first add-on of the list
   instead.
4. **Call agentic-fm scripts by name only.** Your own scripts must call agentic-fm scripts with
   `Perform Script` by calculated name (e.g. `"Agentic-fm Debug"`), and your calculations must not use
   `Context ( )`. Uninstall + install gives the add-on's objects new internal IDs: by-reference calls and
   custom-function uses in your solution then show `<unknown>` / `<Function Missing>`; by-name calls keep
   working.
5. **Update** = right-click the add-on → Uninstall Add-on, then install the new version (an installed add-on
   cannot be installed again on top).
6. **Start-up (optional).** `OnFirstWindowOpen` may call `AGFM Start` by name: it is silent and returns JSON
   (`ok`, `mode`, `repo_path`, `addon_version`, `error`).

The repo path comes from Agentic-FM-APP (`GET /config`, which knows the clone of each registered solution), so
the per-account `If Get ( AccountName )` blocks of older setups are no longer needed. The companion host is
`$$AGENTIC.FM.COMPANION.IP` (default `localhost`).

## Installation Steps (manual install, without the add-on)

For the full first-run workflow, see the main [QUICKSTART.md](../QUICKSTART.md#-one-time-filemaker-setup), especially the `One-time FileMaker setup` section.

### 1. Install the Context custom function

1. Open your FileMaker solution in FileMaker Pro.
2. Go to **File > Manage > Custom Functions**.
3. Click **New** and create a function named `Context` with one parameter: `task` (type: Text).
4. Copy the entire contents of `filemaker/Context.fmfn` and paste it into the calculation editor.
5. Click **OK** and save.

### 2. Install the companion scripts

Choose either option:

**Option A — Open the included .fmp12 file (fastest)**

Open `filemaker/agentic-fm.fmp12` in FileMaker Pro. Copy the **agentic-fm** script folder from its Script Workspace and paste it directly into your solution's Script Workspace.

**Option B — Install via clipboard**

Load `filemaker/agentic-fm.xml` onto the FileMaker clipboard using `clipboard.py`, then paste into the Script Workspace:

```bash
python3 agent/scripts/clipboard.py write filemaker/agentic-fm.xml
```

Switch to FileMaker, open the **Script Workspace** (**Scripts > Script Workspace**), click in the script list, and press **⌘V**. A folder named **agentic-fm** containing the scripts will appear.

> If you already use another method of clipboard manipulation (e.g. MBS/BaseElements plug-in, AppleScript, et al), `clipboard.py` may be optional here.

> Valuable info: MBS added automatic clipboard conversion for FileMaker XML in version `15.4`; with that converter enabled, the plugin can recognize valid `fmxmlsnippet` text on the clipboard and make it pasteable in FileMaker in the background. See [Copy and paste XML in FileMaker](https://www.mbsplugins.de/archive/2025-08-29/Copy_and_paste_XML_in_FileMake) and [MBS FileMaker Plugin, version 15.4pr4](https://www.mbsplugins.de/archive/2025-08-25/MBS_FileMaker_Plugin_version_1).

### 3. Configure the repo path

**Get agentic-fm path** asks Agentic-FM-APP for this file's clone (`GET /config`) and stores it in `$$AGENTIC.FM`; it shows no dialog and returns JSON (`ok`, `source`, `repo_path`, `error`). When the app does not answer (not running, or the classic companion, which has no `/config`), **Explode XML** and **Push Context** offer a folder picker (`AGFM Choose Folder`): select the root of the agentic-fm repo folder. The path lasts for the session.

### 3.5. Start the companion server

Before running **Explode XML**, start `companion_server.py` in a terminal and leave it running:

```bash
python3 agent/scripts/companion_server.py
```

This server listens on port 8765 and handles the shell command that **Explode XML** issues via `Insert from URL`. You will need to restart it each time you open a new terminal session.

### 4. Run Explode XML

Run the **Explode XML** script to perform the first Save as XML export and populate `agent/xml_parsed/`. Re-run it any time the solution schema or scripts change.

> The script derives the `fmparse.sh` path from the `$$AGENTIC.FM` global variable set by **Get agentic-fm path**, so the repo can be located anywhere on disk.

### 5. Push Context before each AI session

Navigate to the layout you are working on and run the **Push Context** script. A dialog will prompt you for a task description. After you click OK, the context is written to `agent/CONTEXT.json` and you are ready to work with AI.

---

## Optional: agentic-fm web viewer

The agentic-fm web viewer is a browser-based Monaco editor embedded directly in FileMaker. It provides a three-panel interface — script editor, XML preview, and AI chat — without leaving FileMaker Pro.

### Adding the web viewer to a layout

Add a **WebViewer** object to any layout and set its URL to `http://localhost:8080` (the Vite dev server). Name the object exactly **`agentic-fm`** — this name is required for the bridge script and custom menu integration to work correctly.

The web viewer works on any layout, but a **dedicated layout** is strongly recommended:

- Place only the web viewer object on the layout with no other interactive objects
- Make the layout window **resizable** so you can expand the editor to a comfortable size
- A single-object layout ensures the custom menu set (assigned per-layout) applies consistently whenever the editor is in use

See `webviewer/WEBVIEWER_INTEGRATION.md` for full setup and development workflow details.

### Custom menu integration (optional)

The `filemaker/custom_menu/` folder contains an optional custom menu set that adds five editor-aware menus to the layout hosting the web viewer. These menus expose keyboard shortcuts for common Monaco editor actions (comment toggle, indent, move line, find, and more) without requiring the developer to remember key bindings.

See `filemaker/custom_menu/README.md` for the integration steps.

---

## Dependency Summary

| Dependency             | Required By                                            | Where to Get                                                                      |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------------------------------------------- |
| FileMaker Pro 21.0+    | Everything                                             | [claris.com](https://www.claris.com)                                              |
| companion_server.py    | Explode XML script                                     | Included — `python3 agent/scripts/companion_server.py`                            |
| fm-xml-export-exploder | Explode XML script, fmparse.sh                         | [GitHub releases](https://github.com/bc-m/fm-xml-export-exploder/releases/latest) |
| Python 3               | clipboard.py, validate_snippet.py, companion_server.py | Ships with macOS or `brew install python`                                         |
| xmllint                | fmcontext.sh                                           | Ships with macOS; `apt-get install libxml2-utils` on Linux                        |
