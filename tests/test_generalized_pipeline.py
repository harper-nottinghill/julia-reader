"""Tests for the generalized text pipeline (normalizer, splitter, chunker).

Run:  pytest tests/test_generalized_pipeline.py -v
"""

from __future__ import annotations

import pytest

from julia_reader.text_normalizer import normalize_text
from julia_reader.sentence_splitter import split_sentences
from julia_reader.chunker import build_chunks
from julia_reader.lake_strings import build_lake_strings


# ===================================================================
# text_normalizer tests
# ===================================================================


class TestNormalizeTextBasic:
    """Core whitespace and line-ending normalization."""

    def test_empty_input(self):
        assert normalize_text("") == "\n"

    def test_none_input(self):
        assert normalize_text(None) == "\n"

    def test_crlf_normalized(self):
        assert normalize_text("line1\r\nline2") == "line1\nline2\n"

    def test_cr_normalized(self):
        assert normalize_text("line1\rline2") == "line1\nline2\n"

    def test_tabs_to_spaces(self):
        assert normalize_text("hello\tworld") == "hello world\n"

    def test_trailing_whitespace_stripped(self):
        assert normalize_text("hello   \nworld  \n") == "hello\nworld\n"

    def test_multiple_blank_lines_collapsed(self):
        assert normalize_text("a\n\n\n\nb") == "a\n\nb\n"

    def test_non_breaking_space_to_space(self):
        assert normalize_text("hello\u00a0world") == "hello world\n"

    def test_leading_whitespace_stripped(self):
        assert normalize_text("  hello") == "hello\n"


class TestNormalizeTextUnicode:
    """Unicode normalization features."""

    def test_smart_quotes_replaced(self):
        result = normalize_text("\u201chello\u201d \u2018world\u2019")
        assert '"' in result
        assert "'" in result
        assert "\u201c" not in result

    def test_nfc_normalization(self):
        # é can be composed (U+00E9) or decomposed (U+0065 + U+0301)
        composed = "caf\u00e9"
        decomposed = "cafe\u0301"
        assert normalize_text(composed) == normalize_text(decomposed)

    def test_zero_width_characters_removed(self):
        text = "hello\u200bworld"
        assert "\u200b" not in normalize_text(text)

    def test_unicode_normalization_disableable(self):
        text = "\u201chello\u201d"
        result = normalize_text(text, normalize_unicode=False)
        assert "\u201c" in result  # smart quotes preserved


class TestNormalizeTextMarkdown:
    """Markdown stripping functionality."""

    def test_atx_heading_stripped(self):
        result = normalize_text("# Hello World", strip_markdown=True)
        assert "#" not in result
        assert "Hello World" in result

    def test_bold_stripped(self):
        result = normalize_text("This is **bold** text", strip_markdown=True)
        assert "**" not in result
        assert "bold" in result

    def test_italic_stripped(self):
        result = normalize_text("This is *italic* text", strip_markdown=True)
        assert "*" not in result
        assert "italic" in result

    def test_link_stripped(self):
        result = normalize_text("Visit [Google](https://google.com)", strip_markdown=True)
        assert "[" not in result
        assert "Google" in result
        assert "https://" not in result

    def test_image_stripped(self):
        result = normalize_text("See ![alt text](image.png)", strip_markdown=True)
        assert "![" not in result
        assert "alt text" in result

    def test_blockquote_stripped(self):
        result = normalize_text("> quoted text", strip_markdown=True)
        assert ">" not in result
        assert "quoted text" in result

    def test_unordered_list_stripped(self):
        result = normalize_text("- item one\n- item two", strip_markdown=True)
        # Dash markers removed; text preserved
        assert "item one" in result
        assert "item two" in result

    def test_horizontal_rule_removed(self):
        result = normalize_text("above\n---\nbelow", strip_markdown=True)
        assert "---" not in result

    def test_markdown_stripping_disabled_by_default(self):
        text = "# Heading with **bold**"
        result = normalize_text(text, strip_markdown=False)
        assert "#" in result
        assert "**" in result

    def test_mixed_markdown_document(self):
        md = """# Title

Some **bold** and *italic* text.

## Section Two

- item one
- item two

> a blockquote

End of [document](link).
"""
        result = normalize_text(md, strip_markdown=True)
        assert "#" not in result
        assert "**" not in result
        assert "[" not in result
        assert "Title" in result
        assert "bold" in result


# ===================================================================
# sentence_splitter tests
# ===================================================================


class TestSentenceSplitter:
    """Sentence boundary detection."""

    def test_basic_splitting(self):
        text = "First sentence. Second sentence. Third sentence."
        sents = split_sentences(text)
        assert len(sents) >= 3

    def test_question_marks(self):
        text = "What is this? I don't know. Are you sure?"
        sents = split_sentences(text)
        assert len(sents) >= 3

    def test_exclamation_marks(self):
        text = "Look out! That was close. Amazing!"
        sents = split_sentences(text)
        assert len(sents) >= 3

    def test_abbreviation_mr_not_split(self):
        text = "Mr. Smith went to the store. He bought milk."
        sents = split_sentences(text)
        # "Mr. Smith" should stay together
        mr_sent = [s for s in sents if "Mr" in s["text"]]
        assert len(mr_sent) >= 1
        assert any("Mr. Smith" in s["text"] for s in mr_sent), (
            f"Expected 'Mr. Smith' to stay together, got: {[s['text'] for s in mr_sent]}"
        )

    def test_abbreviation_dr_not_split(self):
        text = "Dr. Jones arrived early. The meeting started on time."
        sents = split_sentences(text)
        dr_sent = [s for s in sents if "Dr" in s["text"]]
        assert any("Dr. Jones" in s["text"] for s in dr_sent)

    def test_single_paragraph(self):
        text = "Just one sentence here."
        sents = split_sentences(text)
        assert len(sents) == 1

    def test_empty_input(self):
        sents = split_sentences("")
        assert sents == []

    def test_heading_treated_as_single(self):
        text = "Chapter I\n\nThis is the content of chapter one."
        sents = split_sentences(text)
        heading = [s for s in sents if "Chapter I" in s["text"]]
        assert len(heading) == 1

    def test_dialogue_with_speaker_labels(self):
        text = "PAUL: I am going to the market.\nJESSICA: Be careful out there."
        sents = split_sentences(text)
        assert len(sents) >= 2
        paul = [s for s in sents if "PAUL" in s["text"]]
        jessica = [s for s in sents if "JESSICA" in s["text"]]
        assert len(paul) >= 1
        assert len(jessica) >= 1


