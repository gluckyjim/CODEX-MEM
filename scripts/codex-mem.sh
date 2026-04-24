#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
STATE_HOME="$REPO_ROOT/state"

if [ -n "${CODEX_MEM_PYTHON:-}" ]; then
  PYTHON_BIN="$CODEX_MEM_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "No usable Python interpreter found. Set CODEX_MEM_PYTHON." >&2
  exit 1
fi

cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m codex_mem --home "$STATE_HOME" "$@"
