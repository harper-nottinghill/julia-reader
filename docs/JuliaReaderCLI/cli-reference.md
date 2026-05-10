# CLI reference

All of these invoke **the same** `julia_reader.cli:main` and accept **identical** arguments:

- `julia-reader …`
- `julia reader …` (via `terminal/bin/julia` — **terminal bundle only**)
- `python -m julia_reader …` (with venv activated or correct `PYTHONPATH`)

## Options

| Flag | Meaning |
|------|---------|
| `-h`, `--help` | Show help and exit |
| `-i FILE`, `--input FILE` | Source text or markdown file to process (`.txt` or `.md`) |
| `-f FILE`, `--file FILE` | Alias for `--input` (backward compat) |
| `-o DIR`, `--output DIR`, `--out DIR` | Output directory for **`_reader/<timestamp>_<slug>/`** tree (default: current directory) |
| `-m MODEL`, `--model MODEL` | Override model id for this run (`JULIA_READER_MODEL` / `.env` otherwise) |
| `--base-url URL` | Override API base URL (`JULIA_READER_BASE_URL`) |
| `--no-llm` | No HTTP calls; heuristic / local fallback summaries only |
| `--quiet` | Suppress colored progress lines (still runs full pipeline) |
| `--max-pages-per-chunk N` | Max pages generated per chunk (default: `1`; set `>1` to enable multi-page generation) |
| `--book-name NAME` | Override the book name used for directory naming and manifest (default: derived from input filename or first heading) |
| `--env-file PATH` | Load dotenv from `PATH` (default: `.env` in cwd) |

If no input file is given and stdin is a TTY, the CLI prints a usage hint and exits.

### `output-scaffold` subcommand

Scaffolds a Chronicle output directory tree without running the pipeline. Useful for pre-creating directory structures or inspecting the layout.

```
julia-reader output-scaffold "Book Name" -o ./output
```

| Subcommand flag | Meaning |
|-----------------|---------|
| `book_name` (positional) | Human-readable book name for the chronicle directory |
| `-o DIR`, `--output DIR`, `--out DIR` | Base output directory (default: current directory) |
| `--source-filename FILE` | Original source filename (stored in manifest) |
| `--exist-ok` | Do not error if the chronicle directory already exists |

Creates `source/`, `state/`, `book/`, `packet/`, `logs/` subdirectories plus a `_demo-manifest.json`.

## Examples

### Single file — basic usage

```bash
# Process a text file with default settings
julia-reader --input doc.txt --output ./output

# Markdown input, no API calls
julia-reader --input novel.md --output ./chronicle --no-llm

# Stdin mode (pipe)
cat long.txt | julia-reader -o ~/project --quiet

# Old -f flag still works
julia-reader -f doc.txt -o ./out
```

### Novel — single book with custom name

```bash
julia-reader --input my-novel.txt --output ./chronicles --book-name "The Silent Shore" --max-pages-per-chunk 2
```

Processes `my-novel.txt` into a Chronicle under `./chronicles/_reader/<timestamp>_the_silent_shore/`. The `--book-name` flag overrides the auto-detected title for directory naming and manifest metadata. With `--max-pages-per-chunk 2`, each chunk produces up to two Markdown pages instead of one, giving richer chapter coverage for long-form prose.

### Screenplay — markdown source

```bash
julia-reader --input screenplay-final.md --output ./chronicles --book-name "Midnight Protocol" --quiet
```

Processes a markdown-formatted screenplay. The chunking heuristics work on plain text and markdown alike; scene headings (`##`, `###`) are treated as natural subject breaks. Use `--quiet` to suppress the ritual progress output when scripting.

### Essay collection — processing multiple documents

Run Julia Reader once per document to build separate Chronicles in the same output directory:

```bash
# Process each essay into its own Chronicle under ./essays/_reader/
for essay in essays/*.txt; do
  julia-reader --input "$essay" --output ./essays --book-name "$(basename "$essay" .txt)"
done
```

Each invocation creates an independent Chronicle at `./essays/_reader/<timestamp>_<slug>/` — one per essay. Because the output directory is shared, all Chronicles live under the same `./essays/_reader/` tree.

Or scaffold directories first and fill them later:

```bash
# Pre-create the directory structure for a book
julia-reader output-scaffold "Collected Essays" -o ./output
```

### Override model and API for a single run

```bash
julia-reader --input research-notes.md --output ./out --model gpt-4o --base-url https://api.openai.com/v1
```

## Environment variables

Use **`bash scripts/configure-model.sh`** (from repo root) for guided presets and merging into `.env` — see **[configure-model.md](configure-model.md)**.

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

Under **`<output>/_reader/<timestamp>_<slug>/`**:

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
