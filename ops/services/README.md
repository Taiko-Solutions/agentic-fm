# Servicios locales macOS (Companion + Webviewer)

> Para preparar contribuciones hacia upstream en inglés, consulta también: `ops/services/README.upstream.md`.

Esta carpeta contiene una capa de operación para trabajar con `agentic-fm` en macOS, con foco en:

- arranque automático al iniciar sesión (`launchd`),
- uso multi-repo (cambiar de un proyecto a otro),
- comandos operativos simples para equipo técnico.

## Qué resuelve

1. **Companion Server** en `127.0.0.1:8765` gestionado por `launchd`.
2. **Webviewer** en Docker (`127.0.0.1:8080`) gestionado por `launchd`.
3. **Cambio de repo activo** para Webviewer sin rehacer toda la configuración.
4. **Estado y diagnóstico** de servicios en un único comando.

## Componentes

- `servicesctl.sh` — comando principal (`install|start|stop|restart|status|use-repo|uninstall`).
- `install_launchagents.sh` / `uninstall_launchagents.sh` — instalación/desinstalación de LaunchAgents.
- `start_companion.sh` — arranque de Companion (con `PATH` y `FM_XML_EXPLODER_BIN`).
- `start_webviewer_docker.sh` — arranque de Webviewer Docker.
- `use_repo.sh` — cambia el repo activo del Webviewer.
- `status.sh` — muestra estado de Companion + Webviewer + repo activo.

Plantillas de LaunchAgents:
- `launchd/com.agenticfm.companion-server.plist.template`
- `launchd/com.agenticfm.webviewer-docker.plist.template`

## Requisitos

- macOS
- `launchctl`
- Docker Desktop u OrbStack
- `fm-xml-export-exploder` disponible (idealmente en `~/bin/fm-xml-export-exploder`)

## Instalación y uso base

Desde la raíz del repo:

```bash
./ops/services/servicesctl.sh install
./ops/services/servicesctl.sh status
```

Comandos disponibles:

```bash
./ops/services/servicesctl.sh start
./ops/services/servicesctl.sh stop
./ops/services/servicesctl.sh restart
./ops/services/servicesctl.sh status
./ops/services/servicesctl.sh uninstall
```

## Uso multi-repo (Webviewer)

Para cambiar el repo activo del Webviewer:

```bash
./ops/services/servicesctl.sh use-repo /ruta/al/repo/agentic-fm
```

También puedes usar:

```bash
./ops/services/use_repo.sh /ruta/al/repo/agentic-fm
```

### Regla importante

- **Companion** puede servir múltiples repos (según `repo_path` del payload).
- **Webviewer** usa **un único repo activo a la vez** (puerto 8080).

Repo activo persistido en:

```text
~/Library/Application Support/agentic-fm-services/active_repo.path
```

## Ubicaciones runtime y logs

Runtime de LaunchAgents:

```text
~/Library/Application Support/agentic-fm-services/runtime
```

Logs:

```text
~/Library/Logs/agentic-fm/services.log
~/Library/Logs/agentic-fm/companion-server.launchd.log
~/Library/Logs/agentic-fm/webviewer-docker.launchd.log
```

## Integración opcional con ~/.zshrc (recomendado)

No es obligatoria, pero mejora mucho la operativa diaria.

Ejemplo de helpers opcionales:

```bash
agenticfm_start /ruta/al/repo/agentic-fm
agenticfm_use /ruta/al/repo/agentic-fm
agenticfm_status
agenticfm_stop
```

> Sugerencia: mantener estos helpers como configuración local de cada usuario (`~/.zshrc`) y no como requisito del repo.

## Troubleshooting

### `Operation not permitted` al ejecutar `fmparse.sh` desde Companion

Suele ser un bloqueo de macOS/TCC cuando el proceso arranca bajo `launchd` y accede a repos en `Documents`.

Opciones:

1. Dar permisos adecuados (por ejemplo, Full Disk Access al ejecutable Python implicado).
2. Usar Companion manual temporalmente.
3. Mover repos a una ruta sin restricciones de TCC.

### `fm-xml-export-exploder is not installed or not in PATH`

- Instalar binario y/o
- definir `FM_XML_EXPLODER_BIN` correctamente.

`start_companion.sh` ya intenta usar:

```text
~/bin/fm-xml-export-exploder
```

## Nota para mantenimiento / PRs

- Este módulo está orientado a macOS (`launchd` + notificaciones `osascript`).
- Para upstream (`petrowsky/main`), mantenerlo como capa **opcional** y bien documentada.
- Evitar dependencias de configuración local fuera de `$HOME`.
