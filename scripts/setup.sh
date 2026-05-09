#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GOLD=$'\033[38;5;178m'
STONE=$'\033[38;5;245m'
GREEN=$'\033[38;5;34m'
PINK=$'\033[38;5;213m'
RESET=$'\033[0m'
BOLD=$'\033[1m'

echo
echo "  ${GOLD}${BOLD}▌ JULIA READER HARNESS SETUP${RESET}"
echo "  ${STONE}Standalone terminal Reader.${RESET}"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "  Python 3 is required. Install Python 3.10+ and run this again."
  exit 1
fi

PY_VERSION="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
)"
echo "  ${PINK}Python:${RESET} ${PY_VERSION}"

if [ ! -d ".venv" ]; then
  echo "  ${PINK}Creating virtual environment:${RESET} .venv"
  python3 -m venv .venv
else
  echo "  ${STONE}Virtual environment already exists:${RESET} .venv"
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"
PY=".venv/bin/python"

echo "  ${PINK}Installing editable package...${RESET}"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -e . >/dev/null

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo "  ${GREEN}Created .env from .env.example${RESET}"
else
  echo "  ${STONE}.env already exists; leaving it untouched.${RESET}"
fi

SMOKE_DIR="$(mktemp -d)"
SMOKE_FILE="${SMOKE_DIR}/sample.txt"
cat > "$SMOKE_FILE" <<'TXT'
# Julia Reader Smoke Test

This is a tiny source document. It proves the Reader can normalize text, split sentences, chunk safely, create a book, and validate artifacts.

Moving on, this second topic gives the local fallback a subject shift to notice.
TXT

echo "  ${PINK}Running no-LLM smoke test...${RESET}"
"$PY" -m julia_reader --no-llm --quiet -f "$SMOKE_FILE" -o "$SMOKE_DIR" >/dev/null
echo "  ${GREEN}Smoke test passed.${RESET}"

echo
echo "  ${GREEN}${BOLD}Setup complete.${RESET}"
echo
echo "  ${STONE}Next:${RESET}"
echo "    source .venv/bin/activate"
echo "    bash scripts/configure-model.sh   ${STONE}# optional: API key + model presets${RESET}"
echo "    julia-reader -f path/to/your-text.md -o ."
echo
echo "  ${STONE}Without an API key:${RESET}"
echo "    julia-reader -f path/to/your-text.md --no-llm"
echo
