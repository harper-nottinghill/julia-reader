#!/usr/bin/env bash
# =============================================================================
# Julia Reader — build distributable terminal bundle
#
# Produces  dist/julia-reader-terminal-vX.Y.Z.tar.gz
# containing bin/, setup.sh, README.md, vendor/julia_reader/, VERSION, CHECKSUMS.txt
#
# Run from the repository root:
#   bash scripts/build-terminal-bundle.sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
err() { echo "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Resolve project root (repo root)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Resolve version from pyproject.toml
# ---------------------------------------------------------------------------
VERSION=""
if [[ -f "${ROOT}/pyproject.toml" ]]; then
  VERSION="$(grep -m1 '^version\s*=' "${ROOT}/pyproject.toml" | sed 's/.*=.*"\(.*\)".*/\1/')"
fi
VERSION="${VERSION:-0.1.0}"
# Strip leading 'v' if present
VERSION="${VERSION#v}"

# ---------------------------------------------------------------------------
# Validate required source files exist
# ---------------------------------------------------------------------------
TERMINAL_DIR="${ROOT}/terminal"
BIN_DIR="${TERMINAL_DIR}/bin"
SETUP_SH="${TERMINAL_DIR}/setup.sh"
README_MD="${TERMINAL_DIR}/README.md"
SOURCE_DIR="${ROOT}/src/julia_reader"

[[ -d "$BIN_DIR" ]]      || err "Missing required directory: $BIN_DIR"
[[ -f "$SETUP_SH" ]]     || err "Missing required file: $SETUP_SH"
[[ -f "$README_MD" ]]    || err "Missing required file: $README_MD"
[[ -d "$SOURCE_DIR" ]]   || err "Missing required directory: $SOURCE_DIR"

# ---------------------------------------------------------------------------
# Staging directory (clean)
# ---------------------------------------------------------------------------
STAGING_DIR="${ROOT}/dist/staging"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# Cleanup trap
cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Copy files into staging
# ---------------------------------------------------------------------------
echo "  Assembling bundle v${VERSION} ..."

# bin/ directory
cp -R "$BIN_DIR" "${STAGING_DIR}/bin"

# setup.sh (ensure executable)
cp "$SETUP_SH" "${STAGING_DIR}/setup.sh"
chmod +x "${STAGING_DIR}/setup.sh"

# README.md
cp "$README_MD" "${STAGING_DIR}/README.md"

# Vendored source: vendor/ is a self-contained installable project
# Structure:  vendor/pyproject.toml  +  vendor/julia_reader/*.py
mkdir -p "${STAGING_DIR}/vendor/julia_reader"
cp -R "$SOURCE_DIR"/* "${STAGING_DIR}/vendor/julia_reader/"
# Remove __pycache__ from vendored source
find "${STAGING_DIR}/vendor" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Generate a minimal pyproject.toml at the vendor root so
# `pip install vendor/` works without the full repo.
cat > "${STAGING_DIR}/vendor/pyproject.toml" <<PYPROJECT
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "julia-reader"
version = "${VERSION}"
description = "Julia Reader — standalone progressive Reader Chronicle harness."
requires-python = ">=3.10"
license = { text = "MIT" }

[project.scripts]
julia-reader = "julia_reader.cli:main"
PYPROJECT

# VERSION file
{
  echo "${VERSION}"
  echo "Built: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
} > "${STAGING_DIR}/VERSION"

# ---------------------------------------------------------------------------
# Generate checksum manifest
# ---------------------------------------------------------------------------
echo "  Generating checksums ..."
(
  cd "$STAGING_DIR"
  find . -type f ! -name "CHECKSUMS.txt" -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "${STAGING_DIR}/CHECKSUMS.txt"

# ---------------------------------------------------------------------------
# Build the tarball
# ---------------------------------------------------------------------------
DIST_DIR="${ROOT}/dist"
mkdir -p "$DIST_DIR"

ARCHIVE_NAME="julia-reader-terminal-v${VERSION}.tar.gz"
ARCHIVE_PATH="${DIST_DIR}/${ARCHIVE_NAME}"

tar -czf "$ARCHIVE_PATH" -C "$STAGING_DIR" .

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
ARCHIVE_SHA256="$(shasum -a 256 "$ARCHIVE_PATH" | cut -d' ' -f1)"
ARCHIVE_SIZE="$(du -h "$ARCHIVE_PATH" | cut -f1)"

echo ""
echo "  Bundle created successfully."
echo ""
echo "  Archive : ${ARCHIVE_PATH}"
echo "  Size    : ${ARCHIVE_SIZE}"
echo "  SHA-256 : ${ARCHIVE_SHA256}"
echo ""
echo "  To verify:"
echo "    tmpdir=\$(mktemp -d)"
echo "    tar -xzf ${ARCHIVE_PATH} -C \"\$tmpdir\""
echo "    cd \"\$tmpdir\" && sha256sum -c CHECKSUMS.txt"
echo "    bash setup.sh"
echo ""
