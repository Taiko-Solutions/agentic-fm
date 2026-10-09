# Novedades de la capa Taiko (rama `taiko`)

Changelog de reglas, scripts, catálogos y fmlint de la rama `taiko`. Lo leen `session_start.py`, `agentic-fm-sync` y Agentic-FM-APP para decir qué llega a un clon. `UPDATES.md` es el changelog de upstream (petrowsky).

**Regla:** toda PR a `taiko` que cambie reglas o herramientas añade una entrada aquí, la más reciente arriba, con `**Acción requerida:**` u `**Acción opcional:**` cuando el desarrollador deba hacer algo.

## 2026-10-09 — `fm_xml_to_snippet.py`: `Send Mail` «Con diálogo» ya no se invierte

**Acción opcional:** si regeneraste con `fm_xml_to_snippet.py` algún guion con `Send Mail` y lo pegaste, revisa ese paso en FileMaker: si el original abría el mensaje para revisarlo («Con diálogo») y ahora sale sin diálogo, el correo va directo a la bandeja de salida. Vuelve a convertirlo o marca «Con diálogo» a mano.

- FileMaker 2026 exporta el diálogo de `Send Mail` como `<Boolean type="With dialog" value="True">`; el decodificador (`saxml_read.py`, `_dec_send_mail`) suponía el antiguo `type="No dialog"` y lo invertía (`NoInteract="True"`). Ahora lee el `type` y acepta los dos.
- `snippet_to_hr.py` lo delataba como «With dialog: Off» en un `Send Mail` que en FileMaker tiene diálogo.
- Tests nuevos en `agent/scripts/test_fm_xml_to_snippet.py` (`TestSendMailDialog`: «With dialog» True/False y «No dialog» antiguo).
- Conocimiento nuevo `agent/docs/taiko/knowledge/insert-from-url-curl-gotchas.md`: `-F "file=@$var"` sube con el nombre de la variable (usar `;filename=`), un 401 llega como error de `Insert from URL` (leer el código con `-D` antes de `ThrowIfLast`) y `--max-time` en llamadas que envían.

## 2026-10-08 — Conversor HR→XML del webviewer: Perform Script a otro archivo

**Acción opcional:** si convertiste con el webviewer un `Perform Script` a otro archivo (`File: "…"` o `"Script" from file: "…"`) y lo pegaste, en FileMaker sale como `<unknown>`. Vuelve a convertirlo.

- Antes el token `File: "Y"` acababa tal cual dentro de `<FileReference>` y FileMaker no resolvía el paso. Ahora se emite `<FileReference id="0" name="Y">` con `<UniversalPathList>file:Y</UniversalPathList>` y `<Script id="0" name="X"/>`. Comprobado pegando en FileMaker (2026-10): resuelve la fuente de datos y el guion remoto **por nombre**. El guion de destino nunca se busca en el contexto del archivo actual, porque su id es del otro archivo.
- `Y` tiene que ser el nombre de la **fuente de datos externa** (*Manage External Data Sources*), que es lo que muestra el HR de FileMaker.
- Con `File: ""` o `<unknown> from file: ""` el paso se marca como no convertible (error y marcador), en vez de emitir algo que no sirve. Copia ese paso desde FileMaker.
- fmlint X003: un `<FileReference>` con `<UniversalPathList>` pero sin `name` ahora es error. Antes daba un INFO de «llamada al mismo archivo», pero FileMaker descarta la referencia al pegar.
- Tests: `webviewer/test/hr-to-xml.perform-script-crossfile.test.ts` y 2 nuevos en `agent/fmlint/tests/test_param_fidelity.py`.

## 2026-10-08 — Conversor HR→XML del webviewer: entiende el `Specified:` de Perform Script

**Acción opcional:** si pegaste en el webviewer un `Perform Script` o `Perform Script on Server` copiado de Script Workspace (con `Specified: From list` o `Specified: By name`) y lo pegaste convertido en FileMaker, revísalo: puede llamar a un script que no existe o no llamar a nada. Vuelve a convertirlo.

- FileMaker escribe el modo de elegir el script como `Specified: From list` o `Specified: By name` (a veces sin `Specified:`, antes o después del nombre). El conversor lo tomaba como un valor: en `Perform Script` el texto `Specified: From list` acababa de nombre del script y el nombre real dentro de `<FileReference>`; en `Perform Script on Server` (y `… with Callback`) "From list" acababa en `<Calculated>`, que es el modo por nombre, junto a `<Script>`. Ese paso no llama a nada (fmlint X004).
- Ahora `From list` no deja rastro (es el modo por defecto) y `By name` toma como cálculo el token siguiente. En modo por nombre no se emite `<Script>`.
- Comprobado con 458 líneas `Perform Script*` reales de proyectos cliente (2026-10): ningún error X004. Sigue sin resolverse la llamada a **otro archivo** (`File: "…"`): el conversor offline no conoce la fuente de datos externa y emite un `<FileReference>` que no sirve. Para esas, copia el paso desde FileMaker.
- Test nuevo `webviewer/test/hr-to-xml.perform-script-specified.test.ts`.

## 2026-10-08 — `clipboard.py read` ya no confunde texto plano con un menú

**Acción opcional:** si hiciste un `clipboard.py read` que respondió `Saved ut16 (Menu)` y no habías copiado un menú, el archivo que guardó está vacío o tiene texto suelto. Vuelve a copiar los pasos en Script Workspace con ⌘C y repite el `read`.

