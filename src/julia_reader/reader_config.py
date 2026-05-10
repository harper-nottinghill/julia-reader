"""Configuration and path helpers for the Julia Reader harness."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

DEFAULT_TARGET_CHUNK_TOKENS = 1800
DEFAULT_MAX_CHUNK_TOKENS = 2000
DEFAULT_MIN_CHUNK_TOKENS = 100
DEFAULT_PAGE_MAX_LINES = 1000

# Retry settings for transient LLM API failures (rate limits, timeouts, 5xx).
# Override via environment variables JULIA_READER_LLM_MAX_RETRIES / JULIA_READER_LLM_RETRY_BASE_DELAY.
import os as _os

LLM_MAX_RETRIES = int(_os.environ.get("JULIA_READER_LLM_MAX_RETRIES", "3"))
LLM_RETRY_BASE_DELAY = float(_os.environ.get("JULIA_READER_LLM_RETRY_BASE_DELAY", "1.0"))


@dataclass(frozen=True)
class ReaderPaths:
    """Resolved filesystem layout for a single Reader Chronicle run.

    Every sub-module receives the paths it needs from this object — none
    construct directory names internally.
    """

    root: Path
    source: Path
    state: Path
    book: Path
    logs: Path
    packet: Path


@dataclass(frozen=True)
class PipelineConfig:
    """Full configuration for a Reader pipeline invocation.

    Encapsulates resolved paths, LLM wiring, and tuning knobs so callers
    only pass a single object rather than a long parameter list.
    """

    paths: ReaderPaths
    raw_text: str
    complete: Callable[[str, str], str] | None
    model_label: str
    use_llm: bool = True
    live: bool = True
    max_pages_per_chunk: int = 1
    prompt_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "prompts")


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
        packet=root / "packet",
    )
    for p in (paths.source, paths.state, paths.book, paths.logs, paths.packet):
        p.mkdir(parents=True, exist_ok=True)
    return paths
