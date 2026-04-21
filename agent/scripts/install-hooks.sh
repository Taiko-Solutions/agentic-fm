#!/bin/bash
# agentic-fm install-hooks.sh
# Instala (o reinstala) los git hooks de protección en el repo actual.
#
# Uso:
#   bash agent/scripts/install-hooks.sh
#
# Los hooks viven versionados en agent/scripts/hooks/ y se copian a .git/hooks/
# en cada repo. Re-ejecutar este script tras un `git pull origin taiko` si el
# hook se ha actualizado.

set -euo pipefail

# Encontrar la raíz del repo
if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    echo "❌ No estás dentro de un repositorio git."
    exit 1
fi

HOOKS_SRC="$REPO_ROOT/agent/scripts/hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_SRC" ]; then
    echo "❌ No se encuentra $HOOKS_SRC"
    echo "   ¿Estás en un repo agentic-fm con la rama taiko al día?"
    exit 1
fi

mkdir -p "$HOOKS_DST"

installed=0
for hook in "$HOOKS_SRC"/*; do
    [ -f "$hook" ] || continue
    name="$(basename "$hook")"
    dst="$HOOKS_DST/$name"

    cp "$hook" "$dst"
    chmod +x "$dst"
    echo "✅ Instalado: .git/hooks/$name"
    installed=$((installed + 1))
done

if [ $installed -eq 0 ]; then
    echo "⚠️  No se encontraron hooks en $HOOKS_SRC"
    exit 1
fi

echo ""
echo "Hooks agentic-fm instalados ($installed). Protección activa en este repo."
