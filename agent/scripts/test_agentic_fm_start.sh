#!/bin/bash
# agent/scripts/test_agentic_fm_start.sh — agentic-fm-start elige `agfm serve` cuando agentic-fm-app está instalada.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }

mkdir -p "$T/bin" "$T/app" "$T/home/Library/Application Support/Agentic-FM-APP/logs" "$T/runtime/agent/scripts"
echo '[project]' > "$T/app/pyproject.toml"
echo '# stub' > "$T/runtime/agent/scripts/companion_server.py"
# stubs: uv records its args; curl answers /health only after uv or the classic companion "started"
cat > "$T/bin/uv" <<'EOS'
#!/bin/bash
echo "$@" >> "$UV_LOG"; touch "$UV_LOG.started"; sleep 12
EOS
cat > "$T/bin/curl" <<'EOS'
#!/bin/bash
if [[ -f "$UV_LOG.started" || -f "$CLASSIC_STARTED" ]]; then echo '{"status":"ok","version":"1.0.0","service":{"app_version":"0.1.0"}}'; exit 0; fi
exit 7
EOS
cat > "$T/bin/python3" <<'EOS'
#!/bin/bash
if [[ "$*" == *companion_server.py* ]]; then touch "$CLASSIC_STARTED"; sleep 12; fi
if [[ "$1" == "-c" ]]; then /usr/bin/python3 "$@"; fi
EOS
chmod +x "$T/bin/"*
export HOME="$T/home" UV_LOG="$T/uv.log" CLASSIC_STARTED="$T/classic.started" AGFM_RUNTIME="$T/runtime"

# --- app installed → agfm serve ----------------------------------------------------------------
( cd "$T" && PATH="$T/bin:/usr/bin:/bin" AGFM_APP_REPO="$T/app" bash "$REPO_ROOT/agent/scripts/bin/agentic-fm-start" > "$T/out1" 2>&1 ) || true
grep -q "run --project $T/app agfm serve" "$UV_LOG" 2>/dev/null || { cat "$T/out1"; fail "agfm serve not launched: $(cat "$UV_LOG" 2>/dev/null)"; }
[[ ! -f "$CLASSIC_STARTED" ]] || fail "classic companion launched although the app is installed"
grep -q "Agentic-FM-APP" "$T/out1" || fail "output does not say which service started"
pass "app installed → agentic-fm-start launches agfm serve"

# --- app absent → classic companion ------------------------------------------------------------
rm -f "$UV_LOG" "$UV_LOG.started" "$CLASSIC_STARTED"
( cd "$T" && PATH="$T/bin:/usr/bin:/bin" AGFM_APP_REPO="$T/missing" bash "$REPO_ROOT/agent/scripts/bin/agentic-fm-start" > "$T/out2" 2>&1 ) || true
[[ -f "$CLASSIC_STARTED" ]] || { cat "$T/out2"; fail "classic companion not launched"; }
[[ ! -f "$UV_LOG" ]] || fail "uv called although the app is absent"
pass "app absent → agentic-fm-start launches the classic companion"
echo "all agentic-fm-start tests passed"
