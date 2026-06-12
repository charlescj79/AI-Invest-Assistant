#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

echo "==> Running tests"
"$PYTHON_BIN" -m pytest

echo "==> Compiling Python sources"
"$PYTHON_BIN" -m compileall app tests scripts

if command -v docker >/dev/null 2>&1; then
  echo "==> Validating docker compose config"
  docker compose config >/tmp/ai-invest-compose.yml
  echo "Docker Compose config OK: /tmp/ai-invest-compose.yml"
else
  echo "WARN: docker CLI not found; skipping Docker Compose validation" >&2
fi
