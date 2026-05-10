#!/usr/bin/env bash
# =============================================================================
# Julia Reader — terminal bundle setup
# Creates terminal/.venv, installs julia-reader (editable), makes bin/ scripts
# executable, and writes a .installed-version marker for idempotency.
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
err() {
  echo "ERROR: $*" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
VENV_DIR="${ROOT}/.venv"
VERSION_FILE="${ROOT}/.installed-version"
PY="${PYTHON:-python3}"

# ---------------------------------------------------------------------------
# Bundle detection — if vendor/julia_reader/ exists we are inside a
# distributable tarball (no repo).  Install from vendored source instead of
# requiring the full repository.
# ---------------------------------------------------------------------------
BUNDLE_MODE=false
if [[ -d "${ROOT}/vendor/julia_reader" && ! -f "${REPO}/pyproject.toml" ]]; then
  BUNDLE_MODE=true
fi

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
FORCE=false
for arg in "$@"; do
  case "$arg" in
    --force|-f) FORCE=true ;;
  esac
done

# ---------------------------------------------------------------------------
# Python version check (>= 3.10)
# ---------------------------------------------------------------------------
if ! command -v "$PY" >/dev/null 2>&1; then
  err "Python 3.10+ is required but '$PY' not found on PATH. Set PYTHON=... if needed."
fi

"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" \
  || err "Python 3.10+ is required (found $( "$PY" --version 2>&1 ))"

# ---------------------------------------------------------------------------
# Resolve current package version from pyproject.toml or VERSION file
# ---------------------------------------------------------------------------
PKG_VERSION=""
if [[ -f "${REPO}/pyproject.toml" ]]; then
  PKG_VERSION="$(grep -m1 '^version\s*=' "${REPO}/pyproject.toml" | sed 's/.*=.*"\(.*\)".*/\1/')"
elif [[ -f "${ROOT}/VERSION" ]]; then
  PKG_VERSION="$(head -1 "${ROOT}/VERSION")"
fi
PKG_VERSION="${PKG_VERSION:-unknown}"

# ---------------------------------------------------------------------------
# Idempotency — skip if already installed at the same version
# ---------------------------------------------------------------------------
if [[ "$FORCE" == "false" && -f "${VENV_DIR}/bin/python3" && -f "$VERSION_FILE" ]]; then
  INSTALLED_VERSION="$(cat "$VERSION_FILE")"
  if [[ "$INSTALLED_VERSION" == "$PKG_VERSION" ]]; then
    echo "Already installed (version ${PKG_VERSION}). Run with --force to reinstall."
    exit 0
  fi
  echo "Version mismatch (installed=${INSTALLED_VERSION}, current=${PKG_VERSION}). Reinstalling..."
fi

# ---------------------------------------------------------------------------
# Force: wipe existing venv
# ---------------------------------------------------------------------------
if [[ "$FORCE" == "true" && -d "$VENV_DIR" ]]; then
  echo "  --force: removing existing venv at ${VENV_DIR}"
  rm -rf "$VENV_DIR"
fi

# ---------------------------------------------------------------------------
# Create virtual environment
# ---------------------------------------------------------------------------
if [[ -f "${VENV_DIR}/bin/python3" ]]; then
  echo "  Reusing existing venv at ${VENV_DIR}"
else
  echo "  Creating venv at ${VENV_DIR} ..."
  "$PY" -m venv "$VENV_DIR" || err "Failed to create virtual environment at ${VENV_DIR}"
fi

# ---------------------------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------------------------
PIP="${VENV_DIR}/bin/pip"

echo "  Upgrading pip, wheel, setuptools ..."
"$PIP" install -U pip wheel setuptools >/dev/null \
  || err "Failed to upgrade pip"

if [[ "$BUNDLE_MODE" == "true" ]]; then
  echo "  Installing julia-reader from vendored source (bundle mode) ..."
  "$PIP" install "${ROOT}/vendor" \
    || err "Failed to install julia-reader from vendor/"
else
  echo "  Installing julia-reader from ${REPO} (editable) ..."
  "$PIP" install -e "$REPO" \
    || err "Failed to install julia-reader"
fi

# ---------------------------------------------------------------------------
# Make bin/ scripts executable
# ---------------------------------------------------------------------------
for script in "${ROOT}/bin/"*; do
  if [[ -f "$script" ]]; then
    chmod +x "$script"
  fi
done
echo "  Made bin/ scripts executable."

# ---------------------------------------------------------------------------
# Version marker
# ---------------------------------------------------------------------------
echo "$PKG_VERSION" > "$VERSION_FILE"
echo "  Installed version: ${PKG_VERSION}"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "  Setup complete."
echo ""
echo "  Add the launcher scripts to your PATH, then run either:"
echo "    julia reader --help"
echo "    julia-reader --help"
echo ""
echo "  Example:"
echo "    export PATH=\"${ROOT}/bin:\$PATH\""
echo "    julia reader -f ./notes.md -o . --no-llm"
echo ""
echo "  Optional — configure any OpenAI-compatible model in repo root .env:"
echo "    bash \"${REPO}/scripts/configure-model.sh\""
echo ""
