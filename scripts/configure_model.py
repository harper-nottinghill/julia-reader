#!/usr/bin/env python3
"""Merge OpenAI-compatible model settings into .env for Julia Reader.

Works with any host that exposes POST /v1/chat/completions (OpenAI, proxies,
many gateways). Run interactively or pass --non-interactive with flags.

Does not install Python packages — only edits the env file.
"""

from __future__ import annotations

import argparse
import getpass
import re
import sys
from pathlib import Path


PRESETS: dict[str, tuple[str, str]] = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "together": ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "openrouter": ("https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
    "lmstudio": ("http://localhost:1234/v1", "local-model"),
}


MARK_BEGIN = "# <<< julia-reader-model (managed by configure-model) >>>"
MARK_END = "# <<< end julia-reader-model >>>"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def extract_managed_block(text: str) -> tuple[str, str]:
    """Return (outside_block, inner_managed_content_or_empty)."""
    pattern = re.compile(
        re.escape(MARK_BEGIN) + r"[\s\S]*?" + re.escape(MARK_END) + r"\n?",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return text, ""
    before = text[: m.start()]
    after = text[m.end() :]
    inner = text[m.start() : m.end()]
    return before + after, inner


def build_block(
    *,
    offline: bool,
    api_key: str,
    base_url: str,
    model: str,
    extra_headers: str,
) -> str:
    lines = [MARK_BEGIN]
    if offline:
        lines.append("JULIA_READER_DISABLE_LLM=1")
        lines.append("# JULIA_READER_API_KEY=")
        lines.append("# JULIA_READER_BASE_URL=")
        lines.append("# JULIA_READER_MODEL=")
    else:
        lines.append(f"JULIA_READER_API_KEY={api_key.strip()}")
        lines.append(f"JULIA_READER_BASE_URL={base_url.strip().rstrip('/')}")
        lines.append(f"JULIA_READER_MODEL={model.strip()}")
        lines.append("JULIA_READER_DISABLE_LLM=")
        if extra_headers.strip():
            esc = extra_headers.strip().replace("\n", " ")
            lines.append(f"JULIA_READER_EXTRA_HEADERS={esc}")
    lines.append(MARK_END)
    lines.append("")
    return "\n".join(lines) + "\n"


def merge_into_env(env_path: Path, block: str) -> bool:
    """Write merged .env; backup previous file if it existed. Returns True if backup written."""
    raw = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    outside, _ = extract_managed_block(raw)
    outside = outside.rstrip() + ("\n\n" if outside.strip() else "")
    new_content = outside + block
    had_previous = env_path.is_file()
    if had_previous:
        bak = env_path.with_suffix(env_path.suffix + ".bak")
        bak.write_text(raw, encoding="utf-8")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(new_content.rstrip() + "\n", encoding="utf-8")
    return had_previous


def interactive_defaults() -> tuple[bool, str, str, str, str]:
    print("Julia Reader — model configuration (OpenAI-compatible API)\n")
    off = input("Use offline / --no-LLM only? (no API calls) [y/N]: ").strip().lower() in (
        "y",
        "yes",
    )
    if off:
        return True, "", "https://api.openai.com/v1", "gpt-4o-mini", ""

    print("\nPick a gateway preset (you can override URL/model next).")
    keys = list(PRESETS.keys())
    for i, name in enumerate(keys, start=1):
        bu, mid = PRESETS[name]
        print(f"  {i}) {name:12}  base={bu}   default model={mid}")
    print(f"  {len(keys) + 1}) custom — enter base URL and model yourself")

    choice = input("\nChoice [1]: ").strip() or "1"
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        pname = keys[int(choice) - 1]
        base, model = PRESETS[pname]
        print(f"\nUsing preset {pname!r}: {base} | model {model}")
    else:
        base = "https://api.openai.com/v1"
        model = "gpt-4o-mini"

    print("\nAny provider works if it exposes POST {base}/chat/completions in OpenAI shape.")
    key = getpass.getpass("API key (Bearer / OpenAI-compatible): ").strip()
    if not key:
        print("error: API key required unless offline.", file=sys.stderr)
        sys.exit(2)

    base_in = input(f"Base URL [{base}]: ").strip()
    if base_in:
        base = base_in.rstrip("/")
    model_in = input(f"Model id [{model}]: ").strip()
    if model_in:
        model = model_in

    extra = input(
        'Extra HTTP headers as JSON object (optional, Enter to skip) e.g. {"api-key":"..."}: ',
    ).strip()
    return False, key, base.rstrip("/"), model, extra


DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def main() -> None:
    root = repo_root()
    p = argparse.ArgumentParser(
        description="Configure Julia Reader LLM endpoint + model in .env",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=root / ".env",
        help=f"path to .env (default: {root / '.env'})",
    )
    p.add_argument("--non-interactive", action="store_true")
    p.add_argument("--offline", action="store_true", help="set JULIA_READER_DISABLE_LLM=1")
    p.add_argument("--api-key", default="", help="Bearer-style API key")
    p.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        metavar="NAME",
        help="gateway preset: sets default base URL + model (%s)"
        % ", ".join(PRESETS.keys()),
    )
    p.add_argument(
        "--base-url",
        default=None,
        help=f"override base URL (default without --preset: {DEFAULT_BASE})",
    )
    p.add_argument(
        "--model",
        default=None,
        help=f"override model id (default without --preset: {DEFAULT_MODEL})",
    )
    p.add_argument("--extra-headers", default="", help='JSON object string, e.g. \'{"api-key":"x"}\'')
    args = p.parse_args()

    env_path: Path = args.env_file
    if not args.non_interactive:
        off, key, base, model, extra = interactive_defaults()
    else:
        off = args.offline
        key = args.api_key
        extra = args.extra_headers
        if args.preset:
            base, model = PRESETS[args.preset]
        else:
            base = (args.base_url or DEFAULT_BASE).rstrip("/")
            model = args.model or DEFAULT_MODEL
        if args.base_url is not None:
            base = args.base_url.rstrip("/")
        if args.model is not None:
            model = args.model
        if not off and not key.strip():
            print("error: --non-interactive requires --api-key or --offline", file=sys.stderr)
            sys.exit(2)

    block = build_block(
        offline=off,
        api_key=key,
        base_url=base,
        model=model,
        extra_headers=extra,
    )
    backed_up = merge_into_env(env_path, block)

    print(f"\nWrote managed block to {env_path}")
    if backed_up:
        bak = env_path.with_suffix(env_path.suffix + ".bak")
        print(f"Previous file backed up to {bak}")
    print("\nRun from repo root (or pass --env-file):")
    print("  julia-reader -f sample.txt -o .")
    print("Or terminal bundle:")
    print("  julia reader -f sample.txt -o .")


if __name__ == "__main__":
    main()
