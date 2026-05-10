"""Julia Reader harness — progressive Chronicle pipeline."""

from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import logging as _logging

from .book_planner import build_book_plan
from .chunker import build_chunks
from .error_logger import log_error
from .lake_strings import build_lake_strings, build_packet, generate_break_marked_text
from .live_summary import apply_update, summarize_chunk
from .output_scaffold import generate_manifest
from .page_writer import write_book
from .reader_config import PipelineConfig, ReaderPaths, detect_title, estimate_tokens, make_run_paths, safe_slug
from .sentence_splitter import split_sentences
from .text_normalizer import normalize_text
from .validator import validate_reader_run

_READER_CYAN = "\033[38;5;81m"
_READER_BLUE = "\033[38;5;75m"
_READER_PURPLE = "\033[38;5;141m"
_READER_PINK = "\033[38;5;213m"
_READER_GOLD = "\033[38;5;178m"
_READER_GREEN = "\033[38;5;34m"
_READER_RED = "\033[38;5;124m"
_READER_STONE = "\033[38;5;245m"
_READER_DIM = "\033[2m"
_READER_BOLD = "\033[1m"
_READER_RESET = "\033[0m"


def _prompt_dir() -> Path:
    return Path(__file__).resolve().parent / "prompts"


def _json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _log(log_path: Path, msg: str) -> None:
    ts = _dt.datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {ts} — {msg}\n")


def _short(text: Any, limit: int = 96) -> str:
    s = " ".join(str(text or "").split())
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)].rstrip() + "…"


def _reader_live(stage: str, message: str, *, detail: str = "", color: str = _READER_CYAN, live: bool = True) -> None:
    if not live:
        return
    tail = f" {detail}" if detail else ""
    print(
        f"  {color}{_READER_BOLD}{stage}{_READER_RESET} {color}{message}{_READER_RESET}"
        f"{_READER_STONE}{tail}{_READER_RESET}"
    )


def _reader_live_header(*, title: str, folder: Path, model: str, live: bool) -> None:
    if not live:
        return
    print()
    print(f"  {_READER_PINK}{_READER_BOLD}☉ The Reader Chronicle opens its enchanted margins{_READER_RESET}")
    print(f"  {_READER_PINK}  Source title:{_READER_RESET} {_READER_GOLD}{_short(title, 72)}{_READER_RESET}")
    print(f"  {_READER_PINK}  Reader model:{_READER_RESET} {_READER_GOLD}{model or 'default'}{_READER_RESET}")
    print(f"  {_READER_PINK}  Chronicle root:{_READER_RESET} {_READER_GOLD}{folder}{_READER_RESET}")
    print(
        f"  {_READER_PINK}{_READER_DIM}  Watch the quill: archive → sentences → "
        f"lake strings → chunks → book.{_READER_RESET}"
    )
    print()


def _validate_chunk(chunk: dict[str, Any], index: int | None = None) -> str | None:
    """Validate a chunk dict has required keys and non-empty content.

    Returns an error message string if the chunk is malformed, or ``None``
    if the chunk looks valid.
    """
    label = f"Chunk {index}" if index is not None else f"Chunk {chunk.get('chunk_id', '?')}"
    if not isinstance(chunk, dict):
        return f"{label}: expected dict, got {type(chunk).__name__} — skipping."
    chunk_id = chunk.get("chunk_id")
    if not chunk_id:
        return f"{label}: missing chunk_id — skipping."
    sentence_ids = chunk.get("sentence_ids")
    if sentence_ids is None:
        return f"{label} ({chunk_id}): missing sentence_ids — skipping."
    if not isinstance(sentence_ids, list):
        return f"{label} ({chunk_id}): sentence_ids is {type(sentence_ids).__name__}, expected list — skipping."
    if not sentence_ids:
        return f"{label} ({chunk_id}): has empty sentence_ids (no text content) — skipping."
    return None


