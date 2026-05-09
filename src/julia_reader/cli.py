"""Terminal entry — Julia Reader harness (no Orbos)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from . import theme
from .llm import make_completer_for
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
    if args.file:
        return Path(args.file).read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print(
        f"  {theme.PARCHMENT}No file and stdin is a TTY.{theme.RESET}\n"
        f"  {theme.STONE}Pipe text in:{theme.RESET} {theme.GOLD}cat doc.txt | julia-reader{theme.RESET}\n"
        f"  {theme.STONE}Or:{theme.RESET} {theme.GOLD}julia-reader -f path/to.txt{theme.RESET}\n",
        flush=True,
    )
    sys.exit(2)


def main() -> None:
    p = argparse.ArgumentParser(
        prog="julia-reader",
        description="Julia Reader — progressive Reader Chronicle harness (OpenAI-compatible API).",
    )
    p.add_argument("-f", "--file", help="Source text file")
    p.add_argument("-o", "--out", default=".", help="Project root for _reader/ output (default: cwd)")
    p.add_argument("-m", "--model", help="Override JULIA_READER_MODEL for this run")
    p.add_argument("--base-url", help="Override JULIA_READER_BASE_URL")
    p.add_argument("--no-llm", action="store_true", help="Local fallback only (no API calls)")
    p.add_argument("--quiet", action="store_true", help="Suppress ritual progress lines")
    p.add_argument("--env-file", type=Path, default=Path(".env"), help="Optional dotenv path")
    args = p.parse_args()

    _load_dotenv(args.env_file)

    if not args.quiet:
        print()
        print(
            f"  {theme.GOLD}{theme.BOLD}▌ JULIA READER HARNESS{theme.RESET}  "
            f"{theme.STONE}(standalone · not Orbos){theme.RESET}"
        )
        print(
            f"  {theme.DIM}{theme.STONE}Progressive chunks → live understanding → Markdown Chronicle under "
            f"_reader/{theme.RESET}\n"
        )

    text = _read_input(args)
    base = Path(args.out).resolve()
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


if __name__ == "__main__":
    main()
