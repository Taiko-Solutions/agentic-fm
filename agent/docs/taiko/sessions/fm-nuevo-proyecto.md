# Configurar agentic-fm para un cliente nuevo (Taiko)

> Para el agente, tras clonar (la skill `fm-nuevo-proyecto` hace: SSH, `git clone -b taiko git@GIT:Taiko-Solutions/agentic-fm.git`, `git checkout -b trabajo`). Pide los datos que falten de uno en uno. **[app]** = lo asumirá Agentic-FM-APP.

Datos: carpeta (`~/GITs/<Cliente>/agentic-fm`), ficheros `.fmp12` (sin extensión), servidor FM (`https://…`), ¿OData habilitado?

1. **Hook y reglas de rutas (obligatorio):** `bash agent/scripts/install-hooks.sh`; verifica `ls -la "$(git rev-parse --git-common-dir)/hooks/pre-push"`. Sin hook no se continúa.
2. **Scripts de terminal [app]:** symlinks de `agent/scripts/bin/` a `~/bin` (`agentic-fm-start`, `-update`, `-sync`, `-safe-push`); `~/.zshrc` con `export PATH="$HOME/bin:$PATH"`.
3. **Dependencias:** `python3 --version`; `~/bin/fm-xml-export-exploder` **0.7.1** (https://github.com/bc-m/fm-xml-export-exploder/releases/latest, aarch64-apple-darwin; las ≥ 0.6.1 escriben `custom_functions/` y `value_lists/` en vez de `*_stubs/`); `xmllint`; `node ≥ 18` (webviewer opcional).
4. **Directorios:** `mkdir -p agent/xml_parsed agent/context agent/sandbox agent/debug agent/config` (todos ignorados por git y bloqueados por el hook).
5. **`agent/config/removals.json`** (scripts/CFs con credenciales que no deben quedar en el explode): pregunta qué objetos; IDs mejor que nombres. Plantilla: `agent/config/removals.json.example`.
6. **`agent/config/automation.json`:** `companion_url` = `http://127.0.0.1:8765` (local por defecto; FMS→companion es opt-in), bloque `odata` por solución con `base_url`, `database`, `username`, `password`, `script_bridge: "AGFMScriptBridge"`, y `explode_xml` con `repo_path`/`export_path`. Pide las credenciales OData. Plantilla: `agent/config/automation.json.example`.
7. **Companion [app]:** `curl -s http://127.0.0.1:8765/health`; si no responde `agentic-fm-start`; si no existe el runtime, `agentic-fm-update ~/GITs/agentic-fm`.
8. **En FileMaker, por cada fichero [app]:** (a) CF `Context`: `python3 agent/scripts/clipboard.py write filemaker/Context.fmfn` → Gestionar → Funciones personalizadas → ⌘V; (b) los 10 scripts: `python3 agent/scripts/clipboard.py write filemaker/agentic-fm.xml` → Script Workspace → ⌘V; (c) ejecutar *Get agentic-fm path* (carpeta del repo); (d) ejecutar *Explode XML*. Si ya tenía agentic-fm: borrar la carpeta `agentic-fm` de scripts y re-pegar.
9. **Índice cruzado:** `python3 agent/scripts/trace.py build -s "<Solución>"` tras el explode.
10. **MCP del índice [app]:** guía `Setup/MCP-Indice-Agentic-FM-App` del vault (una vez por Mac).
11. **Webviewer (opcional):** layout `agentic-fm` con Web Viewer `http://localhost:8080`, objeto `agentic-fm`; `cd webviewer && npm install && npm run dev`.
12. **Verificación:** `python3 agent/scripts/session_start.py` sin FAIL; `agentic-fm-safe-push --check`; rama `trabajo`; `git status` sin ficheros prohibidos.

Al terminar, lee `fm-sesion.md` para la primera tarea.
