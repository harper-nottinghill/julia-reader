"""Validation pass for Reader chronicles."""

from __future__ import annotations

import datetime as _dt
import json
import re as _re
from pathlib import Path
from typing import Any

from .error_logger import log_error
from .reader_config import DEFAULT_MAX_CHUNK_TOKENS, DEFAULT_PAGE_MAX_LINES, ReaderPaths


# ---------------------------------------------------------------------------
# State file loading helper
# ---------------------------------------------------------------------------

def _load_json_state(path: Path, description: str) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    """Safely load a JSON state file, returning ``(data, error_message)``.

    If the file is missing or malformed, ``data`` is ``None`` and
    ``error_message`` contains a human-readable description including the
    full expected path and a remediation hint.  If loading succeeds,
    ``error_message`` is ``None``.
    """
    if not path.exists():
        msg = (
            f"Required {description} not found: {path}. "
            f"Expected location: {path.parent}. "
            f"Run the pipeline stage that generates this file first."
        )
        return None, msg
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"Cannot read {description} at {path}: {exc}"
        return None, msg
    if not raw.strip():
        msg = f"{description} is empty (0 bytes of parseable content): {path}"
        return None, msg
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Failed to parse JSON in {description} ({path.name}): {exc}. File may be truncated or corrupted."
        return None, msg
    return data, None


# ---------------------------------------------------------------------------
# Per-stage validation helpers
# ---------------------------------------------------------------------------

def _validate_chunking(
    chunks: list[dict[str, Any]],
    sentences: list[dict[str, Any]],
    max_chunk_tokens: int,
    errors_path: Path,
) -> dict[str, Any]:
    """Validate the chunking stage and return stage result dict."""
    stage_errors: list[str] = []
    stage_warnings: list[str] = []
    chunk_ids = set()
    degenerate_chunks: list[str] = []

    for idx, c in enumerate(chunks):
        # Edge case: chunk is not a dict
        if not isinstance(c, dict):
            msg = f"Chunk at index {idx} is not a dict (got {type(c).__name__}) — skipping validation."
            stage_errors.append(msg)
            log_error(
                error_type="malformed_chunk",
                message=msg,
                affected_id=f"index_{idx}",
                errors_path=errors_path,
            )
            continue
        cid = c.get("chunk_id")
        if not cid:
            stage_errors.append(f"Chunk at index {idx} missing chunk_id")
            continue
        if cid in chunk_ids:
            stage_errors.append(f"Duplicate chunk_id: {cid}")
        chunk_ids.add(cid)

        sids = c.get("sentence_ids", [])
        if not sids:
            degenerate_chunks.append(cid)

        if int(c.get("estimated_tokens", 0)) > max_chunk_tokens:
            msg = f"Chunk exceeds max tokens: {cid}={c.get('estimated_tokens')}"
            stage_errors.append(msg)
            log_error(
                error_type="validation_failure",
                message=msg,
                affected_id=cid,
                details={"estimated_tokens": c.get("estimated_tokens"), "max_allowed": max_chunk_tokens},
                errors_path=errors_path,
            )

        if c.get("status") not in {"assigned", "summarized"}:
            stage_warnings.append(f"Chunk not marked assigned/summarized: {cid}")
        if "break_count" not in c:
            stage_warnings.append(f"Chunk missing break_count: {cid}")

    if degenerate_chunks:
        stage_warnings.append(f"Chunks with zero sentences: {', '.join(degenerate_chunks)}")

    # Verify every sentence references a valid chunk
    for s in sentences:
        if not s.get("chunk_id"):
            msg = f"Sentence missing chunk_id: {s.get('sentence_id')}"
            stage_errors.append(msg)
            log_error(
                error_type="validation_failure",
                message=msg,
                affected_id=s.get("sentence_id"),
                errors_path=errors_path,
            )

    status = "PASS" if not stage_errors else "FAIL"
    return {
        "name": "Chunking",
        "status": status,
        "chunks_processed": len(chunks),
        "errors": stage_errors,
        "warnings": stage_warnings,
        "details": {
            "total_sentences_in_chunks": sum(len(c.get("sentence_ids", [])) for c in chunks),
            "degenerate_chunks": degenerate_chunks,
        },
    }


