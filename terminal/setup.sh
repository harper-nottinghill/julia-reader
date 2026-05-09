#!/usr/bin/env bash
# =============================================================================
# Julia Reader — terminal bundle setup
# Creates terminal/.venv and installs this repo (editable) so the CLI works.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Need Python 3.10+ on PATH (set PYTHON=... if yours is python3.12)." >&2
  exit 1
fi

echo "  Creating venv at $ROOT/.venv ..."
"$PY" -m venv .venv

PIP="./.venv/bin/pip"
"$PIP" install -U pip wheel setuptools

echo "  Installing julia-reader from $REPO (editable) ..."
"$PIP" install -e "$REPO"

echo ""
echo "  Done."
echo ""
echo "  Add the launcher scripts to your PATH, then run either:"
echo "    julia reader --help"
echo "    julia-reader --help"
echo ""
echo "  Example:"
echo "    export PATH=\"$ROOT/bin:\$PATH\""
echo "    julia reader -f ./notes.md -o . --no-llm"
echo ""
