# agentic-fm Quickstart

## What this does

agentic-fm gives an AI agent (Claude Code, Cursor, etc.) structured knowledge of your FileMaker solution — schema, scripts, layouts, relationships — so it can generate reliable `fmxmlsnippet` code that pastes directly into the Script Workspace. You describe what you want; the agent writes the XML; you paste it into FileMaker.

---

## Prerequisites

1. **FileMaker Pro 21.0+** — earlier versions lack required steps (`GetTableDDL`, `While`, data file steps)
2. **MBS FileMaker Plugin** — required for the in-FileMaker "Explode XML" automation. Free trial available at [monkeybreadsoftware.com/filemaker](https://www.monkeybreadsoftware.com/filemaker/)
3. **fm-xml-export-exploder** — Rust binary that parses FileMaker XML exports. Download from [GitHub releases](https://github.com/bc-m/fm-xml-export-exploder/releases/latest)
4. **Python 3** — ships with macOS, or `brew install python`
5. **Claude Code** (or another AI agent) — this guide uses `claude` in the terminal

---

## Install

### 1. Clone the repo

```bash
git clone https://github.com/agentic-fm/agentic-fm.git
cd agentic-fm
```

### 2. Install fm-xml-export-exploder

```bash
mkdir -p ~/bin
mv ~/Downloads/fm-xml-export-exploder ~/bin/
chmod +x ~/bin/fm-xml-export-exploder
```

On first run, macOS Gatekeeper will block it. Right-click the binary in Finder and choose **Open** once to clear the restriction.

### 3. Activate the Python virtual environment

```bash
source .venv/bin/activate
```

Verify it works:

```bash
python agent/scripts/clipboard.py --help
```

---

## One-time FileMaker setup

Do this once per solution.

### 1. Install the Context custom function

1. Open your solution in FileMaker Pro
2. Go to **File > Manage > Custom Functions**
3. Click **New**, name it `Context`, add one parameter named `task` (Text)
4. Paste the contents of `filemaker/Context.fmfn` into the calculation editor
5. Click **OK**

### 2. Install the companion scripts

```bash
source .venv/bin/activate
python agent/scripts/clipboard.py write filemaker/agentic-fm.xml
```

Switch to FileMaker, open **Scripts > Script Workspace**, click in the script list, and press **Cmd+V**. A folder named **agentic-fm** with three scripts will appear.

### 3. Configure the repo path

Run **Get agentic-fm path** from the Scripts menu. A folder picker appears — select the root of this repo. The path is stored for the session.

> Add a call to this script in your solution's startup script so it runs automatically on launch.

### 4. Explode the XML

Run **Explode XML** from the Scripts menu. This exports your solution's XML and populates `agent/xml_parsed/`. Re-run it any time the schema or scripts change.

---

## Every session

Each time you sit down to write scripts:

1. **Navigate** to the layout you are working on in FileMaker
2. **Run "Push Context"** from the Scripts menu — enter a plain-English task description when prompted. This writes `agent/CONTEXT.json` with the fields, layouts, relationships, and scripts scoped to your current task.
3. **Open Claude Code** in the agentic-fm directory and describe what you want
4. The agent generates an `fmxmlsnippet` file in `agent/sandbox/`, validates it, and loads it onto the clipboard
5. **Switch to FileMaker**, open the Script Workspace, position your cursor, and press **Cmd+V**

---

## Your first script

This example creates a simple script that sets a status field and commits the record.

### Step 1 — Push context

In FileMaker, navigate to your Invoices layout. Run **Push Context** and enter:

```
Set the Status field to "Sent" and commit the record
```

### Step 2 — Run the agent

```bash
cd /path/to/agentic-fm
source .venv/bin/activate
claude
```

In the Claude Code prompt:

```
Generate the script described in CONTEXT.json
```

The agent will:
- Read `agent/CONTEXT.json` for your field IDs
- Look up the correct XML structure for each step
- Write the snippet to `agent/sandbox/`
- Validate it with `validate_snippet.py`
- Load it onto the clipboard with `clipboard.py`

### Step 3 — Paste into FileMaker

Switch to FileMaker, open the Script Workspace, create a new script (or open an existing one), click where you want the steps inserted, and press **Cmd+V**.

### Step 4 — Iterate

If you want changes, describe them in the Claude Code session:

```
Add error handling around the Commit Records step
```

The agent updates the file, re-validates, and reloads the clipboard. Paste again.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `clipboard.py` not found | Run `source .venv/bin/activate` first |
| Explode XML fails | Confirm MBS Plugin is installed and `~/bin/fm-xml-export-exploder` exists and is executable |
| CONTEXT.json is empty or missing | Run **Push Context** again from the correct layout |
| Paste does nothing in FileMaker | Confirm the clipboard was loaded — the agent logs `clipboard.py write` output; check for errors |