def _validate_summary(
    chunks: list[dict[str, Any]],
    state: dict[str, Any],
    paths: ReaderPaths,
    errors_path: Path,
) -> dict[str, Any]:
    """Validate the summary / live-summary stage."""
    stage_errors: list[str] = []
    stage_warnings: list[str] = []
    skipped: list[str] = []
    empty_summaries: list[str] = []

    live_summary_path = paths.state / "live_summary.md"
    if not live_summary_path.exists():
        msg = f"Missing live_summary.md. Expected location: {live_summary_path}"
        stage_errors.append(msg)
        log_error(
            error_type="missing_state_file",
            message=msg,
            affected_id="live_summary.md",
            errors_path=errors_path,
        )
    else:
        try:
            content = live_summary_path.read_text(encoding="utf-8", errors="replace").strip()
            if not content or content == "(no live summary)":
                stage_warnings.append("live_summary.md is empty or placeholder")
        except OSError as exc:
            msg = f"Cannot read live_summary.md: {exc}"
            stage_errors.append(msg)
            log_error(
                error_type="state_file_read_error",
                message=msg,
                affected_id="live_summary.md",
                errors_path=errors_path,
            )

    for idx, c in enumerate(chunks):
        # Edge case: chunk is not a proper dict
        if not isinstance(c, dict):
            msg = f"Chunk at index {idx} is not a dict (got {type(c).__name__}) — skipping validation."
            stage_warnings.append(msg)
            continue
        chunk_label = c.get("chunk_id", f"index_{idx}")
        if not c.get("chunk_id"):
            stage_warnings.append(f"Chunk at index {idx} missing chunk_id")
        summary = c.get("summary") or c.get("detected_subject")
        if not summary:
            skipped.append(c.get("chunk_id", "unknown"))
        elif isinstance(summary, str) and len(summary.strip()) < 10:
            empty_summaries.append(c.get("chunk_id", "unknown"))

    if skipped:
        stage_warnings.append(f"Chunks with no summary/subject: {', '.join(skipped)}")
    if empty_summaries:
        stage_warnings.append(f"Chunks with very short summaries: {', '.join(empty_summaries)}")

    status = "PASS" if not stage_errors else "FAIL"
    return {
        "name": "Summary",
        "status": status,
        "summaries_generated": len(chunks) - len(skipped),
        "skipped_items": len(skipped),
        "errors": stage_errors,
        "warnings": stage_warnings,
    }


def _validate_page_writing(
    paths: ReaderPaths,
    plan: dict[str, Any],
    page_max_lines: int,
    errors_path: Path,
) -> dict[str, Any]:
    """Validate the page-writing stage."""
    stage_errors: list[str] = []
    stage_warnings: list[str] = []
    pages_generated = 0
    skipped_pages: list[str] = []

    index_path = paths.book / "00_index.md"
    preface_path = paths.book / "01_preface.md"
    for special in (index_path, preface_path):
        if not special.exists():
            stage_errors.append(f"Missing required file: {special.name}")
        else:
            pages_generated += 1

    chapter_dirs = sorted(
        [p for p in paths.book.iterdir() if p.is_dir()] if paths.book.exists() else []
    )
    planned_chapter_ids = {ch.get("chapter_id") for ch in plan.get("chapters", [])}

    for d in chapter_dirs:
        pages = sorted(d.glob("*.md"))
        if not pages:
            msg = f"Empty chapter folder: {d.name}"
            stage_errors.append(msg)
            log_error(
                error_type="validation_failure",
                message=msg,
                affected_id=str(d.relative_to(paths.root)),
                errors_path=errors_path,
            )
            continue
        for p in pages:
            text = p.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                msg = f"Empty page file: {p.relative_to(paths.root)}"
                stage_errors.append(msg)
                log_error(
                    error_type="validation_failure",
                    message=msg,
                    affected_id=str(p.relative_to(paths.root)),
                    errors_path=errors_path,
                )
                skipped_pages.append(p.name)
                continue
            line_count = text.count("\n") + 1
            if line_count > page_max_lines:
                msg = f"Page exceeds {page_max_lines} lines: {p.relative_to(paths.root)} ({line_count} lines)"
                stage_errors.append(msg)
                log_error(
                    error_type="validation_failure",
                    message=msg,
                    affected_id=str(p.relative_to(paths.root)),
                    details={"line_count": line_count, "max_allowed": page_max_lines},
                    errors_path=errors_path,
                )
            pages_generated += 1

    # Validate index links
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8", errors="replace")
        for rel in _re.findall(r"\]\(([^)]+)\)", text):
            if rel.startswith(("http://", "https://", "#")):
                continue
            target = (paths.book / rel).resolve()
            if not target.exists():
                msg = f"Index link does not resolve: {rel}"
                stage_errors.append(msg)
                log_error(
                    error_type="validation_failure",
                    message=msg,
                    affected_id=rel,
                    errors_path=errors_path,
                )

    status = "PASS" if not stage_errors else "FAIL"
    return {
        "name": "Page Writing",
        "status": status,
        "pages_generated": pages_generated,
        "chapters_generated": len(chapter_dirs),
        "skipped_items": len(skipped_pages),
        "errors": stage_errors,
        "warnings": stage_warnings,
    }


