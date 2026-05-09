"""Dynamic sentence chunking for Reader."""

from __future__ import annotations

from typing import Any

from .reader_config import DEFAULT_MAX_CHUNK_TOKENS, DEFAULT_TARGET_CHUNK_TOKENS
from .subject_shift import subject_shift_reason


def _new_chunk(idx: int, sentences: list[dict[str, Any]], reason: str = "") -> dict[str, Any]:
    toks = sum(int(s.get("estimated_tokens", 0)) for s in sentences)
    return {
        "chunk_id": f"C{idx:04d}",
        "sentence_ids": [s["sentence_id"] for s in sentences],
        "estimated_tokens": toks,
        "start_sentence": sentences[0]["sentence_id"],
        "end_sentence": sentences[-1]["sentence_id"],
        "detected_subject": "",
        "subject_shift_reason": reason,
        "summary": "",
        "key_points": [],
        "open_questions": [],
        "possible_chapter": "",
        "important_entities": [],
        "action_items": [],
        "repeated_themes": [],
        "contradictions": [],
        "status": "pending",
    }


def build_chunks(
    sentences: list[dict[str, Any]],
    *,
    target_tokens: int = DEFAULT_TARGET_CHUNK_TOKENS,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    cur: list[dict[str, Any]] = []
    cur_tokens = 0
    pending_reason = ""

    def flush(reason: str = "") -> None:
        nonlocal cur, cur_tokens, pending_reason
        if not cur:
            return
        chunks.append(_new_chunk(len(chunks) + 1, cur, reason or pending_reason))
        cur = []
        cur_tokens = 0
        pending_reason = ""

    for sent in sentences:
        stoks = int(sent.get("estimated_tokens", 0))
        reason = subject_shift_reason(sent, cur)
        natural_boundary = bool(reason)
        if cur and cur_tokens + stoks > max_tokens:
            flush("adding next sentence would exceed max chunk tokens")
        elif cur and cur_tokens >= target_tokens and natural_boundary:
            flush(reason)
        elif cur and cur_tokens >= target_tokens and str(cur[-1].get("text", "")).endswith((".", "?", "!")):
            flush("near target size and reached natural sentence boundary")

        if not cur and natural_boundary:
            pending_reason = reason
        cur.append(sent)
        cur_tokens += stoks

    flush()
    by_id = {sid: ch["chunk_id"] for ch in chunks for sid in ch["sentence_ids"]}
    for sent in sentences:
        sent["chunk_id"] = by_id.get(sent["sentence_id"])
    return chunks
