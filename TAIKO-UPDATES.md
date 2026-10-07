# Novedades de la capa Taiko (rama `taiko`)

Changelog de reglas, scripts, catálogos y fmlint de la rama `taiko`. Lo leen `session_start.py`, `agentic-fm-sync` y Agentic-FM-APP para decir qué llega a un clon. `UPDATES.md` es el changelog de upstream (petrowsky).

**Regla:** toda PR a `taiko` que cambie reglas o herramientas añade una entrada aquí, la más reciente arriba, con `**Acción requerida:**` u `**Acción opcional:**` cuando el desarrollador deba hacer algo.

## 2026-10-07 — `fm_xml_to_snippet.py`: Go to Layout por cálculo y Perform Script con parámetro ya se pegan bien

**Acción requerida:** vuelve a convertir con `fm_xml_to_snippet.py` cualquier XML de `agent/sandbox/` que hayas sacado de `xml_parsed/scripts/` y aún no hayas pegado. Lo que ya está pegado en FileMaker revísalo así: en los `Go to Layout`, un layout que sale como `<BROKEN REFERENCE>`, y en los `Perform Script`, un paso que muestra `From list ; ""` o `By name:` con el parámetro.

- **Go to Layout por cálculo.** Si el destino era un cálculo con el nombre entre comillas (`"Proc_Notas"`), el conversor lo pasaba a "layout seleccionado" por nombre y sin id (`<Layout name="Proc_Notas"/>`), y FileMaker lo pegaba como `<BROKEN REFERENCE>`. Ahora se mantiene por cálculo (`LayoutNameByCalc`), igual que en el original. Los layouts elegidos de la lista ya conservaban su id.
- **Perform Script.** El parámetro salía dentro de `<Calculated>`, que es el modo "by name", con `<Script>` delante y un `<FileReference>` vacío. Ese es el fallo X004 de fmlint, y el paso no llamaba a nada. Ahora sale en el orden de FileMaker: `FileReference` (solo si el script está en otro archivo, con su ruta sacada de `xml_parsed/external_data_sources/`), luego `Calculation` con el parámetro y `Script` al final. El modo "by name" real, que antes se perdía, sale en `<Calculated>`.
- Comprobado sobre 700 scripts reales de un proyecto cliente (2026-10): X004 pasa de 1553 errores a 0 y los `<Layout name/>` sin id de 53 a 0. Siguen saliendo X003 en los `Perform Script` cuyo archivo externo ya está roto en el origen (`<unknown>`). Hay tests nuevos en `test_fm_xml_to_snippet.py` y muestras nuevas en `agent/fixtures/converter/`. Los parches `_fix_layout_ids.py` y `_fix_perform_script.py` ya no hacen falta.

## 2026-10-07 — `agent/fixtures/` en la capa herramientas

**Acción requerida:** tras traer `taiko`, ejecuta `agentic-fm-sync` para reinstalar el hook pre-push con la regla nueva. `agent/fixtures/` (muestras y goldens de los tests de conversores) quedó fuera de `[allow]` en `agent/scripts/hooks/paths.conf` al crear la allowlist, y el hook bloqueaba subir un test de conversor. Ya estaba versionado en `taiko`.

## 2026-10-06 — Fuera de la capa herramientas la guía de conversión de un proyecto cliente

Sin acción. `agent/docs/taiko/` tenía una guía de migración Geist → Clew de un proyecto cliente concreto (2026-03). Ahora está en el vault de Obsidian, en la carpeta de ese cliente, y deja de llegar a los clones. El patrón general sigue en `knowledge/clew-pattern.md`, `knowledge/clew-transactional-dual.md` y `templates/`.

## 2026-10-06 — Plantillas Clew transaccionales sin nombre de cliente

Sin acción. La cabecera de `templates/clew-transactional-dual.md` y `clew-transactional-orchestrator.md` pasa a `# Capa: Controller (plantilla)`, y `knowledge/clew-transactional-dual.md` cita la validación como "proyecto cliente (2026-06)". Antes ambas nombraban la solución de un cliente.
## 2026-10-06 — Funciones personalizadas del patrón Clew transaccional dual en `custom_functions/clew-transactional.xml`

