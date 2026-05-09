"""Lightweight subject-shift detection for Reader chunks."""

from __future__ import annotations

import re

_SHIFT_PHRASES = (
    "moving on",
    "another thing",
    "different topic",
    "now let's talk about",
    "now let us talk about",
    "next,",
    "next ",
    "separately",
    "on another note",
)

_STOP = {
    "the", "and", "for", "that", "this", "with", "from", "have", "will",
    "your", "about", "there", "their", "into", "then", "than", "also",
    "just", "like", "because", "should", "would", "could", "when", "where",
}


def is_heading(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("#") or (len(t) <= 90 and not t.endswith((".", "?", "!", ",")) and bool(re.search(r"[A-Za-z]", t)))


def speaker_label(text: str) -> str | None:
    m = re.match(r"^([A-Za-z][A-Za-z0-9 _.-]{0,40}):\s+", text or "")
    return m.group(1).strip().lower() if m else None


def keywords(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", (text or "").lower())
        if w not in _STOP
    }


def subject_shift_reason(sentence: dict, current_sentences: list[dict]) -> str:
    """Return reason string if this sentence should start a new chunk."""
    text = str(sentence.get("text", ""))
    low = text.lower()
    if is_heading(text):
        return "heading indicates a new section"
    if any(p in low for p in _SHIFT_PHRASES):
        return "transition phrase indicates subject shift"
    if current_sentences:
        prev_speaker = speaker_label(str(current_sentences[-1].get("text", "")))
        cur_speaker = speaker_label(text)
        if prev_speaker and cur_speaker and prev_speaker != cur_speaker:
            return f"speaker changed from {prev_speaker} to {cur_speaker}"
        if len(current_sentences) >= 3:
            prev_words = keywords(" ".join(str(s.get("text", "")) for s in current_sentences[-3:]))
            cur_words = keywords(text)
            if len(prev_words) >= 6 and len(cur_words) >= 6:
                overlap = len(prev_words & cur_words) / max(1, len(prev_words | cur_words))
                if overlap < 0.06:
                    return "keyword/topic overlap dropped"
    return ""
