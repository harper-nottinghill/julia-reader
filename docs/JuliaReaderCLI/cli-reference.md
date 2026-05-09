# CLI reference

All of these invoke **the same** `julia_reader.cli:main` and accept **identical** arguments:

- `julia-reader …`
- `julia reader …` (via `terminal/bin/julia` — **terminal bundle only**)
- `python -m julia_reader …` (with venv activated or correct `PYTHONPATH`)

## Options

| Flag | Meaning |
|------|---------|
| `-h`, `--help` | Show help and exit |
| `-f FILE`, `--file FILE` | Read source text from `FILE` |
| `-o DIR`, `--out DIR` | Project root where **`_reader/<timestamp>_<slug>/`** is written (default: current directory) |
| `-m MODEL`, `--model MODEL` | Override model id for this run (`JULIA_READER_MODEL` / `.env` otherwise) |
| `--base-url URL` | Override API base URL (`JULIA_READER_BASE_URL`) |
| `--no-llm` | No HTTP calls; heuristic / local fallback summaries only |
| `--quiet` | Suppress colored progress lines (still runs full pipeline) |
| `--env-file PATH` | Load dotenv from `PATH` (default: `.env` in cwd) |

If neither `-f` nor stdin is used and stdin is a TTY, the CLI prints a hint and exits.

Stdin mode:

```bash
cat long.txt | julia-reader -o ~/project --quiet
```

## Environment variables

Loaded from **`--env-file`** or process environment (see **`.env.example`** at repo root):

| Variable | Role |
|----------|------|
| `JULIA_READER_API_KEY` | Bearer token (or use `OPENAI_API_KEY`) |
| `JULIA_READER_BASE_URL` | API root (default OpenAI-compatible `/v1`) |
| `JULIA_READER_MODEL` | Model id |
| `JULIA_READER_EXTRA_HEADERS` | Optional JSON object of extra HTTP headers |
| `JULIA_READER_DISABLE_LLM` | Set to `1` to force offline-style behavior via env |

Hosts must implement **`POST /v1/chat/completions`** in the usual OpenAI shape (or use **`--no-llm`**).

## Output layout

Under **`<out>/_reader/<timestamp>_<slug>/`**:

| Path | Contents |
|------|----------|
| `source/` | Raw / normalized / break-marked source |
| `state/` | Sentence map, chunks, lake strings, live summary, book plan, packet JSON, etc. |
| `book/` | Markdown Chronicle (index, preface, chapter pages) |
| `logs/` | Run log, validation report, LLM log, errors |
| `packet/` | Harper-style packet shards |

Same layout as documented in the root **README** — the terminal bundle does not change paths or filenames.

## Exit codes

Typical behavior:

- **`0`** — run completed; Chronicle written  
- **`1`** — empty input or fatal pipeline error (see stderr / logs)  
- **`2`** — argparse / usage (e.g. no file and TTY stdin)

The **`terminal/bin/julia`** helper uses **`2`** when the first argument is not **`reader`** (wrong invocation for that script).
