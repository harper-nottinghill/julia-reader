"""Shared fixtures for the julia-reader integration test suite."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from julia_reader.reader_config import ReaderPaths

# ---------------------------------------------------------------------------
# Paths to the bundled demo chronicle
# ---------------------------------------------------------------------------
DEMO_CHRONICLE = Path("demo/nextjs-reader/public/chronicle-dune")


# ---------------------------------------------------------------------------
# Fixtures for happy-path (real demo data)
# ---------------------------------------------------------------------------


@pytest.fixture()
def demo_paths(tmp_path: Path) -> ReaderPaths:
    """Copy the entire demo chronicle into a temp directory and return ReaderPaths."""
    dest = tmp_path / "chronicle-dune"
    shutil.copytree(DEMO_CHRONICLE, dest)

    return ReaderPaths(
        root=dest,
        source=dest / "source",
        state=dest / "state",
        book=dest / "book",
        logs=dest / "logs",
        packet=dest / "packet",
    )


@pytest.fixture()
def demo_sentences(demo_paths: ReaderPaths) -> list[dict]:
    """Load the demo sentence_map.json."""
    return json.loads((demo_paths.state / "sentence_map.json").read_text())


@pytest.fixture()
def demo_chunks(demo_paths: ReaderPaths) -> list[dict]:
    """Load the demo chunk_map.json."""
    return json.loads((demo_paths.state / "chunk_map.json").read_text())


@pytest.fixture()
def demo_state(demo_paths: ReaderPaths) -> dict:
    """Load the demo reader_state.json."""
    return json.loads((demo_paths.state / "reader_state.json").read_text())


# ---------------------------------------------------------------------------
# Fixtures for failure-path (broken / minimal data)
# ---------------------------------------------------------------------------


@pytest.fixture()
def broken_paths(tmp_path: Path) -> ReaderPaths:
    """Create a chronicle tree with minimal/broken files.

    Provides enough structure for the validator to run but triggers
    many validation errors.
    """
    root = tmp_path / "broken-chronicle"
    source = root / "source"
    state = root / "state"
    book = root / "book"
    logs = root / "logs"
    packet_dir = root / "packet"

    for d in (source, state, book, logs, packet_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Source files — empty to trigger "empty" errors
    (source / "raw_input.txt").write_text("")
    (source / "normalized_input.txt").write_text("")
    (source / "break_marked_input.md").write_text("")

    # State files — valid JSON but with problematic content
    (state / "reader_state.json").write_text(json.dumps({
        "run_id": "broken",
        "status": "incomplete",  # not "complete" -> triggers error
    }))
    (state / "sentence_map.json").write_text("not valid json")
    (state / "chunk_map.json").write_text("[]")
    (state / "lake_strings.json").write_text("[]")
    (state / "break_map.json").write_text("{}")
    (state / "reader_packet.json").write_text("{}")
    (state / "subject_index.json").write_text("{}")
    (state / "sentiment_index.json").write_text("{}")
    (state / "live_summary.md").write_text("")
    (state / "book_plan.json").write_text("{invalid")  # broken JSON

    # Book files — only index, missing preface
    (book / "00_index.md").write_text("# Index\n")
    # No 01_preface.md -> missing required file

    # Packet
    (packet_dir / "packet.json").write_text("{}")

    return ReaderPaths(
        root=root,
        source=source,
        state=state,
        book=book,
        logs=logs,
        packet=packet_dir,
    )


@pytest.fixture()
def broken_chunks() -> list[dict]:
    """Chunks with intentionally bad data."""
    return [
        {
            "chunk_id": "C0001",
            "sentence_ids": ["S000001", "S000002"],
            "estimated_tokens": 5000,  # exceeds default max (2000)
            "status": "draft",  # not "assigned" or "summarized"
        },
        {
            "chunk_id": "C0002",
            "sentence_ids": [],  # degenerate — zero sentences
            "estimated_tokens": 100,
            "status": "assigned",
            "break_count": 5,
        },
    ]


@pytest.fixture()
def broken_sentences() -> list[dict]:
    """Sentences referencing non-existent chunks."""
    return [
        {"sentence_id": "S000001", "chunk_id": "C9999"},  # orphan
        {"sentence_id": "S000002", "chunk_id": "C0001"},
    ]


@pytest.fixture()
def broken_state() -> dict:
    """Reader state that is not 'complete'."""
    return {"run_id": "broken", "status": "incomplete"}


# ---------------------------------------------------------------------------
# Fixtures for LLM retry tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_http_request():
    """Patch ``_do_http_request`` inside julia_reader.llm so no real HTTP is made."""
    with patch("julia_reader.llm._do_http_request") as m:
        m.return_value = {
            "choices": [{"message": {"content": "LLM response text"}}],
        }
        yield m
