"""Markdown book writer for Reader chronicles — supports multi-page generation per chunk."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

from .reader_config import DEFAULT_PAGE_MAX_LINES


# ---------------------------------------------------------------------------
# Helpers for existing-page detection and subject-shift parsing
# ---------------------------------------------------------------------------

def get_existing_pages(directory: Path) -> tuple[list[int], dict[int, str]]:
    """Scan *directory* for page_*.md files and return (sorted nums, {num: content}).

    This is the foundation for continuation writes — it tells you what's already
    on disk so you can pick the next page number and avoid overwrites.
    """
    pages: dict[int, str] = {}
    for f in sorted(directory.glob("page_*.md")):
        match = re.match(r"page_(\d+)\.md", f.name)
        if match:
            num = int(match.group(1))
            pages[num] = f.read_text(encoding="utf-8")
    return sorted(pages.keys()), pages


def parse_subject_shifts(state_dir: Path) -> list[dict[str, str]]:
    """Read ``subject_shift_log.md`` from *state_dir* and return structured entries.

    Each entry is ``{"chunk_id": ..., "reason": ..., "subject": ...}``.
    Returns an empty list when the file is missing or empty.
    """
    log_path = state_dir / "subject_shift_log.md"
    if not log_path.is_file():
        return []
    entries: list[dict[str, str]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        # Format: "- `chunk_id` reason — subject"
        m = re.match(r"-\s+`([^`]+)`\s+(.*?)\s*—\s*(.*)", line)
        if m:
            entries.append({
                "chunk_id": m.group(1).strip(),
                "reason": m.group(2).strip(),
                "subject": m.group(3).strip(),
            })
    return entries


def _build_prior_context(existing_pages: dict[int, str]) -> str:
    """Format previously-written pages as context for deduplication."""
    if not existing_pages:
        return ""
    parts: list[str] = []
    for num in sorted(existing_pages):
        parts.append(f"### Previously Written — page_{num:03d}.md\n\n{existing_pages[num]}")
    return "\n\n".join(parts)


def _shifts_for_chunks(
    shifts: list[dict[str, str]],
    chunk_ids: list[str],
) -> list[dict[str, str]]:
    """Return shift entries relevant to the given *chunk_ids*."""
    return [s for s in shifts if s["chunk_id"] in chunk_ids]


# ---------------------------------------------------------------------------
# Internal template helpers
# ---------------------------------------------------------------------------

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


def _split_lines_at_shifts(
    lines: list[str],
    max_lines: int,
    chunk_ids: list[str],
    chunks_by_id: dict[str, dict[str, dict[str, Any]]],
    shifts: list[dict[str, str]],
) -> list[list[str]]:
    """Split *lines* respecting subject-shift boundaries.

    Identifies ``## `` section headers as candidate break points.  Greedily
    accumulates sections until adding the next section would exceed
    *max_lines*, then splits.  Falls back to plain line-count splitting when
    no shifts apply or there are no natural break points.
    """
    if len(lines) <= max_lines or not chunk_ids:
        return _split_lines(lines, max_lines)

    # Only use shift-aware splitting when there are relevant shifts
    relevant_shifts = _shifts_for_chunks(shifts, chunk_ids)
    if not relevant_shifts:
        return _split_lines(lines, max_lines)

    # Find all ## header positions (candidate break points)
    header_positions: list[int] = []
    for i, line in enumerate(lines):
        if i > 0 and line.startswith("## "):
            header_positions.append(i)

    if not header_positions:
        return _split_lines(lines, max_lines)

    # Greedy accumulation: collect sections between headers, flush a part
    # whenever adding the next section would exceed max_lines.
    parts: list[list[str]] = []
    current_part_start = 0
    for idx, header_pos in enumerate(header_positions):
        # The section from current_part_start up to (but not including) header_pos
        section_end = header_pos  # exclusive
        current_len = section_end - current_part_start
        # Next section length (up to the following header or end of lines)
        next_header = header_positions[idx + 1] if idx + 1 < len(header_positions) else len(lines)
        next_section_len = next_header - header_pos

        # If adding the next section would exceed max_lines, flush now
        if current_len > 0 and (current_len + next_section_len) > max_lines:
            parts.append(lines[current_part_start:section_end])
            current_part_start = section_end

    # Flush remaining
    if current_part_start < len(lines):
        remaining = lines[current_part_start:]
        if len(remaining) > max_lines:
            parts.extend(_split_lines(remaining, max_lines))
        elif remaining:
            parts.append(remaining)

    return parts if parts else [lines]


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


def _page_lines_with_context(
    page: dict[str, Any],
    chapter: dict[str, Any],
    chunks_by_id: dict[str, dict[str, Any]],
    page_number: int,
    prior_context: str,
    shift_context: str,
) -> list[str]:
    """Generate page lines with prior-page context injected for deduplication.

    When *page_number* > 1, a ``## Previously Written Pages`` section and
    deduplication instructions are prepended to the standard page template.
    """
    base_lines = _page_lines(page, chapter, chunks_by_id)

    if page_number <= 1 or not prior_context:
        return base_lines

    # Inject a continuation header after the title
    header = [
        "",
        "## Continuation Note",
        "",
        f"This is page {page_number:03d} for this topic. "
        "The pages below have already been written for this section.",
        "",
    ]
    if shift_context:
        header.extend([
            "## Subject-Shift Boundaries",
            "",
            shift_context,
            "",
        ])
    header.extend([
        "## Previously Written Pages",
        "",
        prior_context,
        "",
        "## Deduplication Instructions",
        "",
        "- Continue from where the last page ended.",
        "- Do NOT repeat any material, topics, examples, or phrasing from prior pages.",
        "- Respect the subject-shift boundaries listed above — if a boundary falls "
        "within your assigned section, end the page there.",
        "",
    ])

    # Insert header after the title line (index 0) and the blank line (index 1)
    return base_lines[:2] + header + base_lines[2:]


# ---------------------------------------------------------------------------
# Public API — write_book
# ---------------------------------------------------------------------------

def write_book(
    *,
    book_dir: Path,
    plan: dict[str, Any],
    chunks: list[dict[str, Any]],
    sentences: list[dict[str, Any]],
    reader_state: dict[str, Any],
    page_max_lines: int = DEFAULT_PAGE_MAX_LINES,
    state_dir: Path | None = None,
    max_pages_per_chunk: int = 1,
) -> dict[str, int]:
    """Write Markdown pages for each chapter in *plan*.

    Parameters
    ----------
    state_dir : Path | None
        Directory containing ``subject_shift_log.md``.  When provided, page
        splitting respects subject-shift boundaries.
    max_pages_per_chunk : int
        Maximum number of pages to generate per page-plan entry.  When > 1,
        content that exceeds *page_max_lines* is split into properly numbered
        ``page_002.md``, ``page_003.md``, … files instead of using suffixes.
        Default is 1 (original single-page behaviour).
    """
    chunks_by_id = _chunk_lookup(chunks)

    # Parse subject-shift boundaries once
    shifts: list[dict[str, str]] = []
    if state_dir is not None:
        shifts = parse_subject_shifts(state_dir)

    pages_written = 0
    chapters = plan.get("chapters", [])

    for chapter in chapters:
        folder = book_dir / f"{int(chapter['chapter_number']):02d}_{chapter['slug']}"
        folder.mkdir(parents=True, exist_ok=True)

        for page in chapter.get("page_plan", []):
            chunk_ids = list(page.get("chunk_ids", []))

            # --- Detect existing pages in this chapter folder ----------------
            existing_nums, existing_pages = get_existing_pages(folder)
            # Determine which existing pages belong to this page-plan entry
            # by matching against the expected filename pattern.
            base_filename = page["filename"]  # e.g. "page_001.md"
            base_match = re.match(r"page_(\d+)\.md", base_filename)
            base_num = int(base_match.group(1)) if base_match else 1

            # Calculate the highest existing page number for this entry
            # (pages sharing the same base number sequence)
            entry_existing: dict[int, str] = {}
            for num, content in existing_pages.items():
                entry_existing[num] = content

            # --- Build prior-page context for deduplication ------------------
            prior_context = _build_prior_context(entry_existing)

            # --- Format subject-shift context --------------------------------
            relevant_shifts = _shifts_for_chunks(shifts, chunk_ids)
            shift_context = ""
            if relevant_shifts:
                shift_lines = []
                for s in relevant_shifts:
                    shift_lines.append(f"- Chunk `{s['chunk_id']}`: {s['reason']} → {s['subject']}")
                shift_context = "\n".join(shift_lines)

            # --- Generate content --------------------------------------------
            if max_pages_per_chunk <= 1:
                # Original behaviour: single page, simple line split with suffixes
                parts = _split_lines(_page_lines(page, chapter, chunks_by_id), page_max_lines)
                for idx, lines in enumerate(parts):
                    if idx == 0:
                        filename = base_filename
                    else:
                        filename = base_filename.replace(".md", f"_{idx + 1:02d}.md")
                    _safe_write(folder / filename, lines)
                    pages_written += 1
            else:
                # Multi-page: use subject-shift-aware splitting
                raw_lines = _page_lines(page, chapter, chunks_by_id)
                if shifts:
                    parts = _split_lines_at_shifts(
                        raw_lines, page_max_lines, chunk_ids, chunks_by_id, shifts,
                    )
                else:
                    parts = _split_lines(raw_lines, page_max_lines)

                # Cap at max_pages_per_chunk
                parts = parts[:max_pages_per_chunk]

                for idx, part_lines in enumerate(parts):
                    page_num = base_num + idx
                    filename = f"page_{page_num:03d}.md"

                    # For continuation pages (idx > 0), inject prior context
                    # from both pre-existing pages and pages already written
                    # in this run to enable deduplication.
                    if idx > 0:
                        # Gather content from all previously written parts
                        all_prior = dict(entry_existing)
                        for prev_idx in range(idx):
                            prev_num = base_num + prev_idx
                            prev_content = "\n".join(parts[prev_idx]).rstrip() + "\n"
                            all_prior[prev_num] = prev_content
                        ctx = _build_prior_context(all_prior)
                        if ctx or shift_context:
                            rendered = _page_lines_with_context(
                                page, chapter, chunks_by_id,
                                page_number=page_num,
                                prior_context=ctx,
                                shift_context=shift_context,
                            )
                        else:
                            rendered = part_lines
                    else:
                        rendered = part_lines

                    _safe_write(folder / filename, rendered)
                    pages_written += 1

    _write_preface(book_dir, reader_state)
    _write_index(book_dir, reader_state, plan, sentences, chunks, pages_written)
    return {"chapters": len(chapters), "pages": pages_written}


def _safe_write(path: Path, lines: list[str]) -> None:
    """Write *lines* to *path*, raising ``FileExistsError`` if it already exists."""
    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing page: {path}. "
            f"Delete it manually or adjust page numbering to continue."
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Preface & Index
# ---------------------------------------------------------------------------

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
