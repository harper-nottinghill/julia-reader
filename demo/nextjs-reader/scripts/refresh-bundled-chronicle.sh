#!/usr/bin/env bash
# Regenerate public/chronicle-<slug> from a source text file (run from repo root).
# Usage:
#   ./refresh-bundled-chronicle.sh [BOOK_NAME] [SOURCE_FILE]
#
# Defaults:
#   BOOK_NAME   → "Dune (2021) film transcript"
#   SOURCE_FILE → demo/nextjs-reader/content/dune-2021-transcript.txt
#
# The script derives a slug from BOOK_NAME and writes to public/chronicle-<slug>/.
# To process a different document:
#   ./refresh-bundled-chronicle.sh "My Book" path/to/my-book.txt
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

BOOK_NAME="${1:-Dune (2021) film transcript}"
SOURCE_FILE="${2:-$REPO_ROOT/demo/nextjs-reader/content/dune-2021-transcript.txt}"

if [ ! -f "$SOURCE_FILE" ]; then
  echo "Error: source file not found: $SOURCE_FILE" >&2
  exit 1
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
PYTHON="${JULIA_READER_PYTHON:-$REPO_ROOT/.venv/bin/python3}"
export PYTHONPATH="${REPO_ROOT}/src"

"$PYTHON" -m julia_reader -f "$SOURCE_FILE" -o "$OUT" --no-llm --quiet

RUN="$(find "$OUT/_reader" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [ -z "$RUN" ]; then
  echo "Error: no _reader/ output found in $OUT" >&2
  exit 1
fi

# Derive slug from book name using the Python slugify function
SLUG="$("$PYTHON" -c "import sys; from julia_reader.output_scaffold import slugify; print(slugify(sys.argv[1]))" "$BOOK_NAME")"

DEST="$REPO_ROOT/demo/nextjs-reader/public/chronicle-${SLUG}"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$RUN/"* "$DEST/"

# Generate _demo-manifest.json using a temp Python script (avoids quoting issues)
PYSCRIPT="$(mktemp /tmp/chronicle-manifest-XXXXXX.py)"
trap 'rm -f "$PYSCRIPT"' EXIT
cat > "$PYSCRIPT" << 'PYEOF'
import json, sys
from pathlib import Path

dest = sys.argv[1]
book_name = sys.argv[2]
slug = sys.argv[3]

root = Path(dest)
files = sorted(
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file() and p.name != "_demo-manifest.json"
)
state = json.loads((root / "state" / "reader_state.json").read_text(encoding="utf-8"))
packet = json.loads((root / "state" / "reader_packet.json").read_text(encoding="utf-8"))
plan = json.loads((root / "state" / "book_plan.json").read_text(encoding="utf-8"))
source_title = state.get("source_title", book_name)
manifest = {
    "version": 1,
    "demoTitle": book_name,
    "demoNote": (
        "Chronicle from julia-reader on the bundled " + source_title + " "
        "(offline --no-llm run). "
        "Use your own API keys in .env for richer summaries; artifact layout is unchanged."
    ),
    "bundledReaderModel": packet.get("modelUsed", "local-fallback"),
    "sourceTitle": source_title,
    "slug": slug,
    "stats": {
        "sentences": state.get("total_sentences"),
        "chunks": state.get("total_chunks"),
        "chapters": len(plan.get("chapters", [])),
        "pages": sum(len(c.get("page_plan", [])) for c in plan.get("chapters", [])),
    },
    "files": files,
    "processingStatus": "complete",
}
(root / "_demo-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Wrote", len(files), "files under", root)
PYEOF

"$PYTHON" "$PYSCRIPT" "$DEST" "$BOOK_NAME" "$SLUG"

echo "Chronicle directory: $DEST"
echo "Slug: chronicle-${SLUG}"