def _validate_subject_shift(
    chunks: list[dict[str, Any]],
    paths: ReaderPaths,
) -> dict[str, Any]:
    """Validate the subject-shift stage."""
    stage_errors: list[str] = []
    stage_warnings: list[str] = []
    shift_entries = 0
    null_shifts: list[str] = []

    shift_log_path = paths.state / "subject_shift_log.md"
    if shift_log_path.exists():
        shift_text = shift_log_path.read_text(encoding="utf-8", errors="replace").strip()
        shift_entries = len([l for l in shift_text.splitlines() if l.strip().startswith("-")])
    else:
        stage_warnings.append("subject_shift_log.md not found")

    for c in chunks:
        reason = c.get("subject_shift_reason")
        if reason is None:
            # Not every chunk has a shift; that's expected for the first chunk
            pass
        elif reason == "":
            pass  # No shift — normal
        else:
            shift_entries += 1

        detected = c.get("detected_subject")
        if detected is None and c.get("chunk_id") != chunks[0].get("chunk_id") if chunks else False:
            null_shifts.append(c.get("chunk_id", "unknown"))

    if null_shifts:
        stage_warnings.append(f"Chunks with null detected_subject: {', '.join(null_shifts)}")

    status = "PASS" if not stage_errors else "FAIL"
    return {
        "name": "Subject Shift",
        "status": status,
        "entries_processed": shift_entries,
        "skipped_items": len(null_shifts),
        "errors": stage_errors,
        "warnings": stage_warnings,
    }