- `«class ut16»` aparece en cualquier texto copiado en macOS, no solo en los menús de FileMaker. `read` trataba como menú todo lo que la llevara, y con el portapapeles vacío guardaba un archivo de 1 byte. Ahora la cuenta como menú solo si el texto contiene `<CustomMenu`, `<CustomMenuSet` o `<fmxmlsnippet`. Se arregla en las dos rutas: AppKit y osascript.
- Si no hay objetos de FileMaker, `read` sale con código 1, no escribe el archivo y avisa: "el portapapeles no contiene objetos de FileMaker: copia los pasos en Script Workspace con ⌘C".
- La decisión está en una función pura, `classify_clipboard()`. Los tests nuevos están en `agent/scripts/test_clipboard.py` y los ejecuta `ci_checks.py`.

## 2026-10-08 — Conocimiento: trampas del separador decimal (`decimal-separator-traps.md`)

**Acción opcional:** si tu solución lee importes con `ExecuteSQL` y los convierte con `GetAsNumber`, revísalos. En un archivo con coma decimal, `GetAsNumber ( "677.6" )` devuelve 6776. El arreglo es una CF `num.DesdeTextoPunto` (el texto está en el documento).

- Documento nuevo en `agent/docs/taiko/knowledge/` con tres trampas que no dan error: `GetAsNumber` sobre texto de ExecuteSQL (×10/×100), `JSONRaw` con un número de FileMaker (trunca los decimales) y `JSONNumber` con valor vacío (serializa `0`).
- Incluye cómo comprobarlo en el motor antes de pegar. Indexado en el MANIFEST.
- Origen: proyecto cliente (2026-10), un MCP devolvía importes ×10/×100.

## 2026-10-07 — Conversor HR→XML del webviewer: Perform Script con parámetro ya se pega bien

**Acción opcional:** si convertiste con el webviewer (HR→XML) algún `Perform Script` con parámetro y ya lo pegaste, revísalo en FileMaker: un paso que muestra `From list ; ""` no llama a nada. Vuelve a convertirlo y pégalo de nuevo.

- El conversor TypeScript (`webviewer/src/converter/catalog-emit.ts`) emitía `<Script>` antes que el `<Calculation>` del parámetro, porque sigue el orden del catálogo, que es el del HR. Con ese orden FileMaker acepta el paste pero deja el destino sin resolver (fmlint X004). Ahora emite en el orden de FileMaker, `FileReference → Calculated → Calculation → Script`, igual que el conversor Python (`_XML_CHILD_ORDER` en `catalog_emit.py`).
- Con el `omitWhenEmpty` que el catálogo ya trae en el `FileReference` de Perform Script, una llamada al mismo archivo tampoco arrastra aquí un `<FileReference></FileReference>` vacío.
- Test nuevo `webviewer/test/hr-to-xml.perform-script-order.test.ts`. El fixture de `Insert Text` en `hr-to-xml.json` se re-bendice: estaba desfasado desde que el catálogo pasó a poner `<Text>` antes que `<Field>`.
- `Perform Script on Server` y `… with Callback` no cambian: comprobado contra pasos copiados de FileMaker 2026, ya emiten el parámetro antes de `<Script>`. Quedan fijados con test.

## 2026-10-07 — `fm_xml_to_snippet.py`: Go to Layout por cálculo y Perform Script con parámetro ya se pegan bien

**Acción requerida:** vuelve a convertir con `fm_xml_to_snippet.py` cualquier XML de `agent/sandbox/` que hayas sacado de `xml_parsed/scripts/` y aún no hayas pegado. Lo que ya está pegado en FileMaker revísalo así: en los `Go to Layout`, un layout que sale como `<BROKEN REFERENCE>`, y en los `Perform Script`, un paso que muestra `From list ; ""` o `By name:` con el parámetro.

- **Go to Layout por cálculo.** Si el destino era un cálculo con el nombre entre comillas (`"Proc_Notas"`), el conversor lo pasaba a "layout seleccionado" por nombre y sin id (`<Layout name="Proc_Notas"/>`), y FileMaker lo pegaba como `<BROKEN REFERENCE>`. Ahora se mantiene por cálculo (`LayoutNameByCalc`), igual que en el original. Los layouts elegidos de la lista ya conservaban su id.
- **Perform Script.** El parámetro salía dentro de `<Calculated>`, que es el modo "by name", con `<Script>` delante y un `<FileReference>` vacío. Ese es el fallo X004 de fmlint, y el paso no llamaba a nada. Ahora sale en el orden de FileMaker: `FileReference` (solo si el script está en otro archivo, con su ruta sacada de `xml_parsed/external_data_sources/`), luego `Calculation` con el parámetro y `Script` al final. El modo "by name" real, que antes se perdía, sale en `<Calculated>`.
- Comprobado sobre 700 scripts reales de un proyecto cliente (2026-10): X004 pasa de 1553 errores a 0 y los `<Layout name/>` sin id de 53 a 0. Siguen saliendo X003 en los `Perform Script` cuyo archivo externo ya está roto en el origen (`<unknown>`). Hay tests nuevos en `test_fm_xml_to_snippet.py` y muestras nuevas en `agent/fixtures/converter/`. Los parches `_fix_layout_ids.py` y `_fix_perform_script.py` ya no hacen falta.
- `agent/scripts/ci_checks.py` limpia las variables `GIT_*` que exporta git al hook pre-push. Con ellas, los tests que crean repos temporales (paths, sync_clone, session_start…) fallaban y bloqueaban el push hecho desde un worktree.

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
