"""Input normalization for Reader chronicles.

Handles plain text (.txt), markdown (.md), and mixed-format prose.
Normalizes Unicode, whitespace, and optionally strips markdown syntax.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Smart-quote / ligature mappings  (order matters – longer sequences first)
# ---------------------------------------------------------------------------
_UNICODE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    # Curly / smart quotes → ASCII
    (re.compile("\u201c"), '"'),   # left double
    (re.compile("\u201d"), '"'),   # right double
    (re.compile("\u2018"), "'"),   # left single
    (re.compile("\u2019"), "'"),   # right single
    (re.compile("\u201a"), "'"),   # single low-9
    (re.compile("\u201e"), '"'),   # double low-9
    (re.compile("\u00ab"), '"'),   # left-pointing double angle
    (re.compile("\u00bb"), '"'),   # right-pointing double angle
    # Em/en dash → em-dash literal (preserves semantic meaning)
    (re.compile("\u2013"), "\u2013"),  # en-dash (keep)
    (re.compile("\u2014"), "\u2014"),  # em-dash (keep)
    # Zero-width characters
    (re.compile("[\u200b\u200c\u200d\ufeff]"), ""),
]

# Markdown stripping patterns  (applied per-line, after whitespace normalization)
_MD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Horizontal rules  (must come before heading strip)
    (re.compile(r"^\s{0,3}[-*_]{3,}\s*$"), ""),
    # ATX headings:  # ## ### etc.
    (re.compile(r"^(#{1,6})\s+"), lambda m: ""),
    # Bold/italic markers
    (re.compile(r"\*{1,3}([^*]+?)\*{1,3}"), r"\1"),
    (re.compile(r"_{1,3}([^_]+?)_{1,3}"), r"\1"),
    # Inline code backticks
    (re.compile(r"`([^`]+)`"), r"\1"),
    # Links  [text](url)
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),
    # Images  ![alt](url)
    (re.compile(r"!\[([^\]]*)\]\([^)]+\)"), r"\1"),
    # Blockquote prefix
    (re.compile(r"^\s*>\s?"), ""),
    # Unordered list markers
    (re.compile(r"^\s*[-*+]\s+"), ""),
    # Ordered list markers
    (re.compile(r"^\s*\d+[.)]\s+"), ""),
]


def _apply_unicode_normalization(text: str) -> str:
    """NFC-normalize and replace common problematic Unicode characters."""
    text = unicodedata.normalize("NFC", text)
    for pattern, replacement in _UNICODE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def _strip_markdown_line(line: str) -> str:
    """Strip common markdown syntax from a single line of text."""
    for pattern, replacement in _MD_PATTERNS:
        line = pattern.sub(replacement, line)
    return line.strip()


def normalize_text(
    raw: str,
    *,
    strip_markdown: bool = False,
    normalize_unicode: bool = True,
) -> str:
    """Normalize whitespace while preserving useful structure.

    Parameters
    ----------
    raw:
        Input text (any encoding already decoded to ``str``).
    strip_markdown:
        When *True*, remove markdown syntax (headings, bold/italic, links,
        images, list markers, blockquotes, horizontal rules).  The result
        is clean prose suitable for sentence splitting.
    normalize_unicode:
        When *True* (default), apply NFC normalization, replace smart
        quotes with ASCII equivalents, and strip zero-width characters.
    """
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")

    if normalize_unicode:
        text = _apply_unicode_normalization(text)

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

        if strip_markdown:
            stripped = _strip_markdown_line(stripped)
            if not stripped:
                if not blank_seen:
                    lines.append("")
                blank_seen = True
                continue

        lines.append(stripped)

    return "\n".join(lines).strip() + ("\n" if lines else "")