def _validate_data_integrity(
    chunks: list[dict[str, Any]],
    sentences: list[dict[str, Any]],
    paths: ReaderPaths,
    errors_path: Path,
) -> list[dict[str, Any]]:
    """Run data-integrity checks across maps and lake strings."""
    checks: list[dict[str, Any]] = []

    # --- Chunk map consistency ---
    chunk_ids = {c.get("chunk_id") for c in chunks}
    sentence_ids_in_chunks: set[str] = set()
    orphan_sentence_refs: list[str] = []
    for c in chunks:
        for sid in c.get("sentence_ids", []):
            sentence_ids_in_chunks.add(sid)

    # Every sentence's chunk_id should point to an existing chunk
    sentences_missing_chunk: list[str] = []
    for s in sentences:
        if s.get("chunk_id") and s["chunk_id"] not in chunk_ids:
            sentences_missing_chunk.append(f"{s.get('sentence_id')}→{s['chunk_id']}")

    if sentences_missing_chunk:
        checks.append({
            "check": "Chunk map consistency",
            "status": "FAIL",
            "details": f"{len(sentences_missing_chunk)} sentences reference non-existent chunks",
        })
    else:
        checks.append({
            "check": "Chunk map consistency",
            "status": "PASS",
            "details": "All sentence→chunk references valid",
        })

    # --- Sentence map consistency ---
    sentence_ids = set()
    dup_ids: list[str] = []
    sentences_missing_chunk_id: list[str] = []
    for s in sentences:
        sid = s.get("sentence_id")
        if not sid:
            continue
        if sid in sentence_ids:
            dup_ids.append(sid)
        sentence_ids.add(sid)
        if not s.get("chunk_id"):
            sentences_missing_chunk_id.append(sid)

    detail_parts = []
    if dup_ids:
        detail_parts.append(f"{len(dup_ids)} duplicate IDs: {', '.join(dup_ids[:5])}")
    if sentences_missing_chunk_id:
        detail_parts.append(f"{len(sentences_missing_chunk_id)} missing chunk_id")
    if not detail_parts:
        detail_parts.append("All sentences valid and unique")

    checks.append({
        "check": "Sentence map consistency",
        "status": "FAIL" if (dup_ids or sentences_missing_chunk_id) else "PASS",
        "details": "; ".join(detail_parts),
    })

    # --- Lake strings consistency ---
    lake_path = paths.state / "lake_strings.json"
    lake_data, lake_error = _load_json_state(lake_path, "lake_strings.json")
    if lake_error:
        checks.append({
            "check": "Lake strings consistency",
            "status": "FAIL",
            "details": lake_error,
        })
        log_error(
            error_type="missing_or_malformed_state_file",
            message=lake_error,
            affected_id="lake_strings.json",
            errors_path=errors_path,
        )
    elif not isinstance(lake_data, list):
        checks.append({
            "check": "Lake strings consistency",
            "status": "FAIL",
            "details": f"Expected list, got {type(lake_data).__name__}",
        })
    else:
        missing_keys: list[str] = []
        empty_content: list[str] = []
        dup_keys: set[str] = set()
        seen_ids: set[str] = set()
        for ls in lake_data:
            ls_id = ls.get("id", "")
            if ls_id in seen_ids:
                dup_keys.add(ls_id)
            seen_ids.add(ls_id)
            if not ls.get("sentence_id"):
                missing_keys.append(ls_id or "(no-id)")
            orig = ls.get("originalSentence", "")
            if isinstance(orig, str) and not orig.strip():
                empty_content.append(ls_id or "(no-id)")

        lake_detail_parts = []
        if dup_keys:
            lake_detail_parts.append(f"{len(dup_keys)} duplicate IDs")
        if missing_keys:
            lake_detail_parts.append(f"{len(missing_keys)} missing sentence_id refs")
        if empty_content:
            lake_detail_parts.append(f"{len(empty_content)} empty content entries")
        if not lake_detail_parts:
            lake_detail_parts.append("All entries valid")

        checks.append({
            "check": "Lake strings consistency",
            "status": "FAIL" if lake_detail_parts != ["All entries valid"] else "PASS",
            "details": f"{len(lake_data)} entries — {'; '.join(lake_detail_parts)}",
        })

    return checks


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _build_report(
    stage_results: list[dict[str, Any]],
    integrity_checks: list[dict[str, Any]],
    all_errors: list[str],
    all_warnings: list[str],
) -> str:
    """Render the full validation_report.md as a string."""
    lines: list[str] = []
    overall_fail = any(s["status"] == "FAIL" for s in stage_results) or any(
        c["status"] == "FAIL" for c in integrity_checks
    )
    overall = "FAIL" if overall_fail else "PASS"

    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"Generated: {_dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"## Overall Status: {overall}")
    lines.append("")

    # Per-stage sections
    for s in stage_results:
        lines.append("---")
        lines.append("")
        lines.append(f"## {s['name']}")
        lines.append(f"- Status: {s['status']}")
        if "chunks_processed" in s:
            lines.append(f"- Chunks processed: {s['chunks_processed']}")
        if "summaries_generated" in s:
            lines.append(f"- Summaries generated: {s['summaries_generated']}")
        if "pages_generated" in s:
            lines.append(f"- Pages generated: {s['pages_generated']}")
        if "chapters_generated" in s:
            lines.append(f"- Chapters generated: {s['chapters_generated']}")
        if "entries_processed" in s:
            lines.append(f"- Entries processed: {s['entries_processed']}")
        if s.get("skipped_items"):
            lines.append(f"- Skipped items: {s['skipped_items']}")
        if s.get("details"):
            for k, v in s["details"].items():
                if v and not (isinstance(v, list) and not v):
                    lines.append(f"- {k}: {v}")
        warn_list = s.get("warnings", [])
        lines.append(f"- Warnings: {', '.join(warn_list) if warn_list else 'None'}")
        if s.get("errors"):
            lines.append("")
            lines.append("  **Errors:**")
            for e in s["errors"]:
                lines.append(f"  - {e}")
        lines.append("")

    # Data integrity section
    lines.append("---")
    lines.append("")
    lines.append("## Data Integrity")
    lines.append("")
    lines.append("| Check | Status | Details |")
    lines.append("|---|---|---|")
    for c in integrity_checks:
        lines.append(f"| {c['check']} | {c['status']} | {c['details']} |")
    lines.append("")

    # Flat error/warning summary for quick scanning
    if all_errors:
        lines.append("---")
        lines.append("")
        lines.append("## All Errors")
        lines.append("")
        for e in all_errors:
            lines.append(f"- {e}")
        lines.append("")
    if all_warnings:
        lines.append("---")
        lines.append("")
        lines.append("## All Warnings")
        lines.append("")
        for w in all_warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Main entry point (preserves original signature and return type)