**Acción requerida:** antes de pegar un script hecho con `templates/clew-transactional-dual.md` o `clew-transactional-orchestrator.md` en un archivo que aún no use el patrón, pega primero `agent/docs/taiko/custom_functions/clew-transactional.xml` (`python3 agent/scripts/clipboard.py write agent/docs/taiko/custom_functions/clew-transactional.xml` → Gestionar funciones personalizadas → ⌘V). Si falta alguna de las cuatro funciones, FileMaker comenta con `/* */` el cálculo que la usa y el script deja de propagar el error sin avisar. Los archivos que ya usan el patrón no tienen que hacer nada: el 2026-10-06 se comprobó en el índice de Agentic-FM-APP que el único que lo usa tiene las cuatro definidas y todos sus usos resueltos.

- Nuevo `agent/docs/taiko/custom_functions/clew-transactional.xml`: `Clew.SetError ( trace )`, `Clew.ClearError`, `Clew.HasError` y `Clew.GetError`, con el mismo cuerpo que define `knowledge/clew-transactional-dual.md`. Va aparte de `clew.xml` porque es una extensión de Taiko que solo necesita quien use el patrón dual.
- Las dos plantillas avisan en la cabecera de este requisito; `knowledge/clew-transactional-dual.md`, `knowledge/MANIFEST.md` y `agent/docs/taiko/README.md` enlazan el XML.
## 2026-10-06 — IDs de pasos corregidos en CODING_CONVENTIONS y `<FlushType>` en las plantillas CLEW transaccionales

**Acción opcional:** si generaste scripts a partir de `templates/clew-transactional-dual.md` o `clew-transactional-orchestrator.md`, o tomaste IDs de la tabla de `CODING_CONVENTIONS.md`, revisa el XML guardado: busca `<Flush state="Always"/>` (cámbialo por `<FlushType value="Always"/>`) e `id="118|200|201|202"` en Close Window / Open, Commit y Revert Transaction. Los scripts ya pegados en FileMaker no tienen que cambiar: FM descarta `<Flush>` y aplica `Always`, que es el valor por defecto.

- `agent/docs/taiko/CODING_CONVENTIONS.md`, tabla "FM Script Step ID Reference": Close Window 118 → **121**, Open Transaction 200 → **205**, Commit Transaction 201 → **206**, Revert Transaction 202 → **207**, que son los valores del catálogo y del XML de FileMaker. Los demás IDs de la tabla se han contrastado con `step-catalog-en.json` y cuadran.
- `templates/clew-transactional-dual.md` y `clew-transactional-orchestrator.md`: el paso Loop pasa de `<Flush state="Always"/>` a `<FlushType value="Always"/>`, el elemento que define el catálogo. fmlint lo marcaba X001 en todos los scripts generados desde estas plantillas. Ahora el XML de las dos plantillas pasa fmlint sin errores.

## 2026-10-02 — agentic-fm-start arranca Agentic-FM-APP (`agfm serve`) si está instalada

**Acción opcional:** instala agentic-fm-app (`git clone git@GIT:Taiko-Solutions/agentic-fm-app.git ~/GITs/agentic-fm-app && cd ~/GITs/agentic-fm-app && uv sync && uv run agfm exploder install`). Desde entonces `agentic-fm-start` levanta `agfm serve` en 8765: Explode XML pasa por el pipeline nuevo (explode + índices + indexación + retención) y Push Context entra en el índice al momento. El resto de endpoints (`/trigger`, `/clipboard`, `/debug`, `/lint`, `/webviewer/*`, `/plugin/*`) los sigue sirviendo el companion de siempre como proceso hijo (puerto interno 8769, solo `127.0.0.1`). Sin la app, nada cambia.

- `agentic-fm-start`: variables `AGFM_APP_REPO` (por defecto `~/GITs/agentic-fm-app`) y `AGFM_RUNTIME`.
- Diagnóstico: `uv run --project ~/GITs/agentic-fm-app agfm service status`; log en `~/Library/Application Support/Agentic-FM-APP/logs/service.log`.
- Detalle en `docs/service.md` de agentic-fm-app y en `agent/docs/COMPANION_SERVER.md` § Behind Agentic-FM-APP.

## 2026-10-02 — Procedimientos de sesión en el repo y plugin taiko-filemaker

**Acción requerida:** instala el plugin `taiko-filemaker` del marketplace `taiko` (README de `claude-plugins`). Los prompts Nueva-Tarea/Puesta-Al-Dia/Nuevo-Proyecto del vault quedan retirados.

