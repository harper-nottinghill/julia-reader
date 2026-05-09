"""Validation pass for Reader chronicles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .reader_config import DEFAULT_MAX_CHUNK_TOKENS, DEFAULT_PAGE_MAX_LINES, ReaderPaths


def validate_reader_run(
    *,
    paths: ReaderPaths,
    sentences: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    state: dict[str, Any],
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    page_max_lines: int = DEFAULT_PAGE_MAX_LINES,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    report_path = paths.logs / "validation_report.md"
    report_path.touch(exist_ok=True)

    required = [
        paths.source / "raw_input.txt",
        paths.source / "normalized_input.txt",
        paths.source / "break_marked_input.md",
        paths.state / "reader_state.json",
        paths.state / "sentence_map.json",
        paths.state / "chunk_map.json",
        paths.state / "lake_strings.json",
        paths.state / "break_map.json",
        paths.state / "reader_packet.json",
        paths.state / "subject_index.json",
        paths.state / "sentiment_index.json",
        paths.state / "live_summary.md",
        paths.book / "00_index.md",
        paths.book / "01_preface.md",
        paths.root / "packet" / "packet.json",
    ]
    for p in required:
        if not p.exists():
            errors.append(f"Missing required file: {p.relative_to(paths.root)}")

    for s in sentences:
        if not s.get("chunk_id"):
            errors.append(f"Sentence missing chunk_id: {s.get('sentence_id')}")
    for c in chunks:
        if int(c.get("estimated_tokens", 0)) > max_chunk_tokens:
            errors.append(f"Chunk exceeds max tokens: {c.get('chunk_id')}={c.get('estimated_tokens')}")
        if c.get("status") not in {"assigned", "summarized"}:
            warnings.append(f"Chunk not marked assigned/summarized: {c.get('chunk_id')}")
        if "break_count" not in c:
            warnings.append(f"Chunk missing break_count: {c.get('chunk_id')}")

    plan_path = paths.state / "book_plan.json"
    plan = {}
    if plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid book_plan.json: {exc}")
    assigned = {
        cid
        for ch in plan.get("chapters", [])
        for page in ch.get("page_plan", [])
        for cid in page.get("chunk_ids", [])
    }
    for c in chunks:
        if c.get("chunk_id") not in assigned:
            errors.append(f"Chunk not assigned to a page: {c.get('chunk_id')}")

    chapter_dirs = [p for p in paths.book.iterdir() if p.is_dir()] if paths.book.exists() else []
    for d in chapter_dirs:
        pages = sorted(d.glob("*.md"))
        if not pages:
            errors.append(f"Empty chapter folder: {d.relative_to(paths.root)}")
        for p in pages:
            text = p.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                errors.append(f"Empty page file: {p.relative_to(paths.root)}")
            if text.count("\n") + 1 > page_max_lines:
                errors.append(f"Page exceeds {page_max_lines} lines: {p.relative_to(paths.root)}")

    index = paths.book / "00_index.md"
    if index.exists():
        text = index.read_text(encoding="utf-8", errors="replace")
        import re

        for rel in re.findall(r"\]\(([^)]+)\)", text):
            if rel.startswith(("http://", "https://", "#")):
                continue
            target = (paths.book / rel).resolve()
            if not target.exists():
                errors.append(f"Index link does not resolve: {rel}")
    if state.get("status") != "complete":
        errors.append(f"reader_state status is not complete: {state.get('status')}")

    report = ["# Reader Validation Report", "", "## Errors", ""]
    report.extend(f"- {e}" for e in (errors or ["None"]))
    report.extend(["", "## Warnings", ""])
    report.extend(f"- {w}" for w in (warnings or ["None"]))
    report_path.write_text("\n".join(report).rstrip() + "\n", encoding="utf-8")
    return errors, warnings
