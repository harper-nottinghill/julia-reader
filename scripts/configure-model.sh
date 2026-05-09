#!/usr/bin/env bash
# Configure any OpenAI-compatible model URL + model id + API key in .env.
# Wrapper around scripts/configure_model.py — safe to re-run; replaces only the
# marked block inside .env (previous file saved as .env.bak).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${PYTHON:-python3}" "$ROOT/scripts/configure_model.py" "$@"