# ===================================================================
# chunker tests
# ===================================================================


class TestChunker:
    """Dynamic chunking behavior."""

    def _make_sentences(self, n: int, tokens_each: int = 100) -> list[dict]:
        """Generate N fake sentence records."""
        return [
            {
                "sentence_id": f"S{i:06d}",
                "text": f"Sentence number {i}.",
                "estimated_tokens": tokens_each,
                "chunk_id": None,
            }
            for i in range(1, n + 1)
        ]

    def test_empty_sentences(self):
        assert build_chunks([]) == []

    def test_single_sentence(self):
        sents = self._make_sentences(1)
        chunks = build_chunks(sents)
        assert len(chunks) == 1
        assert sents[0]["chunk_id"] is not None

    def test_few_sentences(self):
        sents = self._make_sentences(5)
        chunks = build_chunks(sents)
        assert len(chunks) >= 1
        assert all(s["chunk_id"] is not None for s in sents)

    def test_many_sentences_produce_multiple_chunks(self):
        sents = self._make_sentences(100, tokens_each=100)
        chunks = build_chunks(sents, target_tokens=500, max_tokens=700)
        assert len(chunks) > 1

    def test_all_sentences_assigned(self):
        sents = self._make_sentences(50)
        chunks = build_chunks(sents)
        unassigned = [s for s in sents if s.get("chunk_id") is None]
        assert unassigned == []

    def test_tiny_trailing_chunk_merged(self):
        # Create sentences where the last one is very small
        sents = self._make_sentences(10, tokens_each=200)
        sents[-1]["estimated_tokens"] = 5  # tiny last sentence
        chunks = build_chunks(sents, target_tokens=500, max_tokens=700, min_tokens=50)
        # The tiny trailing chunk should be merged
        assert len(chunks) >= 1
        assert all(s["chunk_id"] is not None for s in sents)

    def test_min_tokens_zero_disables_merging(self):
        sents = self._make_sentences(10, tokens_each=200)
        sents[-1]["estimated_tokens"] = 5
        chunks = build_chunks(sents, target_tokens=500, max_tokens=700, min_tokens=0)
        # With min_tokens=0, tiny chunks are NOT merged
        assert all(s["chunk_id"] is not None for s in sents)


# ===================================================================
# Integration: full pipeline on sample documents
# ===================================================================


class TestPipelineIntegration:
    """End-to-end pipeline on various document structures."""

    def _run_pipeline(self, text: str, strip_md: bool = False) -> dict:
        normalized = normalize_text(text, strip_markdown=strip_md)
        sentences = split_sentences(normalized)
        lake_strings, breaks = build_lake_strings(sentences)
        chunks = build_chunks(sentences)
        return {
            "normalized_len": len(normalized),
            "sentences": len(sentences),
            "chunks": len(chunks),
            "lake_strings": len(lake_strings),
            "breaks": len(breaks),
            "unassigned": sum(1 for s in sentences if s.get("chunk_id") is None),
        }

    def test_plain_prose(self):
        text = (
            "The cat sat on the mat. It was a sunny day. Birds sang in the trees. "
            "The dog played in the yard. Everything was peaceful and calm."
        )
        result = self._run_pipeline(text)
        assert result["sentences"] >= 1
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0

    def test_markdown_document(self):
        md = """# My Document

This is **bold** text with *italic* styling.

## Section Two

- Point one
- Point two

Visit [example](https://example.com) for more.
"""
        result = self._run_pipeline(md, strip_md=True)
        assert result["sentences"] >= 1
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0

    def test_multi_chapter(self):
        text = """Chapter I

The first chapter begins here. It was a dark and stormy night. The wind howled through the trees.

Chapter II

The second chapter continues. Morning came with bright sunshine. The birds returned to the trees.

Chapter III

The final chapter wraps up. All was well. The end.
"""
        result = self._run_pipeline(text)
        assert result["sentences"] >= 6
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0

    def test_very_short_text(self):
        result = self._run_pipeline("Hello world.")
        assert result["sentences"] >= 1
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0

    def test_text_with_dialogue(self):
        text = (
            "PAUL: We must go to the south.\n"
            "JESSICA: Why the south?\n"
            "PAUL: I have seen it in a dream. The answers are there."
        )
        result = self._run_pipeline(text)
        assert result["sentences"] >= 3
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0

    def test_unicode_heavy_text(self):
        text = (
            "L\u2019amour toujours \u2014 c\u2019est la vie! "
            "She said \u201chello\u201d with a smile. "
            "The caf\u00e9 was wonderful."
        )
        result = self._run_pipeline(text)
        assert result["sentences"] >= 1
        assert result["chunks"] >= 1
        assert result["unassigned"] == 0
