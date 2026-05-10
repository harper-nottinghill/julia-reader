"""Terminal entry — Julia Reader harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from . import theme
from .llm import make_completer_for
from .output_scaffold import scaffold_book, slugify
from .pipeline import run_reader


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in __import__("os").environ:
            __import__("os").environ[key] = val


def _read_input(args: argparse.Namespace) -> str:
    # --input takes priority, then -f/--file, then stdin
    input_path = getattr(args, "input", None) or args.file
    if input_path:
        p = Path(input_path)
        if not p.exists():
            print(
                f"  {theme.CRIMSON}Error: input file not found: {p}{theme.RESET}\n",
                file=sys.stderr,
            )
            sys.exit(1)
        if not p.is_file():
            print(
                f"  {theme.CRIMSON}Error: input path is not a file: {p}{theme.RESET}\n",
                file=sys.stderr,
            )
            sys.exit(1)
        return p.read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print(
        f"  {theme.PARCHMENT}No input file provided and stdin is a TTY.{theme.RESET}\n"
        f"  {theme.STONE}Usage:{theme.RESET} {theme.GOLD}julia-reader --input path/to/doc.txt{theme.RESET}\n"
        f"  {theme.STONE}Pipe text in:{theme.RESET} {theme.GOLD}cat doc.txt | julia-reader{theme.RESET}\n"
        f"  {theme.STONE}Or:{theme.RESET} {theme.GOLD}julia-reader -f path/to.txt{theme.RESET}\n"
        f"\n  {theme.STONE}Run{theme.RESET} {theme.GOLD}julia-reader --help{theme.RESET} {theme.STONE}for all options.{theme.RESET}\n",
        flush=True,
    )
    sys.exit(2)


def main() -> None:
    p = argparse.ArgumentParser(
        prog="julia-reader",
        description="Julia Reader — progressive Reader Chronicle harness (OpenAI-compatible API).\n"
                    "\n"
                    "Processes a text or markdown file into a structured Chronicle with chapters,\n"
                    "pages, and metadata. Output is written to <output>/_reader/<timestamp>_<slug>/.",
        epilog=(
            "examples:\n"
            "  julia-reader --input doc.txt --output ./output\n"
            "  julia-reader --input novel.md --output ./chronicle --no-llm\n"
            "  cat doc.txt | julia-reader -o ./out --quiet\n"
            "  julia-reader -f doc.txt -o ./out\n"
            "  julia-reader output-scaffold \"My Book\" -o ./output\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = p.add_subparsers(dest="command")

    # --- output-scaffold subcommand ---
    scaffold_p = sub.add_parser(
        "output-scaffold",
        help="Scaffold a Chronicle output directory for a given book name (no processing).",
        description="Create the full output directory tree (source/, state/, book/, packet/, logs/) "
                    "with a _demo-manifest.json for a given book name.",
    )
    scaffold_p.add_argument("book_name", help='Human-readable book name, e.g. "My Test Book"')
    scaffold_p.add_argument(
        "-o", "--output", "--out", metavar="DIR", default=".",
        help="Base output directory (default: current directory)",
    )
    scaffold_p.add_argument(
        "--source-filename", default="", help="Original source filename (stored in manifest)"
    )
    scaffold_p.add_argument(
        "--exist-ok", action="store_true",
        help="Do not error if the chronicle directory already exists",
    )

    # --- main run arguments ---
    p.add_argument("-i", "--input", metavar="FILE",
                   help="Source text or markdown file to process (.txt or .md)")
    p.add_argument("-f", "--file", metavar="FILE",
                   help="Alias for --input (source text file)")
    p.add_argument("-o", "--output", "--out", metavar="DIR", default=".",
                   help="Output directory for _reader/ chronicle tree (default: current directory)")
    p.add_argument("-m", "--model", help="Override JULIA_READER_MODEL for this run")
    p.add_argument("--base-url", help="Override JULIA_READER_BASE_URL")
    p.add_argument("--no-llm", action="store_true", help="No HTTP calls; heuristic / local fallback summaries only")
    p.add_argument("--quiet", action="store_true", help="Suppress colored progress lines (still runs full pipeline)")
    p.add_argument("--max-pages-per-chunk", type=int, default=1, help="Max pages generated per chunk (default: 1; set >1 to enable multi-page generation)")
    p.add_argument("--book-name", help="Override the book name used for directory naming and manifest (default: derived from input)")
    p.add_argument("--env-file", type=Path, default=Path(".env"), help="Load dotenv from PATH (default: .env in cwd)")
    args = p.parse_args()

    # --- output-scaffold subcommand ---
    if args.command == "output-scaffold":
        _cmd_scaffold(args)
        return

    _load_dotenv(args.env_file)

    # Validate input file early (before printing the banner)
    input_path = getattr(args, "input", None) or args.file
    if input_path:
        inp = Path(input_path)
        if not inp.exists():
            print(f"  {theme.CRIMSON}Error: input file not found: {inp}{theme.RESET}\n", file=sys.stderr)
            sys.exit(1)
        if not inp.is_file():
            print(f"  {theme.CRIMSON}Error: input path is not a file: {inp}{theme.RESET}\n", file=sys.stderr)
            sys.exit(1)

    text = _read_input(args)

    if not args.quiet:
        print()
        print(
            f"  {theme.GOLD}{theme.BOLD}▌ JULIA READER HARNESS{theme.RESET}  "
            f"{theme.STONE}(standalone harness){theme.RESET}"
        )
        print(
            f"  {theme.DIM}{theme.STONE}Progressive chunks → live understanding → Markdown Chronicle under "
            f"_reader/{theme.RESET}\n"
        )

    base = Path(args.output).resolve()
    complete: Callable[[str, str], str] | None
    model_label: str
    if args.no_llm:
        complete = None
        model_label = "local-fallback"
    else:
        model_label, _base, complete = make_completer_for(args.model, args.base_url)

    summary = run_reader(
        raw_text=text,
        base_dir=base,
        complete=complete,
        model_label=model_label,
        use_llm=not args.no_llm,
        live=not args.quiet,
        max_pages_per_chunk=args.max_pages_per_chunk,
    )
    if summary is None:
        print(f"  {theme.CRIMSON}No content — cancelled.{theme.RESET}\n")
        sys.exit(1)

    folder = summary["folder"]
    print(f"\n  {theme.EMERALD}Chronicle complete.{theme.RESET}\n")
    print(f"  {theme.STONE}Folder:{theme.RESET}\n  {theme.PARCHMENT}{folder}{theme.RESET}\n")
    print(f"  {theme.STONE}Model:{theme.RESET} {theme.PARCHMENT}{summary['reader_model']}{theme.RESET}")
    print(
        f"  {theme.STONE}Artifacts:{theme.RESET} {summary['sentences']} sentences · "
        f"{summary['chunks']} chunks · {summary['chapters']} chapters · {summary['pages']} pages\n"
    )


def _cmd_scaffold(args: argparse.Namespace) -> None:
    """Handle the ``output-scaffold`` subcommand."""
    base = Path(args.output).resolve()
    book_name = args.book_name
    root = scaffold_book(
        base,
        book_name,
        source_filename=args.source_filename or book_name,
        exist_ok=args.exist_ok,
    )
    slug = root.name.replace("chronicle-", "", 1)
    print()
    print(f"  {theme.EMERALD}Chronicle directory scaffolded.{theme.RESET}")
    print(f"  {theme.STONE}Root:{theme.RESET}   {theme.PARCHMENT}{root}{theme.RESET}")
    print(f"  {theme.STONE}Slug:{theme.RESET}   {theme.PARCHMENT}{slug}{theme.RESET}")
    print(f"  {theme.STONE}Subdirs:{theme.RESET} {theme.PARCHMENT}source/, state/, book/, packet/, logs/{theme.RESET}")
    manifest_path = root / "_demo-manifest.json"
    if manifest_path.exists():
        print(f"  {theme.STONE}Manifest:{theme.RESET} {theme.PARCHMENT}_demo-manifest.json ✓{theme.RESET}")
    print()


if __name__ == "__main__":
    main()
