"""Incremental live understanding — LLM via OpenAI-compatible HTTP."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from .error_logger import log_error
from .reader_config import estimate_tokens
from .subject_shift import keywords


def _extract_json(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    blob = fence.group(1) if fence else raw
    brace = re.search(r"\{[\s\S]*\}", blob)
    if not brace:
        return None
    try:
        data = json.loads(brace.group())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _fallback_chunk_update(chunk_text: str, previous_summary: str, chunk: dict[str, Any]) -> dict[str, Any]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chunk_text) if s.strip()]
    key_points = sentences[:5]
    words = sorted(keywords(chunk_text))
    subject = " ".join(words[:5]) or "reader notes"
    summary = " ".join(key_points)[:1200] or chunk_text[:1200]
    live = (previous_summary.strip() + "\n\n" if previous_summary.strip() else "")
    live += f"## {chunk['chunk_id']} — {subject}\n\n{summary}\n"
    return {
        "chunk_summary": summary,
        "updated_live_summary": live.strip() + "\n",
        "detected_subject": subject,
        "subject_shift_reason": chunk.get("subject_shift_reason", ""),
        "key_points": key_points,
        "open_questions": [s for s in sentences if s.endswith("?")][:5],
        "possible_chapter": subject.title()[:80],
        "important_entities": [],
        "action_items": [s for s in sentences if re.search(r"\b(todo|must|should|need to|action)\b", s, re.I)][:5],
        "repeated_themes": words[:8],
        "contradictions": [],
    }


def summarize_chunk(
    *,
    complete: Callable[[str, str], str] | None,
    model_label: str,
    chunk: dict[str, Any],
    chunk_text: str,
    previous_live_summary: str,
    reader_state: dict[str, Any],
    prompt_dir: Path,
    llm_log_path: Path,
    errors_path: Path,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Summarize one chunk with an LLM, falling back to local extraction."""
    system = (prompt_dir / "chunk_summary.md").read_text(encoding="utf-8")
    user = json.dumps(
        {
            "chunk_id": chunk["chunk_id"],
            "chunk_text": chunk_text,
            "previous_live_summary": previous_live_summary[-8000:],
            "reader_state": {
                "main_topics": reader_state.get("main_topics", []),
                "chapter_candidates": reader_state.get("chapter_candidates", []),
            },
            "subject_shift_reason": chunk.get("subject_shift_reason", ""),
        },
        ensure_ascii=False,
        indent=2,
    )
    log_entry: dict[str, Any] = {
        "timestamp": _dt.datetime.now().isoformat(),
        "prompt_type": "chunk_summary",
        "chunk_id": chunk["chunk_id"],
        "input_token_estimate": estimate_tokens(system + user),
        "output_token_estimate": None,
        "model": model_label,
        "success": False,
        "error": "",
    }
    data: dict[str, Any] | None = None
    disabled = os.environ.get("JULIA_READER_DISABLE_LLM", "").strip().lower() in ("1", "true", "yes", "on")
    if use_llm and complete is not None and not disabled:
        for attempt in (1, 2):
            try:
                text = complete(system, user)
                log_entry["output_token_estimate"] = estimate_tokens(text or "")
                data = _extract_json(text or "")
                if data:
                    log_entry["success"] = True
                    break
                raise ValueError("model response did not contain JSON")
            except Exception as exc:  # noqa: PERF203
                log_entry["error"] = f"attempt {attempt}: {exc}"
                log_error(
                    error_type="llm_error",
                    message=f"LLM call failed for chunk {chunk['chunk_id']} (attempt {attempt}): {exc}",
                    affected_id=chunk["chunk_id"],
                    details={"attempt": attempt, "model": model_label},
                    errors_path=errors_path,
                )
    if not data:
        data = _fallback_chunk_update(chunk_text, previous_live_summary, chunk)
        log_entry["success"] = False
        log_entry["error"] = log_entry["error"] or "local fallback used"
        log_entry["output_token_estimate"] = estimate_tokens(json.dumps(data))
    with llm_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return data


def apply_update(chunk: dict[str, Any], reader_state: dict[str, Any], update: dict[str, Any]) -> None:
    chunk["summary"] = str(update.get("chunk_summary", "")).strip()
    chunk["detected_subject"] = str(update.get("detected_subject", "")).strip()
    chunk["subject_shift_reason"] = str(
        update.get("subject_shift_reason", chunk.get("subject_shift_reason", ""))
    ).strip()
    for key in (
        "key_points",
        "open_questions",
        "important_entities",
        "action_items",
        "repeated_themes",
        "contradictions",
    ):
        val = update.get(key, [])
        chunk[key] = val if isinstance(val, list) else []
    chunk["possible_chapter"] = str(update.get("possible_chapter", "")).strip()
    chunk["status"] = "summarized"
    live = str(update.get("updated_live_summary", "")).strip()
    if live:
        reader_state["current_understanding"] = live
    for topic in chunk.get("repeated_themes", [])[:5]:
        if topic and topic not in reader_state["main_topics"]:
            reader_state["main_topics"].append(topic)
    chapter = chunk.get("possible_chapter")
    if chapter and chapter not in reader_state["chapter_candidates"]:
        reader_state["chapter_candidates"].append(chapter)
