# Configurar agentic-fm para un cliente nuevo (Taiko)

> Para el agente, tras clonar (la skill `fm-nuevo-proyecto` hace: SSH, `git clone -b taiko git@GIT:Taiko-Solutions/agentic-fm.git`, `git checkout -b trabajo`). Pide los datos que falten de uno en uno.

Datos: carpeta (`~/GITs/<Cliente>/agentic-fm`), ficheros `.fmp12` (sin extensión), servidor FM (`https://…`), ¿OData?

**Camino por defecto: con Agentic-FM-APP** (la app de escritorio + el add-on `agentic-fm` en FileMaker). Compruébalo antes de empezar: `curl -s http://127.0.0.1:8765/health` debe devolver JSON con un bloque `service`. Si no hay app en este Mac, sigue el [camino clásico](#camino-clásico-sin-la-app) al final.

## Con Agentic-FM-APP

1. **Hook y reglas de rutas (obligatorio):** `bash agent/scripts/install-hooks.sh` (o *Instalar hooks* en la ventana de proyectos de la app); verifica `ls -la "$(git rev-parse --git-common-dir)/hooks/pre-push"`. Sin hook no se continúa.
2. **Dependencias:** `python3 --version` y `xmllint --version` (los scripts del clon); `node ≥ 18` solo si se usa el webviewer. **No** hace falta `~/bin/fm-xml-export-exploder`: la app pasa su exploder 0.7.1 empaquetado con `FM_XML_EXPLODER_BIN`. Tampoco los scripts de terminal de `agent/scripts/bin/` en `~/bin`.
3. **Directorios:** `mkdir -p agent/xml_parsed agent/context agent/sandbox agent/debug agent/config` (todos ignorados por git y bloqueados por el hook).
4. **`agent/config/removals.json`** (scripts/CFs con credenciales que no deben quedar en el explode; la app lo aplica en cada explode): pregunta qué objetos; IDs mejor que nombres. Plantilla: `agent/config/removals.json.example`.
5. **`agent/config/automation.json`: solo si se quiere OData.** Bloque `odata` por solución con `base_url`, `database`, `username`, `password`, `script_bridge: "AGFMScriptBridge"`; pide las credenciales OData. `companion_url` = `http://127.0.0.1:8765` (lo sirve la app). Plantilla: `agent/config/automation.json.example`. Sin OData, sáltalo: el explode no lo necesita.
6. **Servicio:** nada que arrancar; la app es dueña del puerto 8765. Si `/health` no responde, abre Agentic-FM-APP; si el 8765 lo tiene el companion clásico, *Tomar el control del 8765* en la app.
7. **En FileMaker, por cada fichero:**
   1. Paquete en este Mac: la línea «Add-on agentic-fm» de la app → *Instalar en FileMaker* (copia el paquete a `AddonModules`; reinicia FileMaker después). Sin la app, doble clic en `filemaker/addon/agentic-fm.fmaddon`.
   2. Si el fichero ya tenía agentic-fm **pegado**: borra la carpeta de guiones `agentic-fm` y la CF `Context` **antes** de instalar.
   3. Modo Presentación › pestaña Add-ons › Instalar add-on › **selecciona `agentic-fm` y pulsa Intro**.
   4. Ejecuta *Explode XML*. La primera vez la app aún no conoce el fichero (`GET /config` → `unknown_solution`), así que el add-on abre el selector de carpeta: elige la carpeta `agentic-fm` del clon. Ese primer explode crea el proyecto en la app (con el nombre de la carpeta padre del clon, p. ej. `<Cliente>`) y es la línea base; los siguientes ya no preguntan.
   5. Tus guiones llaman a los de agentic-fm **por nombre** (`"Agentic-fm Debug"`, `"Get agentic-fm path"`), nunca por referencia.
8. **Índice cruzado (opcional):** el índice de la app ya da `fm_refs` / `fm_impact`. `python3 agent/scripts/trace.py build -s "<Solución>"` solo si se va a usar `trace.py` directamente.
9. **MCP del índice (una vez por Mac):** *Registrar MCP* en la ventana de la app, o guía `Setup/MCP-Indice-Agentic-FM-App` del vault. Si ya está registrado, no lo repitas.
10. **Webviewer (opcional):** no va en el add-on; pega `filemaker/addon/agentic-fm-webviewer.xml` (nunca el `agentic-fm.xml` completo encima del add-on), layout `agentic-fm` con Web Viewer `http://localhost:8080`, objeto `agentic-fm`; `cd webviewer && npm install && npm run dev`.
11. **Verificación:** `python3 agent/scripts/session_start.py` sin FAIL (la línea `embedded` debe ver el add-on al día); `bash agent/scripts/bin/agentic-fm-safe-push --check`; la solución aparece en la ventana de proyectos de la app; rama `trabajo`; `git status` sin ficheros prohibidos.

## Camino clásico (sin la app)

Mismos pasos 1, 2 (python3, xmllint), 3, 4, 7 y 11, con estos cambios:

- **Scripts de terminal:** symlinks de `agent/scripts/bin/` a `~/bin` (`agentic-fm-start`, `-update`, `-sync`, `-safe-push`); `~/.zshrc` con `export PATH="$HOME/bin:$PATH"`.
- **Exploder:** `~/bin/fm-xml-export-exploder` **0.7.1** (https://github.com/bc-m/fm-xml-export-exploder/releases/latest, aarch64-apple-darwin); *Explode XML* lo busca ahí y llama a `fmparse.sh`.
- **`automation.json`:** además de `odata`, el bloque `explode_xml` con `repo_path`/`export_path`.
- **Companion:** `curl -s http://127.0.0.1:8765/health`; si no responde `agentic-fm-start`; si no existe el runtime, `agentic-fm-update ~/GITs/agentic-fm`. Sin `/config`, el add-on pide la carpeta del clon en cada sesión.
- **Índice cruzado:** `python3 agent/scripts/trace.py build -s "<Solución>"` tras cada explode (no hay MCP del índice).

Al terminar, lee `fm-sesion.md` para la primera tarea.
