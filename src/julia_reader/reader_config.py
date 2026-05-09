"""Configuration and path helpers for the Julia Reader harness."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TARGET_CHUNK_TOKENS = 1800
DEFAULT_MAX_CHUNK_TOKENS = 2000
DEFAULT_PAGE_MAX_LINES = 1000


@dataclass(frozen=True)
class ReaderPaths:
    root: Path
    source: Path
    state: Path
    book: Path
    logs: Path


def estimate_tokens(text: str) -> int:
    """Cheap tokenizer estimate used throughout Reader."""
    return max(1, (len(text or "") + 3) // 4)


def safe_slug(text: str, *, fallback: str = "reader_run", max_words: int = 12) -> str:
    words = re.findall(r"[A-Za-z0-9]+", (text or "").strip().lower())
    if not words:
        return fallback
    slug = "_".join(words[:max_words])
    return slug[:80].strip("_") or fallback


def detect_title(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "Reader Run"
        if len(stripped.split()) >= 3:
            return " ".join(stripped.split()[:12])
    return "Reader Run"


def make_run_paths(base_dir: Path, source_text: str, *, now: _dt.datetime | None = None) -> ReaderPaths:
    ts = (now or _dt.datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    title = detect_title(source_text)
    slug = safe_slug(title)
    # Chronicle root: ``<base_dir>/_reader/<timestamp>_<slug>/``
    root = base_dir / "_reader" / f"{ts}_{slug}"
    paths = ReaderPaths(
        root=root,
        source=root / "source",
        state=root / "state",
        book=root / "book",
        logs=root / "logs",
    )
    for p in (paths.source, paths.state, paths.book, paths.logs):
        p.mkdir(parents=True, exist_ok=True)
    return paths
