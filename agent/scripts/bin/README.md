# agent/scripts/bin — herramientas de línea de comandos (Taiko)

Fuente **canónica y versionada** de los scripts que cada desarrollador instala en `~/bin`. Hasta julio 2026 vivían solo en las máquinas (sin fuente en git) — ahora viajan con la rama `taiko` y se actualizan con `git pull`.

| Script | Qué hace |
|---|---|
| `agentic-fm-start` | Arranca el companion (runtime único, `:8765`). **Bind por defecto `127.0.0.1`**; el modo FMS→companion es opt-in vía `COMPANION_BIND_HOST`. |
| `agentic-fm-update` | Copia un repo válido → runtime único (sin `.git` ni datos de cliente) y reinicia el companion. En rama `taiko` hace `git pull --ff-only` antes. |
| `agentic-fm-safe-push` | Validación manual de política antes de un push (2ª red; la 1ª es `.gitignore`, la 3ª el hook pre-push). `--check` / `--execute`. |

## Instalación (una vez por máquina)

Recomendado — **symlinks al repo base** (se actualizan solos con `git pull`):

```bash
mkdir -p ~/bin
for s in agentic-fm-start agentic-fm-update agentic-fm-safe-push; do
  ln -sf "$HOME/GITs/agentic-fm/agent/scripts/bin/$s" ~/bin/$s
done
```

Alternativa — copia (hay que re-copiar tras cada actualización):

```bash
mkdir -p ~/bin && cp agent/scripts/bin/agentic-fm-* ~/bin/ && chmod +x ~/bin/agentic-fm-*
```

Asegúrate de que `~/bin` está en el `PATH` (`echo $PATH`; si falta: `export PATH="$HOME/bin:$PATH"` en `~/.zshrc`).