- `agent/docs/taiko/sessions/fm-sesion.md` y `fm-nuevo-proyecto.md`: lo que leen las skills `fm-sesion` y `fm-nuevo-proyecto`. El hook `SessionStart` del plugin ejecuta `session_start.py` e inyecta el resumen en cada sesión dentro de un clon.

## 2026-10-01 — Exploder 0.7.1: cambian las carpetas del explode; `agfm explode` sustituye a `fmparse.sh` + `fmcontext.sh`

**Acción requerida:** ninguna si tienes la **0.5.1** (los Macs de Taiko hoy). Si instalas la **0.6.1 o superior** (lo que da el enlace "releases/latest" de `fm-nuevo-proyecto`), trae esta entrega antes del primer explode: `fmparse.sh` y `fmcontext.sh` de `taiko` ya entienden las carpetas nuevas. Con la versión anterior de los scripts y un exploder ≥ 0.6.1, `removals.json` **no borraba** la copia de las funciones personalizadas sensibles en `custom_functions/<solución>/*.xml` y `custom_functions.index` salía vacío.
**Acción opcional:** pipeline nuevo en Agentic-FM-APP (`Taiko-Solutions/agentic-fm-app`, `main` ≥ `ddcaf17`): `uv run --project ~/GITs/agentic-fm-app agfm exploder install` (una vez: descarga la 0.7.1 fijada con SHA-256 en la carpeta de la app, sin tocar `~/bin`) y después `agfm explode <export.xml> --solution <Solución> --repo <clon>`. Hace lo mismo que `fmparse.sh` + `fmcontext.sh` (archivo en `xml_exports/`, explode, `removals.json`, los siete `agent/context/*.index`), indexa al final y mueve a la Papelera los exports en bruto más antiguos que los 3 últimos **solo si el índice los cubre**. Guía: `docs/pipeline.md` de ese repo.

- **Qué cambió en el exploder** (release 0.6.1, "BREAKING"): las funciones personalizadas pasan de `custom_function_stubs/*.xml` a `custom_functions/*.xml` + `custom_functions_sanitized/*.txt`, y las listas de valores de `value_list_stubs/` a `value_lists/`. Todos los explodes actuales de los clones de Taiko están hechos con la 0.5.1 (nombres antiguos); el primer explode con 0.7.1 de una solución elimina esas carpetas antiguas y crea las nuevas.
- **Qué sigue funcionando con los dos nombres:** el índice y el MCP `agentic-fm-app` (leen primero los nombres nuevos y caen a los antiguos), `check_embedded_agfm.py` (busca `custom_functions_sanitized/` primero), `trace.py` (lee `custom_functions_sanitized/`), el MCP `fm_unused`/`fm_refs`.
- **Parcheados en esta entrega para leer los dos nombres:** `fmparse.sh` (removals limpia también `custom_functions/`), `fmcontext.sh` (`custom_functions/` o `custom_function_stubs/`; `value_lists/` o `value_list_stubs/`), `analyze.py` y la skill `solution-analysis` que lo usa, `.claude/CLAUDE.md` § Custom functions. Tests: `agent/scripts/test_explode_layouts.sh` y `test_analyze_layouts.py` (en `ci_checks.py`).
- **Corrección de paso:** `fmcontext.sh` nunca había rellenado `value_lists.index` (leía el nombre de un elemento `ValueListReference` que el exploder no escribe y comparaba el origen con `Field` cuando el valor real es `FromField`). Corregido aquí y en `agfm explode`: nombres, ids y `(field-based)`.
- **Aviso de seguridad ya vigente:** con la 0.5.1 `fmparse.sh` tampoco activa `--obfuscate-passwords` (solo lo hace para versiones > 0.6.1): las contraseñas de pasos como *Insert from URL* o *Open URL* quedan en claro en `scripts_sanitized/`. El pipeline nuevo con la 0.7.1 las ofusca.
- La aceptación del pipeline (índices byte a byte idénticos a `fmcontext.sh` salvo la corrección de `value_lists.index`; 2,1 s frente a 17,4 s) está en el vault, `Indice-MCP-App/Medicion` § Aceptación F5.

## 2026-10-01 — Modelo de ramas trabajo/taiko/mejora, hook de cuatro capas y agentic-fm-sync

**Acción requerida:** en cada clon, una vez: `git pull origin taiko && agentic-fm-sync --migrar` (crea `trabajo`, deja `taiko` como espejo, quita `upstream` si lo hubiera, reinstala el hook). Instala el symlink nuevo: `ln -sf "$PWD/agent/scripts/bin/agentic-fm-sync" ~/bin/agentic-fm-sync`.

