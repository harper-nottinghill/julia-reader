"""Markdown book writer for Reader chronicles."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from .reader_config import DEFAULT_PAGE_MAX_LINES


def _chunk_lookup(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {c["chunk_id"]: c for c in chunks}


def _sent_range(chunk_ids: list[str], chunks_by_id: dict[str, dict[str, Any]]) -> str:
    starts = [chunks_by_id[c]["start_sentence"] for c in chunk_ids if c in chunks_by_id]
    ends = [chunks_by_id[c]["end_sentence"] for c in chunk_ids if c in chunks_by_id]
    return f"{starts[0]} - {ends[-1]}" if starts and ends else "(unknown)"


def _split_lines(lines: list[str], max_lines: int) -> list[list[str]]:
    if len(lines) <= max_lines:
        return [lines]
    return [lines[i : i + max_lines] for i in range(0, len(lines), max_lines)]


def _page_lines(page: dict[str, Any], chapter: dict[str, Any], chunks_by_id: dict[str, dict[str, Any]]) -> list[str]:
    chunk_ids = list(page.get("chunk_ids", []))
    chunks = [chunks_by_id[cid] for cid in chunk_ids if cid in chunks_by_id]
    key_details: list[str] = []
    questions: list[str] = []
    actions: list[str] = []
    notes: list[str] = []
    for ch in chunks:
        key_details.extend(str(x) for x in ch.get("key_points", []))
        questions.extend(str(x) for x in ch.get("open_questions", []))
        actions.extend(str(x) for x in ch.get("action_items", []))
        notes.append(str(ch.get("summary", "")).strip())
    summary = "\n\n".join(n for n in notes if n).strip() or "No summary was generated for this source span."
    lines = [
        f"# {page['title']}",
        "",
        "## Source Coverage",
        f"- Chapter: {chapter['title']}",
        f"- Source chunks: {', '.join(chunk_ids)}",
        f"- Sentence range: {_sent_range(chunk_ids, chunks_by_id)}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Key Details",
        "",
    ]
    lines.extend(f"- {item}" for item in (key_details[:30] or ["No key details extracted."]))
    lines.extend(["", "## Expanded Explanation", "", summary, "", "## Important Source Notes", ""])
    for ch in chunks:
        lines.append(f"- `{ch['chunk_id']}` subject: {ch.get('detected_subject') or '(undetected)'}")
        if ch.get("breaks"):
            lines.append(f"  - Breaks in span: {len(ch['breaks'])}")
        if ch.get("subject_shift_reason"):
            lines.append(f"  - Shift reason: {ch['subject_shift_reason']}")
    lines.extend(["", "## Questions / Implications", ""])
    lines.extend(f"- {q}" for q in (questions[:20] or ["No explicit open questions extracted."]))
    if actions:
        lines.extend(["", "## Action Items", ""])
        lines.extend(f"- {a}" for a in actions[:20])
    lines.extend(["", "## Related Pages", "", "- See `../00_index.md` for the full book map."])
    return lines


def write_book(
    *,
    book_dir: Path,
    plan: dict[str, Any],
    chunks: list[dict[str, Any]],
    sentences: list[dict[str, Any]],
    reader_state: dict[str, Any],
    page_max_lines: int = DEFAULT_PAGE_MAX_LINES,
) -> dict[str, int]:
    chunks_by_id = _chunk_lookup(chunks)
    pages_written = 0
    chapters = plan.get("chapters", [])
    for chapter in chapters:
        folder = book_dir / f"{int(chapter['chapter_number']):02d}_{chapter['slug']}"
        folder.mkdir(parents=True, exist_ok=True)
        for page in chapter.get("page_plan", []):
            parts = _split_lines(_page_lines(page, chapter, chunks_by_id), page_max_lines)
            for idx, lines in enumerate(parts):
                filename = page["filename"] if idx == 0 else page["filename"].replace(".md", f"_{idx + 1:02d}.md")
                (folder / filename).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
                pages_written += 1
    _write_preface(book_dir, reader_state)
    _write_index(book_dir, reader_state, plan, sentences, chunks, pages_written)
    return {"chapters": len(chapters), "pages": pages_written}


def _write_preface(book_dir: Path, state: dict[str, Any]) -> None:
    body = f"""# Preface

This generated book was created by the Julia Reader harness.

## Source

- Title: {state.get("source_title", "Reader Run")}
- Generated: {state.get("created_at", "")}

## How It Was Processed

The source was saved verbatim, normalized conservatively, split into sentence IDs, chunked under the configured token ceiling, summarized progressively, then written into chapter/page Markdown.

## How To Use This Book

Start with `00_index.md`, then follow chapter folders and page files. Every page preserves source chunk IDs and sentence ranges so you can trace interpretations back to the maps under `../state/`.

## Limits

Reader preserves traceability and avoids inventing facts, but generated summaries are still interpretive. Use `source/raw_input.txt`, `state/sentence_map.json`, and `state/chunk_map.json` for audit.
"""
    (book_dir / "01_preface.md").write_text(body, encoding="utf-8")


def _write_index(
    book_dir: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
    sentences: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    pages_written: int,
) -> None:
    chapters = plan.get("chapters", [])
    lines = [
        "# Index",
        "",
        "## Source",
        f"- Title: {state.get('source_title', 'Reader Run')}",
        f"- Date generated: {_dt.datetime.now().isoformat()}",
        f"- Total characters: {state.get('total_characters', 0)}",
        f"- Total sentences: {len(sentences)}",
        f"- Total chunks: {len(chunks)}",
        f"- Total chapters: {len(chapters)}",
        f"- Total pages: {pages_written}",
        "",
        "## Book Structure",
        "",
        "- [Preface](01_preface.md)",
    ]
    for chapter in chapters:
        folder = f"{int(chapter['chapter_number']):02d}_{chapter['slug']}"
        lines.append(f"- {chapter['title']}")
        for page in chapter.get("page_plan", []):
            lines.append(f"  - [{page['title']}]({folder}/{page['filename']})")
    lines.extend(["", "## Major Themes", ""])
    lines.extend(f"- {t}" for t in (state.get("main_topics", [])[:20] or ["No themes extracted."]))
    lines.extend(["", "## Key Questions", ""])
    qs: list[str] = []
    for ch in chunks:
        qs.extend(str(x) for x in ch.get("open_questions", []))
    lines.extend(f"- {q}" for q in (qs[:20] or ["No explicit questions extracted."]))
    lines.extend(["", "## Action Items", ""])
    acts: list[str] = []
    for ch in chunks:
        acts.extend(str(x) for x in ch.get("action_items", []))
    lines.extend(f"- {a}" for a in (acts[:20] or ["No action items extracted."]))
    lines.extend(
        [
            "",
            "## Source Maps",
            "",
            "- [Sentence map](../state/sentence_map.json)",
            "- [Chunk map](../state/chunk_map.json)",
            "- [Lake Strings](../state/lake_strings.json)",
            "- [Break map](../state/break_map.json)",
            "- [Reader packet](../state/reader_packet.json)",
            "- [Break-marked source](../source/break_marked_input.md)",
            "- [Live summary](../state/live_summary.md)",
            "- [Validation report](../logs/validation_report.md)",
        ]
    )
    (book_dir / "00_index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
