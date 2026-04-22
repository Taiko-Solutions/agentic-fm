# `ops/services/` — descartado para producción por TCC

> ⚠️ **No instalar. Ver Plan B abajo para el método oficial Taiko.**

## Qué hay aquí

Infraestructura para arrancar el `companion_server.py` como un **LaunchAgent de macOS** (servicio gestionado por `launchd`). Incluye:

- `launchd/*.plist.template` — templates de LaunchAgent para companion + webviewer-docker
- `install_launchagents.sh` — instalador que renderiza los templates a `~/Library/LaunchAgents/` e invoca `launchctl bootstrap`
- `servicesctl.sh` — control unificado (`install | start | stop | restart | status | uninstall | use-repo`)
- `start_companion.sh` / `start_webviewer_docker.sh` — scripts invocados por los LaunchAgents
- `uninstall_launchagents.sh`, `status.sh`, `use_repo.sh`, `common.sh` — utilidades

## Por qué no se usa

El companion necesita **acceso a `~/Documents/GITs/*/agent/xml_parsed/`** y a otras rutas bajo `~/Documents/` (TCC-protegidas en macOS).

Cuando el companion se lanza **desde un LaunchAgent**, el proceso Python no hereda los permisos TCC de la sesión interactiva del usuario. El "responsible bundle" a efectos TCC pasa a ser `/bin/zsh` (o el intérprete Python directamente), que no tiene Full Disk Access concedido.

Resultado: los endpoints `/context`, `/explode`, `/debug` fallan en silencio (Permission denied) al intentar leer/escribir dentro de `~/Documents/`.

Se probó en su momento (ver historia de pruebas internas Taiko) y se descartó. La solución vía concesión manual de Full Disk Access al binario `/opt/homebrew/.../python3` es frágil (se pierde en cada upgrade de Python por homebrew) y no escalable al equipo.

## Plan B — método oficial Taiko

El companion se arranca **manualmente cada mañana** con `~/bin/agentic-fm-start`. El proceso hereda TCC del Terminal (que tiene Full Disk Access concedido).

Para que el FMS remoto pueda alcanzar el companion, `agentic-fm-start` lee la variable `COMPANION_BIND_HOST` del environment y bindea el servidor a esa IP (LAN física u overlay Tailscale según dónde esté el desarrollador).

**Documentación completa del setup:** `Proyectos/Taiko/Agentic-FM-Taiko/Setup/Companion-Bind-LAN.md` (Obsidian vault Taiko).

## Por qué se mantiene este directorio

Dos razones:

1. **Referencia histórica** — documenta un camino explorado y descartado, evita que alguien del equipo vuelva a re-descubrir el problema de cero.
2. **Fallback si macOS cambia** — si Apple relaja las reglas TCC en una versión futura, o si el equipo decide conceder Full Disk Access manualmente al python3, el camino launchd vuelve a ser viable sin empezar de cero.

## Origen

- La **recomendación conceptual** de usar launchd viene de upstream (Matt Petrovsky, commit `e0911fc` en `agent/docs/COMPANION_SERVER.md`). El plist que Matt propone allí es **mínimo**.
- La **infraestructura elaborada** de este directorio (templates con `EnvironmentVariables`, sustituciones de placeholders, `servicesctl.sh`, etc.) es invención interna Taiko, introducida en el commit `aae65e5` sobre la rama `taiko`.
- Commit que añade la nota de deprecación: ver `git log ops/README.md`.
