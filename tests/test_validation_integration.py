"""Integration tests exercising the validation flow end-to-end.

Three groups:
  - TestHappyPath  — validator against the bundled Dune demo chronicle
  - TestFailurePath — validator against intentionally broken fixtures
  - TestRetryBehavior — LLM retry logic under simulated transient failures

Run:  pytest tests/test_validation_integration.py -v
"""

from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from julia_reader.llm import chat_completion
from julia_reader.reader_config import ReaderPaths
from julia_reader.validator import validate_reader_run


# ===================================================================
# Happy-path tests
# ===================================================================


class TestHappyPath:
    """Validate against the real bundled Dune demo chronicle."""

    def test_validation_report_created_and_nonempty(
        self,
        demo_paths: ReaderPaths,
        demo_sentences: list[dict],
        demo_chunks: list[dict],
        demo_state: dict,
    ):
        """validation_report.md is produced and is non-empty."""
        errors, warnings = validate_reader_run(
            paths=demo_paths,
            sentences=demo_sentences,
            chunks=demo_chunks,
            state=demo_state,
        )

        report_path = demo_paths.logs / "validation_report.md"
        assert report_path.exists(), "validation_report.md was not created"
        content = report_path.read_text()
        assert len(content.strip()) > 0, "validation_report.md is empty"

    def test_validation_report_has_overall_status_pass(
        self,
        demo_paths: ReaderPaths,
        demo_sentences: list[dict],
        demo_chunks: list[dict],
        demo_state: dict,
    ):
        """The demo data should produce a PASS overall status."""
        validate_reader_run(
            paths=demo_paths,
            sentences=demo_sentences,
            chunks=demo_chunks,
            state=demo_state,
        )

        content = (demo_paths.logs / "validation_report.md").read_text()
        assert "## Overall Status: PASS" in content, (
            f"Expected 'PASS' in report header.\n{content[:500]}"
        )

    def test_happy_path_returns_no_errors(
        self,
        demo_paths: ReaderPaths,
        demo_sentences: list[dict],
        demo_chunks: list[dict],
        demo_state: dict,
    ):
        """Validator returns empty error list for valid demo data."""
        errors, warnings = validate_reader_run(
            paths=demo_paths,
            sentences=demo_sentences,
            chunks=demo_chunks,
            state=demo_state,
        )
        assert errors == [], f"Unexpected errors: {errors[:5]}"

    def test_report_contains_stage_sections(
        self,
        demo_paths: ReaderPaths,
        demo_sentences: list[dict],
        demo_chunks: list[dict],
        demo_state: dict,
    ):
        """Report contains the expected per-stage sections."""
        validate_reader_run(
            paths=demo_paths,
            sentences=demo_sentences,
            chunks=demo_chunks,
            state=demo_state,
        )

        content = (demo_paths.logs / "validation_report.md").read_text()
        for section in ["## Chunking", "## Summary", "## Page Writing", "## Subject Shift"]:
            assert section in content, f"Missing section '{section}' in report"


# ===================================================================
# Failure-path tests
# ===================================================================