def _load_state_file(path: Path, description: str = "state file") -> Any:
    """Load a JSON state file with clear errors if missing or malformed.

    Raises ``SystemExit(1)`` so the caller can rely on a valid return.
    """
    if not path.exists():
        msg = (
            f"Required {description} not found: {path}\n"
            f"Expected location: {path.parent}\n"
            f"Run the earlier pipeline stage first to generate this file."
        )
        print(f"[ERROR] {msg}", file=sys.stderr)
        raise SystemExit(1)
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        msg = (
            f"Required {description} is empty (0 bytes of content): {path}\n"
            f"This file was expected to contain JSON data."
        )
        print(f"[ERROR] {msg}", file=sys.stderr)
        raise SystemExit(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = (
            f"Failed to parse JSON in {description} ({path.name}): {exc}\n"
            f"File may be truncated or corrupted."
        )
        print(f"[ERROR] {msg}", file=sys.stderr)
        raise SystemExit(1)


def _chunk_text(chunk: dict[str, Any], sentence_by_id: dict[str, dict[str, Any]]) -> str:
    return "\n".join(str(sentence_by_id[sid]["text"]) for sid in chunk["sentence_ids"] if sid in sentence_by_id)


def _initial_state(run_id: str, raw: str, normalized: str) -> dict[str, Any]:
    title = detect_title(normalized or raw)
    return {
        "run_id": run_id,
        "created_at": _dt.datetime.now().isoformat(),
        "source_title": title,
        "source_slug": safe_slug(title),
        "total_characters": len(raw),
        "total_sentences": 0,
        "total_chunks": 0,
        "total_lake_strings": 0,
        "total_breaks": 0,
        "current_sentence_id": None,
        "current_chunk_id": None,
        "current_understanding": "",
        "main_topics": [],
        "chapter_candidates": [],
        "resolved_chapters": [],
        "status": "initialized",
        "errors": [],
    }


def run_reader(
    *,
    raw_text: str = "",
    base_dir: Path | None = None,
    complete: Callable[[str, str], str] | None = None,
    model_label: str = "local-fallback",
    use_llm: bool = True,
    live: bool = True,
    max_pages_per_chunk: int = 1,
    config: PipelineConfig | None = None,
) -> dict[str, Any] | None:
    """Run the full Reader pipeline. Returns summary metadata or None on empty input.

    Two calling conventions are supported:

    1. **Explicit parameters** (backward compatible): pass ``raw_text`` and
       ``base_dir`` plus the other keyword arguments.
    2. **PipelineConfig object**: pass a single ``config`` — all other keyword
       arguments are ignored in favour of the config's fields.
    """
    if config is not None:
        raw = (config.raw_text or "").strip()
        paths = config.paths
        use_llm = config.use_llm
        live = config.live
        max_pages_per_chunk = config.max_pages_per_chunk
        reader_model = config.model_label
        complete = config.complete
        prompt_dir = config.prompt_dir
    else:
        raw = (raw_text or "").strip()
        if not raw:
            print(
                "[ERROR] pipeline.py:run_reader — Input text is empty (0 characters after stripping whitespace). "
                "Nothing to process.",
                file=sys.stderr,
            )
            return None
        if base_dir is None:
            base_dir = Path(".")
        paths = make_run_paths(base_dir, raw)
        reader_model = model_label
        prompt_dir = _prompt_dir()

    if not raw:
        print(
            "[ERROR] pipeline.py:run_reader — Input text is empty (0 characters after stripping whitespace). "
            "Nothing to process.",
            file=sys.stderr,
        )
        return None

    run_id = paths.root.name
    run_log = paths.logs / "reader_run_log.md"
    errors_log = paths.logs / "errors.log"
    llm_log = paths.logs / "llm_calls.jsonl"
    packet_dir = paths.packet
    packet_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()
    _reader_live_header(title=detect_title(raw), folder=paths.root, model=reader_model, live=live)
    run_log.write_text("# Reader Run Log\n\n", encoding="utf-8")
    errors_log.write_text("", encoding="utf-8")
    llm_log.write_text("", encoding="utf-8")

    # Wire the LLM retry logger to this run's errors.log so every retry
    # attempt is captured alongside other structured error entries.
    _retry_handler = _logging.FileHandler(errors_log, encoding="utf-8")
    _retry_handler.setFormatter(
        _logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    _logging.getLogger("julia_reader.llm_retry").addHandler(_retry_handler)

    _log(run_log, "run started")

    (paths.source / "raw_input.txt").write_text(raw + "\n", encoding="utf-8")
    _log(run_log, "raw input saved")
    _reader_live(
        "✦ Archive Charm",
        "raw source sealed",
        detail=f"{len(raw):,} chars → source/raw_input.txt",
        color=_READER_BLUE,
        live=live,
    )
    normalized = normalize_text(raw)
    (paths.source / "normalized_input.txt").write_text(normalized, encoding="utf-8")
    _log(run_log, "normalization complete")
    _reader_live(
        "✦ Scourgify",
        "whitespace and structure normalized",
        detail="source/normalized_input.txt",
        color=_READER_CYAN,
        live=live,
    )

    state = _initial_state(run_id, raw, normalized)
    _json(paths.state / "reader_state.json", state)
    _reader_live(
        "✦ Pensieve Basin",
        "reader state initialized",
        detail=f"run {run_id}",
        color=_READER_PURPLE,
        live=live,
    )

    state["status"] = "chunking"
    sentences = split_sentences(normalized)
    state["total_sentences"] = len(sentences)
    _json(paths.state / "sentence_map.json", sentences)
    _log(run_log, f"sentence splitting complete ({len(sentences)} sentences)")
    _reader_live(
        "✦ Sentence Scrying",
        "source split into stable sentence runes",
        detail=f"{len(sentences):,} sentences → state/sentence_map.json",
        color=_READER_GOLD,
        live=live,
    )

    lake_strings, breaks = build_lake_strings(sentences)
    state["total_lake_strings"] = len(lake_strings)
    state["total_breaks"] = len(breaks)
    _json(paths.state / "lake_strings.json", lake_strings)
    _json(paths.state / "break_map.json", breaks)
    _log(run_log, f"lake strings generated ({len(lake_strings)} units, {len(breaks)} breaks)")
    _reader_live(
        "✦ Lake Strings",
        "sentence metadata woven",
        detail=f"{len(lake_strings):,} strings, {len(breaks):,} breaks",
        color=_READER_PINK,
        live=live,
    )

    chunks = build_chunks(sentences)
    sentence_chunk = {s["sentence_id"]: s.get("chunk_id") for s in sentences}
    breaks_by_chunk: dict[str, list[dict[str, Any]]] = {}
    for br in breaks:
        cid = sentence_chunk.get(br.get("sentence_id"))
        if cid:
            breaks_by_chunk.setdefault(str(cid), []).append(br)
    for chunk in chunks:
        chunk["breaks"] = breaks_by_chunk.get(chunk["chunk_id"], [])
        chunk["break_count"] = len(chunk["breaks"])
    state["total_chunks"] = len(chunks)
    _json(paths.state / "sentence_map.json", sentences)
    _json(paths.state / "chunk_map.json", chunks)
    _log(run_log, f"chunking complete ({len(chunks)} chunks)")
    largest_chunk = max((int(c.get("estimated_tokens", 0) or 0) for c in chunks), default=0)
    _reader_live(
        "✦ Chunking Ward",
        "safe LLM packets prepared",
        detail=f"{len(chunks):,} chunks, largest {largest_chunk:,}/2000 tokens",
        color=_READER_GREEN,
        live=live,
    )
    (paths.source / "break_marked_input.md").write_text(
        generate_break_marked_text(chunks, lake_strings, breaks),
        encoding="utf-8",
    )
    _reader_live(
        "✦ Break Map",
        "subject shifts inked into reconstructed source",
        detail="source/break_marked_input.md",
        color=_READER_PURPLE,
        live=live,
    )

    sentence_by_id = {s["sentence_id"]: s for s in sentences}
    shift_lines = ["# Subject Shift Log", ""]
    state["status"] = "summarizing"
    skipped_chunk_count = 0
    for idx, chunk in enumerate(chunks):
        # --- Edge case: validate chunk structure before processing ---
        validation_error = _validate_chunk(chunk, index=idx)
        if validation_error:
            log_error(
                error_type="malformed_chunk",
                message=validation_error,
                affected_id=chunk.get("chunk_id", f"index_{idx}"),
                errors_path=errors_log,
            )
            skipped_chunk_count += 1
            _reader_live(
                "⚠ Skipped Chunk",
                validation_error,
                color=_READER_RED,
                live=live,
            )
            continue

        # --- Edge case: check chunk text content is not empty ---
        text = _chunk_text(chunk, sentence_by_id)
        if not text.strip():
            msg = f"Chunk {idx} ({chunk['chunk_id']}) has empty text content after resolving sentences — skipping."
            log_error(
                error_type="empty_chunk_content",
                message=msg,
                affected_id=chunk["chunk_id"],
                errors_path=errors_log,
            )
            skipped_chunk_count += 1
            _reader_live(
                "⚠ Skipped Chunk",
                msg,
                color=_READER_RED,
                live=live,
            )
            continue

        state["current_chunk_id"] = chunk["chunk_id"]
        state["current_sentence_id"] = chunk["end_sentence"]
        _json(paths.state / "reader_state.json", state)
        _reader_live(
            "✦ Reading Rune",
            f"{chunk['chunk_id']} enters the reading circle",
            detail=(
                f"{len(chunk.get('sentence_ids', []))} sentences, "
                f"{chunk.get('estimated_tokens', 0)} tokens, {chunk.get('break_count', 0)} breaks"
            ),
            color=_READER_BLUE,
            live=live,
        )
        _reader_live(
            "✦ Augury",
            "asking the model to update live understanding (silent HTTP — no raw stream)",
            detail=f"model {reader_model}",
            color=_READER_PINK,
            live=live and use_llm and complete is not None,
        )
        try:
            update = summarize_chunk(
                complete=complete,
                model_label=reader_model,
                chunk=chunk,
                chunk_text=text,
                previous_live_summary=state.get("current_understanding", ""),
                reader_state=state,
                prompt_dir=prompt_dir,
                llm_log_path=llm_log,
                errors_path=errors_log,
                use_llm=use_llm,
            )
        except Exception as exc:
            log_error(
                error_type="unexpected_state",
                message=f"Unexpected error summarizing chunk {chunk['chunk_id']}: {exc}",
                affected_id=chunk["chunk_id"],
                details={"skipped_so_far": skipped_chunk_count + 1},
                errors_path=errors_log,
            )
            skipped_chunk_count += 1
            continue
        apply_update(chunk, state, update)
        _reader_live(
            "✦ Marginalia",
            f"{chunk['chunk_id']} understood",
            detail=f"subject: {_short(chunk.get('detected_subject') or chunk.get('possible_chapter') or 'reader notes')}",
            color=_READER_GOLD,
            live=live,
        )
        if chunk.get("subject_shift_reason"):
            shift_lines.append(
                f"- `{chunk['chunk_id']}` {chunk['subject_shift_reason']} — {chunk.get('detected_subject', '')}"
            )
            _reader_live(
                "✦ Topic Turn",
                "subject shift detected",
                detail=_short(chunk.get("subject_shift_reason")),
                color=_READER_PURPLE,
                live=live,
            )
        (paths.state / "live_summary.md").write_text(
            state.get("current_understanding", "") or "(no live summary)\n",
            encoding="utf-8",
        )
        _json(paths.state / "chunk_map.json", chunks)
        _json(paths.state / "reader_state.json", state)
        _log(run_log, f"{chunk['chunk_id']} summarized")

    # Report skipped chunks
    if skipped_chunk_count > 0:
        msg = (
            f"Skipped {skipped_chunk_count} of {len(chunks)} chunks during summarization. "
            "See errors.log for details on each skipped chunk."
        )
        log_error(
            error_type="skipped_chunks_summary",
            message=msg,
            affected_id="pipeline_summary",
            details={"skipped": skipped_chunk_count, "total": len(chunks)},
            errors_path=errors_log,
        )
        _reader_live(
            "⚠ Chunk Summary",
            f"{skipped_chunk_count} chunks skipped",
            detail=f"of {len(chunks)} total — see errors.log",
            color=_READER_RED,
            live=live,
        )

    (paths.state / "subject_shift_log.md").write_text("\n".join(shift_lines).rstrip() + "\n", encoding="utf-8")
    _log(run_log, "live summary updated")
    _reader_live(
        "✦ Living Summary",
        "evolving understanding written",
        detail="state/live_summary.md",
        color=_READER_GREEN,
        live=live,
    )

    state["status"] = "planning_book"
    plan = build_book_plan(chunks)
    state["resolved_chapters"] = [c["title"] for c in plan.get("chapters", [])]
    _json(paths.state / "book_plan.json", plan)
    _log(run_log, "book plan generated")
    _reader_live(
        "✦ Chapter Divination",
        "book plan resolved",
        detail=f"{len(plan.get('chapters', [])):,} chapters → state/book_plan.json",
        color=_READER_PINK,
        live=live,
    )

    state["status"] = "writing_book"
    stats = write_book(
        book_dir=paths.book,
        plan=plan,
        chunks=chunks,
        sentences=sentences,
        reader_state=state,
        state_dir=paths.state,
        max_pages_per_chunk=max_pages_per_chunk,
    )
    _reader_live(
        "✦ Quick-Quotes Quill",
        "Markdown pages written",
        detail=f"{stats['chapters']} chapters, {stats['pages']} pages",
        color=_READER_GOLD,
        live=live,
    )
    assigned_chapters = {
        cid: chapter["chapter_id"]
        for chapter in plan.get("chapters", [])
        for cid in chapter.get("chunk_ids", [])
    }
    for chunk in chunks:
        chunk["status"] = "assigned"
        for sid in chunk["sentence_ids"]:
            if sid in sentence_by_id:
                sentence_by_id[sid]["chapter_id"] = assigned_chapters.get(chunk["chunk_id"])
    _json(paths.state / "sentence_map.json", sentences)
    _json(paths.state / "chunk_map.json", chunks)
    _log(run_log, "pages written")

    packet = build_packet(
        raw_text=raw,
        chunks=chunks,
        lake_strings=lake_strings,
        breaks=breaks,
        model_used=reader_model,
        processing_time_ms=int((time.monotonic() - started_at) * 1000),
    )
    _json(paths.state / "reader_packet.json", packet)
    _json(paths.state / "subject_index.json", packet["subjectMatterIndex"])
    _json(paths.state / "sentiment_index.json", packet["sentimentIndex"])
    packet_meta = dict(packet)
    packet_meta["chunks"] = []
    packet_meta["chunkFiles"] = []
    for chunk in packet["chunks"]:
        filename = f"chunk_{int(chunk['index']):04d}_{str(chunk['id'])[:8]}.json"
        _json(packet_dir / filename, chunk)
        packet_meta["chunkFiles"].append(filename)
    _json(packet_dir / "packet.json", packet_meta)
    _log(run_log, "Harper Reader packet artifacts written")
    _reader_live(
        "✦ Packet Portkey",
        "Reader packet sealed",
        detail="packet/packet.json",
        color=_READER_BLUE,
        live=live,
    )

    state["status"] = "complete"
    state["total_sentences"] = len(sentences)
    state["total_chunks"] = len(chunks)
    _json(paths.state / "reader_state.json", state)
    state["status"] = "validating"
    _json(paths.state / "reader_state.json", state)
    state["status"] = "complete"
    _json(paths.state / "reader_state.json", state)
    errors, warnings = validate_reader_run(paths=paths, sentences=sentences, chunks=chunks, state=state)
    _log(run_log, "validation complete")
    validation_color = _READER_GREEN if not errors else _READER_RED
    _reader_live(
        "✦ Ministry Inspection",
        "validation complete",
        detail=f"{len(errors)} errors, {len(warnings)} warnings",
        color=validation_color,
        live=live,
    )
    # Generate _demo-manifest.json for NextJS ChronicleExplorer discovery
    _chronicle_files = sorted(
        p.relative_to(paths.root).as_posix()
        for p in paths.root.rglob("*")
        if p.is_file() and p.name != "_demo-manifest.json"
    )
    generate_manifest(
        paths.root,
        state.get("source_title", "Reader Run"),
        source_filename=state.get("source_title", ""),
        file_size_bytes=len(raw),
        bundled_reader_model=reader_model,
        chunk_count=len(chunks),
        chapter_count=stats["chapters"],
        page_count=stats["pages"],
        sentence_count=len(sentences),
        files=_chronicle_files,
        processing_status="complete",
    )
    _log(run_log, "_demo-manifest.json generated")
    _reader_live(
        "✦ Chronicle Complete",
        "the book is ready",
        detail="book/00_index.md",
        color=_READER_GREEN,
        live=live,
    )
    return {
        "folder": paths.root,
        "sentences": len(sentences),
        "chunks": len(chunks),
        "lake_strings": len(lake_strings),
        "breaks": len(breaks),
        "chapters": stats["chapters"],
        "pages": stats["pages"],
        "errors": len(errors),
        "warnings": len(warnings),
        "tokens_estimated": estimate_tokens(raw),
        "reader_model": reader_model,
    }