- Clones: `taiko` = espejo (sin commits propios), `trabajo` = todo lo del cliente (nunca se sube), `mejora/<tema>` = solo capa herramientas, PR a `taiko`.
- Hook pre-push: prohibidos (como antes) + bloqueo de `taiko`/`trabajo` desde clones + allowlist de la capa herramientas en cualquier otra rama del clon (`agent/scripts/hooks/paths.conf`) + aviso si se tocan reglas sin entrada aquí. `agentic-fm-safe-push` y la GitHub Action usan las mismas reglas (`agent/scripts/check_pushed_paths.py`).
- `session_start.py` lista las novedades de este fichero cuando el clon va por detrás y avisa si estás en `taiko` dentro de un clon.
- `agentic-fm-sync --migrar` detecta una reescritura de `origin/taiko` (force-push) con el reflog del remoto: realinea `taiko`/`trabajo` a la historia nueva y reaplica solo los commits propios (sin merges); lo anterior queda en `backup/trabajo-pre-reescritura-<fecha>`.
- Seguridad: `agentic-fm-sync` nunca descarta commits locales de `taiko` (sin `--migrar` se detiene; con `--migrar` los mueve a `trabajo` o los guarda en `backup/taiko-local-<fecha>`). El hook lleva copia de `check_pushed_paths.py` y `paths.conf` en `.git/hooks/` y es **fail-closed**: sin ellas, un clon no puede hacer push. La Action usa las reglas de la rama base y mira commit a commit (merges incluidos).

## 2026-10-01 — ProofKit: gotchas F13–F19, deploy estándar en FileMaker 2026 y plantilla CLAUDE-webapp.md nueva

**Acción requerida:** apps web ProofKit existentes: sustituir su `CLAUDE.md` por `agent/docs/taiko/proofkit/CLAUDE-webapp.md` (ajustando el bloque "Este proyecto"). Verificar que el objeto Web Viewer se llama `web`.
**Acción requerida:** `.mcp.json` pasa a `proofkit mcp` (forma oficial desde ProofKit 3.2.0): `~/.local/bin` debe estar en el PATH de las sesiones de Claude (`echo $PATH` dentro de Claude Code).

- Nombre del Web Viewer `web` (F13); `PK_send_callback` resuelve en la ventana activa (F14); cerrar la pantalla antes de `deploy_html` (F15); `fmBridge` en dev dentro de FM con `?wv=web` (F16); esperar a `window.FileMaker` (F17); claves UUIDDecimal nunca por OData (F19).
- Deploy FM 2026: `deploy_html` guarda en el almacén persistente; el WV lee `"data:text/html," & GetPersistentData ( "proofkit" ; "<app>" )`. Sobrevive migraciones.
- Docs alineados: `proofkit/README.md`, `taiko/README.md`, `troubleshooting.md`, `conventions.md`.
- **Corrección (2026-10-01, tarde):** la PR #11 borró `.cursor/` creyendo que eran copias; en realidad `.claude/skills` es un symlink a `.cursor/skills` (estructura de upstream) y las 25 skills desaparecieron. Restaurado en `taiko`; `agentic-fm-sync` lo trae. Si en un clon `ls .claude/skills/` está vacío o da error, sincroniza.

## 2026-10-01 — Perform Script: orden de los hijos (fmlint X004) y X003 sin falsos positivos

- `<Script>` debe ir el **último** (`FileReference → Calculated → Calculation → Script`); si va primero FileMaker acepta el paste y el paso no llama a nada. Detalle en `agent/docs/taiko/knowledge/silent-discard-params.md`; `fmlint` X004 lo bloquea.
- X003 ya no se dispara en llamadas al mismo archivo con `<FileReference/>` vacío.
- `clipboard.py` pasa el AppleScript por stdin: snippets grandes (una app HTML en `Insert Text`) ya no fallan.
- Catálogo: `Perform Script` documenta `<Calculated>` (by name) y `<FileReference>`.

## 2026-09-19 — Propuestas de clones aplicadas (PRs #7–#10)

- Herramientas de historial del MCP `agentic-fm-app` en el árbol de búsqueda; 17 propuestas de clones registradas en `agent/UPSTREAM_PROPOSALS.md`; `fmparse.sh` borra el `.txt` de CFs sensibles en explode multi-BD; knowledge `SQL.Get*` devuelve `?` con TO no relacionada.