class TestFailurePath:
    """Validate against intentionally broken fixtures."""

    def test_errors_log_created_on_failure(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """errors.log is created and contains entries when given bad input."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        errors_path = broken_paths.logs / "errors.log"
        assert errors_path.exists(), "errors.log was not created"
        content = errors_path.read_text().strip()
        assert len(content) > 0, "errors.log is empty despite broken input"

    def test_errors_log_contains_json_lines(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """Each line in errors.log is valid JSON with error_type and message."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        errors_path = broken_paths.logs / "errors.log"
        lines = errors_path.read_text().strip().splitlines()
        assert len(lines) > 0, "No error lines written"

        for line in lines:
            entry = json.loads(line)
            assert "error_type" in entry, f"Missing error_type: {line[:100]}"
            assert "message" in entry, f"Missing message: {line[:100]}"

    def test_missing_files_logged_to_errors(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """Missing required files produce error entries in errors.log."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        errors_path = broken_paths.logs / "errors.log"
        content = errors_path.read_text().lower()
        assert "missing" in content, (
            "Expected 'missing' keyword in errors.log for absent required files"
        )

    def test_incomplete_state_logged(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """reader_state status != 'complete' is logged."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        errors_path = broken_paths.logs / "errors.log"
        content = errors_path.read_text().lower()
        assert "not complete" in content, (
            "Expected validation error about incomplete state status"
        )

    def test_oversized_chunk_logged(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """Chunk exceeding max tokens produces an error entry."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
            max_chunk_tokens=2000,
        )

        errors_path = broken_paths.logs / "errors.log"
        content = errors_path.read_text().lower()
        assert "exceeds max tokens" in content, (
            "Expected error about oversized chunk"
        )

    def test_failure_report_has_fail_status(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """validation_report.md shows FAIL status on broken data."""
        validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        content = (broken_paths.logs / "validation_report.md").read_text()
        assert "## Overall Status: FAIL" in content, (
            f"Expected FAIL status in report.\n{content[:500]}"
        )

    def test_errors_log_has_entries_and_errors_returned(
        self,
        broken_paths: ReaderPaths,
        broken_chunks: list[dict],
        broken_sentences: list[dict],
        broken_state: dict,
    ):
        """Both errors.log and returned error list have entries for broken data."""
        errors, warnings = validate_reader_run(
            paths=broken_paths,
            sentences=broken_sentences,
            chunks=broken_chunks,
            state=broken_state,
        )

        assert len(errors) > 0, "Validator should return errors for broken input"

        errors_path = broken_paths.logs / "errors.log"
        log_lines = [
            l for l in errors_path.read_text().strip().splitlines() if l.strip()
        ]
        assert len(log_lines) > 0, "errors.log should have entries for broken input"


# ===================================================================
# Retry-behavior tests
# ===================================================================


class TestRetryBehavior:
    """Test LLM retry logic via chat_completion with mocked HTTP."""

    def test_retry_on_transient_429(self, mock_http_request: MagicMock):
        """chat_completion retries on HTTP 429 and eventually succeeds."""
        # Simulate two transient 429 errors, then success on the 3rd call
        transient_exc = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )

        mock_http_request.side_effect = [
            transient_exc,
            transient_exc,
            {"choices": [{"message": {"content": "Success after retry"}}]},
        ]

        result = chat_completion(
            system="You are a test.",
            user="Hello",
            api_key="test-key",
            _max_retries=3,
            _base_delay=0,  # no delay in tests
        )

        assert result == "Success after retry"
        assert mock_http_request.call_count == 3

    def test_retry_on_connection_error(self, mock_http_request: MagicMock):
        """chat_completion retries on ConnectionError and succeeds."""
        mock_http_request.side_effect = [
            ConnectionError("Connection reset"),
            {"choices": [{"message": {"content": "Recovered"}}]},
        ]

        result = chat_completion(
            system="sys",
            user="usr",
            api_key="test-key",
            _max_retries=3,
            _base_delay=0,
        )

        assert result == "Recovered"
        assert mock_http_request.call_count == 2

    def test_retry_on_timeout(self, mock_http_request: MagicMock):
        """chat_completion retries on socket.timeout."""
        mock_http_request.side_effect = [
            socket.timeout("Timed out"),
            {"choices": [{"message": {"content": "After timeout"}}]},
        ]

        result = chat_completion(
            system="sys",
            user="usr",
            api_key="test-key",
            _max_retries=2,
            _base_delay=0,
        )

        assert result == "After timeout"
        assert mock_http_request.call_count == 2

    def test_no_retry_on_400(self, mock_http_request: MagicMock):
        """Non-retryable HTTP 400 raises immediately without retry."""
        mock_http_request.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=None,
        )

        with pytest.raises(RuntimeError, match="LLM HTTP 400"):
            chat_completion(
                system="sys",
                user="usr",
                api_key="test-key",
                _max_retries=3,
                _base_delay=0,
            )

        # Should have been called exactly once — no retries
        assert mock_http_request.call_count == 1

    def test_exhausted_retries_raises(self, mock_http_request: MagicMock):
        """When all retries are exhausted, RuntimeError is raised."""
        transient_exc = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )
        mock_http_request.side_effect = transient_exc

        with pytest.raises(RuntimeError, match="retried"):
            chat_completion(
                system="sys",
                user="usr",
                api_key="test-key",
                _max_retries=2,
                _base_delay=0,
            )

        # max_retries=2 → initial + 2 retries = 3 total attempts
        assert mock_http_request.call_count == 3
