"""Input normalization for Reader chronicles."""

from __future__ import annotations

import re


def normalize_text(raw: str) -> str:
    """Normalize whitespace while preserving useful structure."""
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    lines: list[str] = []
    blank_seen = False
    for line in text.split("\n"):
        stripped = re.sub(r"[ \u00a0]+", " ", line).strip()
        if not stripped:
            if not blank_seen:
                lines.append("")
            blank_seen = True
            continue
        blank_seen = False
        lines.append(stripped)
    return "\n".join(lines).strip() + ("\n" if lines else "")
