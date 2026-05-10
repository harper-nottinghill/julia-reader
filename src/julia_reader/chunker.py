"""Dynamic sentence chunking for Reader."""

from __future__ import annotations

from typing import Any

from .reader_config import DEFAULT_MAX_CHUNK_TOKENS, DEFAULT_MIN_CHUNK_TOKENS, DEFAULT_TARGET_CHUNK_TOKENS
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
    min_tokens: int = DEFAULT_MIN_CHUNK_TOKENS,
) -> list[dict[str, Any]]:
    """Build chunks from a list of sentence records.

    Parameters
    ----------
    sentences:
        Sentence dicts produced by :func:`split_sentences`.
    target_tokens:
        Soft target — once accumulated tokens reach this level, the chunker
        looks for the next natural boundary to flush.
    max_tokens:
        Hard cap — adding the next sentence would exceed this, so the current
        chunk is flushed immediately.
    min_tokens:
        When merging the final chunk, if it is below *min_tokens* it will be
        folded into the previous chunk (if any) to avoid tiny orphans.
        Set to ``0`` to disable merging.
    """
    if not sentences:
        return []

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

    # Merge tiny trailing chunk into the previous one to avoid orphans.
    if (
        min_tokens > 0
        and len(chunks) >= 2
        and chunks[-1]["estimated_tokens"] < min_tokens
    ):
        last = chunks.pop()
        prev = chunks[-1]
        prev["sentence_ids"].extend(last["sentence_ids"])
        prev["estimated_tokens"] += last["estimated_tokens"]
        prev["end_sentence"] = last["end_sentence"]
        if not prev["subject_shift_reason"]:
            prev["subject_shift_reason"] = last.get("subject_shift_reason", "")

    # If we still ended up with zero chunks but had sentences, force one.
    if not chunks and sentences:
        chunks.append(_new_chunk(1, sentences, "entire document as single chunk"))

    by_id = {sid: ch["chunk_id"] for ch in chunks for sid in ch["sentence_ids"]}
    for sent in sentences:
        sent["chunk_id"] = by_id.get(sent["sentence_id"])
    return chunks