# ---------------------------------------------------------------------------

def validate_reader_run(
    *,
    paths: ReaderPaths,
    sentences: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    state: dict[str, Any],
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    page_max_lines: int = DEFAULT_PAGE_MAX_LINES,
) -> tuple[list[str], list[str]]:
    """Run all validation checks and write a comprehensive validation_report.md."""
    errors: list[str] = []
    warnings: list[str] = []
    report_path = paths.logs / "validation_report.md"
    report_path.touch(exist_ok=True)
    errors_path = paths.logs / "errors.log"

    # --- Check required files ---
    required = [
        paths.source / "raw_input.txt",
        paths.source / "normalized_input.txt",
        paths.source / "break_marked_input.md",
        paths.state / "reader_state.json",
        paths.state / "sentence_map.json",
        paths.state / "chunk_map.json",
        paths.state / "lake_strings.json",
        paths.state / "break_map.json",
        paths.state / "reader_packet.json",
        paths.state / "subject_index.json",
        paths.state / "sentiment_index.json",
        paths.state / "live_summary.md",
        paths.book / "00_index.md",
        paths.book / "01_preface.md",
        paths.packet / "packet.json",
    ]
    for p in required:
        if not p.exists():
            msg = (
                f"Missing required file: {p.relative_to(paths.root)}. "
                f"Expected location: {p}. "
                f"Run the pipeline stage that generates this file first."
            )
            errors.append(msg)
            log_error(
                error_type="missing_state_file",
                message=msg,
                affected_id=str(p.relative_to(paths.root)),
                errors_path=errors_path,
            )
        elif p.stat().st_size == 0:
            msg = f"Required file is empty (0 bytes): {p.relative_to(paths.root)}. Expected at: {p}"
            errors.append(msg)
            log_error(
                error_type="empty_state_file",
                message=msg,
                affected_id=str(p.relative_to(paths.root)),
                errors_path=errors_path,
            )

    # --- Check reader_state status ---
    if state.get("status") != "complete":
        msg = f"reader_state status is not complete: {state.get('status')}"
        errors.append(msg)
        log_error(
            error_type="validation_failure",
            message=msg,
            affected_id="reader_state",
            errors_path=errors_path,
        )

    # --- Load book plan ---
    plan_path = paths.state / "book_plan.json"
    plan, plan_error = _load_json_state(plan_path, "book_plan.json")
    if plan_error:
        errors.append(plan_error)
        log_error(
            error_type="missing_or_malformed_state_file",
            message=plan_error,
            affected_id="book_plan.json",
            errors_path=errors_path,
        )
        plan = {}
    elif not isinstance(plan, dict):
        msg = f"book_plan.json expected to be a JSON object, got {type(plan).__name__}"
        errors.append(msg)
        log_error(
            error_type="malformed_state_file",
            message=msg,
            affected_id="book_plan.json",
            errors_path=errors_path,
        )
        plan = {}

    # --- Check chunk assignments to pages ---
    assigned = {
        cid
        for ch in plan.get("chapters", [])
        for page in ch.get("page_plan", [])
        for cid in page.get("chunk_ids", [])
    }
    for c in chunks:
        if c.get("chunk_id") not in assigned:
            msg = f"Chunk not assigned to a page: {c.get('chunk_id')}"
            errors.append(msg)
            log_error(
                error_type="validation_failure",
                message=msg,
                affected_id=c.get("chunk_id"),
                errors_path=errors_path,
            )

    # -----------------------------------------------------------------------
    # Per-stage validation
    # -----------------------------------------------------------------------
    chunking_result = _validate_chunking(chunks, sentences, max_chunk_tokens, errors_path)
    summary_result = _validate_summary(chunks, state, paths, errors_path)
    page_result = _validate_page_writing(paths, plan, page_max_lines, errors_path)
    shift_result = _validate_subject_shift(chunks, paths)
    integrity_checks = _validate_data_integrity(chunks, sentences, paths, errors_path)

    stage_results = [chunking_result, summary_result, page_result, shift_result]

    # Collect all errors and warnings from stages into the flat lists
    for s in stage_results:
        errors.extend(s.get("errors", []))
        warnings.extend(s.get("warnings", []))

    # -----------------------------------------------------------------------
    # Build and write the report
    # -----------------------------------------------------------------------
    report_text = _build_report(stage_results, integrity_checks, errors, warnings)
    report_path.write_text(report_text, encoding="utf-8")
    return errors, warnings
