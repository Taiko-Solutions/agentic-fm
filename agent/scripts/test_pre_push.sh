#!/bin/bash
# agent/scripts/test_pre_push.sh — prueba el hook pre-push con repos de juguete.
# Uso: bash agent/scripts/test_pre_push.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }

git init -q --bare "$T/origin.git"
git init -q "$T/seed" && cd "$T/seed"
git config user.email t@t && git config user.name t
mkdir -p agent/scripts/hooks agent/docs/taiko
cp "$REPO_ROOT/agent/scripts/hooks/pre-push" agent/scripts/hooks/pre-push
cp "$REPO_ROOT/agent/scripts/hooks/paths.conf" agent/scripts/hooks/paths.conf
cp "$REPO_ROOT/agent/scripts/check_pushed_paths.py" agent/scripts/check_pushed_paths.py
echo "# changelog" > TAIKO-UPDATES.md
git add -A && git commit -qm base && git branch -M taiko && git remote add origin "$T/origin.git" && git push -q origin taiko

install_hook() { cp agent/scripts/hooks/pre-push .git/hooks/pre-push; chmod +x .git/hooks/pre-push; }

# --- Clon (sin upstream) -------------------------------------------------
git clone -q -b taiko "$T/origin.git" "$T/clone" && cd "$T/clone" && git config user.email t@t && git config user.name t && install_hook
mkdir -p agent/docs/taiko && echo x > agent/docs/taiko/a.md && git add -A && git commit -qm "regla"
git push -q origin taiko 2>/dev/null && fail "push a taiko desde clon debió bloquearse" || pass "clon: push a taiko bloqueado"
git checkout -qb trabajo && git push -q origin trabajo 2>/dev/null && fail "push de trabajo debió bloquearse" || pass "clon: push de trabajo bloqueado"
git checkout -qb mejora/docs taiko && mkdir -p docs/superpowers/specs && echo s > docs/superpowers/specs/x.md && git add -A && git commit -qm spec
git push -q origin mejora/docs 2>/dev/null && fail "mejora con docs/ debió bloquearse" || pass "clon: mejora/* fuera de allowlist bloqueada"
git checkout -qb mejora/ok taiko && echo y > agent/docs/taiko/b.md && echo "## 2026-10-01 — b" >> TAIKO-UPDATES.md && git add -A && git commit -qm ok
git push -q origin mejora/ok || fail "mejora/ok (capa herramientas) debió pasar"; pass "clon: mejora/* capa herramientas pasa (rama nueva)"
git checkout -qb mejora/ctx taiko && echo '{}' > agent/CONTEXT.json && git add -f agent/CONTEXT.json && git commit -qm ctx
git push -q origin mejora/ctx 2>/dev/null && fail "CONTEXT.json debió bloquearse" || pass "clon: prohibido bloqueado en mejora/*"
git checkout -qb claude/spec taiko && mkdir -p docs/superpowers/specs && echo s > docs/superpowers/specs/y.md && git add -A && git commit -qm spec2
git push -q origin claude/spec 2>/dev/null && fail "claude/* con docs/ debió bloquearse" || pass "clon: claude/* fuera de allowlist bloqueada"
git push -q origin --delete mejora/ok || fail "borrar rama debió permitirse"; pass "clon: borrar rama permitido"
git checkout -qb mejora/borrado taiko && git rm -q TAIKO-UPDATES.md && mkdir -p docs && echo d > docs/tmp.md && git add -A && git commit -qm "borra y añade" && git rm -q docs/tmp.md && git commit -qm "borra docs" 
git push -q origin mejora/borrado 2>/dev/null && fail "fichero añadido fuera de allowlist (aunque luego borrado) debió bloquearse" || pass "clon: añadir fuera de allowlist bloqueado aunque se borre después"
git checkout -qb mejora/solo-borrado taiko && git rm -q agent/docs/taiko/a.md 2>/dev/null || true; echo z > agent/docs/taiko/z.md && git add -A && git commit -qm z
git push -q origin mejora/solo-borrado || fail "borrar ficheros debió permitirse"; pass "clon: borrados no cuentan para la allowlist"

# --- Repo base (con upstream) --------------------------------------------
git clone -q -b taiko "$T/origin.git" "$T/base" && cd "$T/base" && git config user.email t@t && git config user.name t && install_hook
git remote add upstream "$T/origin.git"
mkdir -p docs/superpowers/specs && echo s > docs/superpowers/specs/x.md && git add -A && git commit -qm spec
git push -q origin taiko || fail "base: push a taiko con docs/ debió pasar"; pass "base: exento de reglas de rama y allowlist"
echo '{}' > agent/CONTEXT.json && git add -f agent/CONTEXT.json && git commit -qm ctx
git push -q origin taiko 2>/dev/null && fail "base: CONTEXT.json debió bloquearse" || pass "base: prohibidos siguen bloqueados"
echo "Todos los casos del hook en verde."
