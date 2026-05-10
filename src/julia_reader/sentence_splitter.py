"""Practical sentence stream generation for Reader."""

from __future__ import annotations

import re
from typing import Any

from .reader_config import estimate_tokens

# ---------------------------------------------------------------------------
# Sentence-boundary detection
# ---------------------------------------------------------------------------

# Common abbreviations that should NOT trigger a sentence break.
_ABBREVIATIONS = frozenset({
    # Titles / honorifics
    "mr", "mrs", "ms", "miss", "dr", "prof", "rev", "hon", "jr", "sr",
    "sgt", "capt", "lt", "col", "gen", "admiral", "gov", "pres",
    # Academic / professional
    "inc", "ltd", "corp", "co", "dept", "div", "assn", "est",
    # Misc
    "vs", "etc", "approx", "appt", "apt", "dept", "dpt", "est",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
    "oct", "nov", "dec", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    # Common Latin abbreviations
    "i.e", "e.g", "a.m", "p.m", "al", "cf", "nb",
})

# Regex that matches a trailing abbreviation word (e.g. "Mr." or "U.S.")
# followed by a period at the end of a token.
_ABBREV_PERIOD = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in sorted(_ABBREVIATIONS, key=len, reverse=True)) + r")\.$",
    re.IGNORECASE,
)

# Ellipsis patterns
_ELLIPSIS = re.compile(r"\.{3,}|…+")

# Main sentence-boundary regex — looks for .!? followed by whitespace
# and then a capital letter, digit, quote, or list marker.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[]|[-*]\s)")

_SPEAKER = re.compile(r"^[A-Za-z][A-Za-z0-9 _.-]{0,40}:\s+")


def _is_abbreviation_boundary(before: str, after: str) -> bool:
    """Return True if the period in *before* is part of an abbreviation."""
    # Check if the token ending with the period is a known abbreviation
    if _ABBREV_PERIOD.search(before):
        return True
    # Single-letter initials (e.g. "U. S.", "J. R. R.")
    if re.search(r"\b[A-Z]\.$", before):
        return True
    return False


def _split_sentences_in_text(text: str) -> list[str]:
    """Split a line of prose into sentences, respecting abbreviations and ellipses."""
    # First do a naive split on sentence boundaries
    raw_splits = _SENTENCE_BOUNDARY.split(text)
    if len(raw_splits) <= 1:
        return [text.strip()] if text.strip() else []

    # Re-join splits that were incorrectly broken at abbreviations
    sentences: list[str] = []
    current = raw_splits[0]
    for i in range(1, len(raw_splits)):
        # Check if current ends with an abbreviation period
        before = current.rstrip()
        after = raw_splits[i].lstrip()
        if before.endswith(".") and _is_abbreviation_boundary(before, after):
            current = current + " " + raw_splits[i]
        else:
            if current.strip():
                sentences.append(current.strip())
            current = raw_splits[i]
    if current.strip():
        sentences.append(current.strip())
    return sentences


def _is_heading(line: str) -> bool:
    if line.startswith("#"):
        return True
    if len(line) <= 90 and not line.endswith((".", "?", "!", ",")):
        return bool(re.search(r"[A-Za-z]", line))
    return False


def _split_long_span(span: str, max_chars: int = 7600) -> list[str]:
    if len(span) <= max_chars:
        return [span]
    parts: list[str] = []
    cur = span
    while len(cur) > max_chars:
        cut = cur.rfind(" ", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        parts.append(cur[:cut].strip())
        cur = cur[cut:].strip()
    if cur:
        parts.append(cur)
    return parts


def split_sentences(normalized: str) -> list[dict[str, Any]]:
    """Split normalized text into stable sentence records."""
    out: list[dict[str, Any]] = []
    offset = 0
    sentence_n = 1
    paragraphs = normalized.split("\n\n") if normalized else []
    for para_idx, para in enumerate(paragraphs):
        lines = para.splitlines()
        for line in lines:
            text = line.strip()
            if not text:
                offset += len(line) + 1
                continue
            line_start = normalized.find(text, offset)
            if line_start < 0:
                line_start = offset
            spans: list[str]
            if _is_heading(text) or text.startswith(("- ", "* ")) or re.match(r"^\d+[.)]\s+", text):
                spans = [text]
            elif _SPEAKER.match(text):
                speaker, _, rest = text.partition(":")
                rest_parts = [p.strip() for p in _split_sentences_in_text(rest.strip()) if p.strip()]
                spans = [f"{speaker}: {p}" for p in rest_parts] or [text]
            else:
                spans = _split_sentences_in_text(text)
            for span in spans:
                for safe in _split_long_span(span):
                    start = normalized.find(safe, line_start)
                    if start < 0:
                        start = line_start
                    end = start + len(safe)
                    out.append(
                        {
                            "sentence_id": f"S{sentence_n:06d}",
                            "text": safe,
                            "paragraph_index": para_idx,
                            "char_start": start,
                            "char_end": end,
                            "estimated_tokens": estimate_tokens(safe),
                            "chunk_id": None,
                            "chapter_id": None,
                            "subject_tags": [],
                            "importance_score": None,
                        }
                    )
                    sentence_n += 1
            offset = line_start + len(text) + 1
        offset += 1
    return out
