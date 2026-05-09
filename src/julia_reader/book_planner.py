"""Book-plan generation for Reader chronicles."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .reader_config import safe_slug


def build_book_plan(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
    for chunk in chunks:
        title = str(chunk.get("possible_chapter") or chunk.get("detected_subject") or "Reader Notes").strip()
        title = title[:90] or "Reader Notes"
        grouped.setdefault(title, []).append(chunk)

    chapters = []
    for idx, (title, ch_chunks) in enumerate(grouped.items(), 2):
        chapter_id = f"CH{idx:03d}"
        page_plan = []
        for pidx, chunk in enumerate(ch_chunks, 1):
            page_plan.append(
                {
                    "page_id": f"{chapter_id}_P{pidx:03d}",
                    "filename": f"page_{pidx:03d}.md",
                    "title": str(chunk.get("detected_subject") or title or f"Page {pidx}").title()[:90],
                    "chunk_ids": [chunk["chunk_id"]],
                }
            )
        chapters.append(
            {
                "chapter_id": chapter_id,
                "chapter_number": idx,
                "title": title,
                "slug": safe_slug(title, fallback=f"chapter_{idx:03d}"),
                "description": f"Reader chapter covering {title}.",
                "chunk_ids": [c["chunk_id"] for c in ch_chunks],
                "page_plan": page_plan,
            }
        )
    return {"chapters": chapters}
