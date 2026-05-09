#!/usr/bin/env bash
# Regenerate public/chronicle-dune from content/dune-2021-transcript.txt (run from repo root).
# Transcript source: https://scrapsfromtheloft.com/movies/dune-2021-transcript/ (third-party; trim site chrome before committing updates).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
PYTHON="${JULIA_READER_PYTHON:-$REPO_ROOT/.venv/bin/python3}"
"$PYTHON" -m julia_reader -f "$REPO_ROOT/demo/nextjs-reader/content/dune-2021-transcript.txt" -o "$OUT" --no-llm --quiet
RUN="$(find "$OUT/_reader" -mindepth 1 -maxdepth 1 -type d | head -1)"
DEST="$REPO_ROOT/demo/nextjs-reader/public/chronicle-dune"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$RUN/"* "$DEST/"
"$PYTHON" << PY
import json
from pathlib import Path
root = Path("$DEST")
files = sorted(
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file() and p.name != "_demo-manifest.json"
)
state = json.loads((root / "state" / "reader_state.json").read_text(encoding="utf-8"))
packet = json.loads((root / "state" / "reader_packet.json").read_text(encoding="utf-8"))
plan = json.loads((root / "state" / "book_plan.json").read_text(encoding="utf-8"))
manifest = {
  "version": 1,
  "demoTitle": "Dune (2021) film transcript",
  "demoNote": (
    "Chronicle from julia-reader on the bundled Dune (2021) transcript "
    "(third-party text from scrapsfromtheloft.com; offline --no-llm run). "
    "Use your own API keys in .env for richer summaries; artifact layout is unchanged."
  ),
  "bundledReaderModel": packet.get("modelUsed", "local-fallback"),
  "sourceTitle": state.get("source_title"),
  "stats": {
    "sentences": state.get("total_sentences"),
    "chunks": state.get("total_chunks"),
    "chapters": len(plan.get("chapters", [])),
    "pages": sum(len(c.get("page_plan", [])) for c in plan.get("chapters", [])),
  },
  "files": files,
}
(root / "_demo-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Wrote", len(files), "files under", root)
PY
