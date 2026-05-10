"""Structured JSON error logging for the Julia Reader pipeline.

Each entry is a single JSON line written to *errors.log* containing:
  timestamp, error_type, message, affected_id, stack_trace_summary.
"""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def log_error(
    *,
    error_type: str,
    message: str,
    affected_id: str | None = None,
    details: dict[str, Any] | None = None,
    errors_path: Path,
) -> None:
    """Append one timestamped JSON entry to *errors_path*.

    Parameters
    ----------
    error_type:
        Category — e.g. ``"validation_failure"``, ``"llm_error"``,
        ``"unexpected_state"``.
    message:
        Human-readable summary of what went wrong.
    affected_id:
        Chunk ID, page ID, or other identifier for the failing unit.
    details:
        Optional extra context dict (e.g. ``stack_trace_summary``).
    errors_path:
        Path to the ``errors.log`` file.
    """
    # Build a condensed stack-trace summary: file:line func -> ExcType: msg
    exc_info = traceback.format_exc()
    stack_summary = ""
    if exc_info and exc_info.strip() != "NoneType: None":
        lines = exc_info.strip().splitlines()
        # Take last meaningful frame line and the exception line
        frame_lines = [l for l in lines if l.strip().startswith("File ")]
        exc_line = lines[-1] if lines else ""
        if frame_lines:
            stack_summary = frame_lines[-1].strip() + " -> " + exc_line.strip()
        else:
            stack_summary = exc_line

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_type": error_type,
        "message": message,
        "affected_id": affected_id,
        "stack_trace_summary": stack_summary or None,
    }
    if details:
        entry["details"] = details

    with errors_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
