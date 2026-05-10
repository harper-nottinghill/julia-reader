"""Dynamic output directory scaffolding for any book in the Chronicle pipeline.

Generates the full output directory structure (source/, state/, book/, packet/, logs/)
for any given book name. Replaces the static chronicle-dune layout so the NextJS demo
can discover and render outputs from any processed document.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Slug derivation
# ---------------------------------------------------------------------------

def slugify(name: str, *, fallback: str = "untitled", max_length: int = 64) -> str:
    """Convert a book name to a filesystem-safe, hyphenated slug.

    Rules:
      1. Transliterate to ASCII (best-effort).
      2. Lowercase.
      3. Replace any run of non-alphanumeric characters with a single hyphen.
      4. Strip leading/trailing hyphens.
      5. Truncate to *max_length* characters.
      6. Fallback to *fallback* if the result is empty.
    """
    # Transliterate to ASCII (e.g. é → e, ü → u)
    try:
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    except Exception:
        ascii_name = name
    slug = ascii_name.lower()
    # Replace non-alphanumeric runs with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or fallback


def _unique_slug(base_path: Path, slug: str) -> str:
    """Return *slug*, appending ``-2``, ``-3``, … if the directory already exists."""
    candidate = slug
    counter = 2
    while (base_path / candidate).exists():
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


# ---------------------------------------------------------------------------
# Directory scaffolding
# ---------------------------------------------------------------------------

_SUBDIRS = ("source", "state", "book", "packet", "logs")


def scaffold_output_dir(
    base_path: Path,
    book_name: str,
    *,
    exist_ok: bool = False,
) -> Path:
    """Create the full Chronicle output directory tree for *book_name*.

    Returns the root path ``<base_path>/chronicle-<slug>/``.
    Raises ``FileExistsError`` if the directory already exists and
    *exist_ok* is ``False``.
    """
    base_path = Path(base_path)
    slug = slugify(book_name)
    slug = _unique_slug(base_path, slug)
    root = base_path / f"chronicle-{slug}"

    if root.exists() and not exist_ok:
        raise FileExistsError(f"Chronicle directory already exists: {root}")

    for sub in _SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)

    return root


# ---------------------------------------------------------------------------
# Manifest generation
# ---------------------------------------------------------------------------

def generate_manifest(
    chronicle_dir: Path,
    book_name: str,
    *,
    source_filename: str = "",
    file_size_bytes: int = 0,
    file_type: str = "",
    demo_title: str = "",
    demo_note: str = "",
    bundled_reader_model: str = "local-fallback",
    chunk_count: int = 0,
    chapter_count: int = 0,
    page_count: int = 0,
    sentence_count: int = 0,
    files: list[str] | None = None,
    processing_status: str = "initialized",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``_demo-manifest.json`` into *chronicle_dir* and return the manifest dict.

    The format matches what ``ChronicleExplorer.tsx`` expects:
    ``version``, ``demoTitle``, ``demoNote``, ``bundledReaderModel``,
    ``sourceTitle``, ``stats``, ``files``, plus optional extension fields.
    """
    chronicle_dir = Path(chronicle_dir)
    slug = chronicle_dir.name.replace("chronicle-", "", 1)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    if not demo_title:
        demo_title = book_name
    if not source_filename:
        source_filename = book_name

    manifest: dict[str, Any] = {
        "version": 1,
        "demoTitle": demo_title,
        "demoNote": demo_note or f"Chronicle from julia-reader on {book_name}.",
        "bundledReaderModel": bundled_reader_model,
        "sourceTitle": book_name,
        "slug": slug,
        "createdAt": now,
        "updatedAt": now,
        "stats": {
            "sentences": sentence_count,
            "chunks": chunk_count,
            "chapters": chapter_count,
            "pages": page_count,
        },
        "files": files or [],
        "processingStatus": processing_status,
        "source": {
            "filename": source_filename,
            "fileSizeBytes": file_size_bytes,
            "fileType": file_type,
        },
    }

    if metadata:
        manifest["metadata"] = metadata

    manifest_path = chronicle_dir / "_demo-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def update_manifest(
    chronicle_dir: Path,
    *,
    chunk_count: int | None = None,
    sentence_count: int | None = None,
    chapter_count: int | None = None,
    page_count: int | None = None,
    processing_status: str | None = None,
    files: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update an existing ``_demo-manifest.json`` with new values.

    Always bumps ``updatedAt``.  Returns the updated manifest dict.
    """
    manifest_path = Path(chronicle_dir) / "_demo-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No _demo-manifest.json in {chronicle_dir}")

    manifest: dict[str, Any] = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    manifest["updatedAt"] = _dt.datetime.now(_dt.timezone.utc).isoformat()

    if processing_status is not None:
        manifest["processingStatus"] = processing_status

    stats = manifest.setdefault("stats", {})
    if chunk_count is not None:
        stats["chunks"] = chunk_count
    if sentence_count is not None:
        stats["sentences"] = sentence_count
    if chapter_count is not None:
        stats["chapters"] = chapter_count
    if page_count is not None:
        stats["pages"] = page_count

    if files is not None:
        manifest["files"] = files

    if extra:
        manifest.update(extra)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


# ---------------------------------------------------------------------------
# Seed stub files
# ---------------------------------------------------------------------------

def seed_stub_files(chronicle_dir: Path, book_slug: str) -> None:
    """Create minimal placeholder files so downstream tools don't crash."""
    chronicle_dir = Path(chronicle_dir)

    # source/metadata.json
    meta = chronicle_dir / "source" / "metadata.json"
    if not meta.exists():
        meta.write_text(
            json.dumps({"imported": False}, indent=2) + "\n", encoding="utf-8"
        )

    # state/progress.json
    prog = chronicle_dir / "state" / "progress.json"
    if not prog.exists():
        prog.write_text(
            json.dumps({"stage": "scaffolded", "percent": 0}, indent=2) + "\n",
            encoding="utf-8",
        )

    # logs/processing.log
    plog = chronicle_dir / "logs" / "processing.log"
    if not plog.exists():
        plog.write_text(
            f"# Processing log for {book_slug}\n", encoding="utf-8"
        )

    # logs/errors.log
    elog = chronicle_dir / "logs" / "errors.log"
    if not elog.exists():
        elog.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Full scaffold (convenience wrapper)
# ---------------------------------------------------------------------------

def scaffold_book(
    base_path: Path,
    book_name: str,
    *,
    source_filename: str = "",
    file_size_bytes: int = 0,
    file_type: str = "",
    exist_ok: bool = False,
) -> Path:
    """Scaffold a complete Chronicle output directory with manifest and stubs.

    Returns the chronicle root directory.
    """
    root = scaffold_output_dir(base_path, book_name, exist_ok=exist_ok)
    slug = root.name.replace("chronicle-", "", 1)

    generate_manifest(
        root,
        book_name,
        source_filename=source_filename,
        file_size_bytes=file_size_bytes,
        file_type=file_type,
    )
    seed_stub_files(root, slug)
    return root


# ---------------------------------------------------------------------------
# Discover existing books (used by NextJS demo)
# ---------------------------------------------------------------------------

def discover_chronicles(public_dir: Path) -> list[dict[str, Any]]:
    """Scan *public_dir* for directories containing ``_demo-manifest.json``.

    Returns a list of manifest dicts sorted by ``createdAt`` descending.
    """
    results: list[dict[str, Any]] = []
    public_dir = Path(public_dir)
    if not public_dir.is_dir():
        return results

    for child in sorted(public_dir.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "_demo-manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["_dir"] = child.name
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    results.sort(key=lambda m: m.get("createdAt", ""), reverse=True)
    return results
