# Julia Reader Harness

This repo is a **standalone progressive Reader harness** for the terminal: sentence splitting, dynamic chunking (≤2000 token estimates), per-chunk LLM summaries with a **live evolving understanding**, Lake Strings / breaks / packet JSON, Markdown **Chronicle** output, and validation.

It ships as **stdlib-only Python** plus your **OpenAI-compatible** HTTP endpoint—no heavyweight framework imports required.

## For visitors (GitHub landing)

**What it does.** Julia Reader ingests long, messy source text (transcripts, logs, notes) and walks it the way a careful human would: stable **sentence maps**, bounded **chunks**, soft **subject breaks**, and a **running synthesis** that updates as each chunk is read. It then **plans a book**, writes **Markdown pages** (index, preface, chapters), and seals a **Harper-style packet** (indexes, shard metadata) with a **validation report**. The output is a reproducible **Chronicle folder** under `_reader/<timestamp>_<slug>/`, not a single blob of prose.

**Research angle.** We treat “reading” as an **agent loop** with **layered limbs**: some steps are cheap and deterministic (normalize, split, lake strings, chunking, validation), others are **LLM limbs** (per-chunk JSON summaries, live understanding). The **lake** layer keeps structured signals about sentences—enough texture for downstream tools without rereading the whole source every time. The **Chronicle** is deliberately book-shaped so humans and other agents can **browse, cite, and extend** understanding instead of drowning in context windows.

**Why open source.** We want **other builders** to experiment with **how machines read and retain meaning**: different chunking strategies, safer prompts, non-English pipelines, retrieval hooks, evaluation harnesses, or entirely different “book” layouts. If the community improves **reading-as-structure**—not just bigger models—we all get better scaffolding for **analysis, compliance, education, creative tooling, and other AI workflows** that depend on grounded summaries rather than vibes.

### Major themes (names you can reason about)

These are the ideas we care about—not opaque numeric slugs:

- **Progressive reading** — work in bounded passes instead of one heroic context dump.
- **Live understanding** — a single document that evolves as evidence arrives (chunk by chunk).
- **Lake-scale structure** — sentence-level metadata and breaks that make the source navigable.
- **Simulated books** — human-legible artifacts (Markdown + maps) that stand in for “I read the whole thing.”
- **Validation as discipline** — checks that the run is internally consistent before you trust downstream use.

## Research white paper

For the full argument (agentic reading, progressive loops, Chronicles, evaluation, roadmap):

- **[WHITE_PAPER.md](WHITE_PAPER.md)** — copy at repository root  
- **[docs/whitepaper.md](docs/whitepaper.md)** — same document under `docs/`  
- **Next.js demo:** run `demo/nextjs-reader` and open the **White paper** route (`/whitepaper`). After editing `WHITE_PAPER.md`, run `npm run sync:whitepaper` inside `demo/nextjs-reader` to refresh `public/whitepaper.md` and `docs/whitepaper.md`.

## Why “Julia Reader”

Internal codename for the **Reader-as-its-own-harness** line: ritual CLI colors and an “agent take” loop (read → augment → write artifacts), packaged so others can harden chunking, prompts, and book layout in one focused codebase.

## Install (editable)

For the guided setup:

```bash
./scripts/setup.sh
```

That creates `.venv/`, installs the package, creates `.env` from `.env.example`, and runs a no-LLM smoke test. See `SETUP.md` for the full first-run guide.

### Terminal bundle (`julia reader`)

For a dedicated copy under **`terminal/`** (its own `.venv` plus **`julia reader`** and **`julia-reader`** launchers):

```bash
cd terminal
bash setup.sh
export PATH="$(pwd)/bin:$PATH"
julia reader --help
```

See **[terminal/README.md](terminal/README.md)** and **[docs/JuliaReaderCLI/](docs/JuliaReaderCLI/)** for how the bundle works.

**LLM / model setup** — register any OpenAI-compatible API (OpenAI, Groq, Together, LM Studio, …):

```bash
bash scripts/configure-model.sh
```

See **[docs/JuliaReaderCLI/configure-model.md](docs/JuliaReaderCLI/configure-model.md)**.

Manual setup:

```bash
cd julia-reader
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Or run without install:

```bash
export PYTHONPATH=src
python3 -m julia_reader --help
```

## Configure

Copy `.env.example` to `.env` in your working directory (or pass `--env-file`). Variables:

| Variable | Meaning |
|----------|---------|
| `JULIA_READER_API_KEY` | Bearer token (or use `OPENAI_API_KEY`) |
| `JULIA_READER_BASE_URL` | API root, default `https://api.openai.com/v1` |
| `JULIA_READER_MODEL` | Model id, default `gpt-4o-mini` |
| `JULIA_READER_EXTRA_HEADERS` | Optional JSON object of extra headers |
| `JULIA_READER_DISABLE_LLM` | Set to `1` for offline heuristic-only run |

Any host that implements `POST /v1/chat/completions` in the usual OpenAI shape works (OpenAI, many proxies, compatible gateways).

## Usage

Write a Chronicle under **`<out>/_reader/<timestamp>_<slug>/`** using this layout: `source/`, `state/`, `book/`, `logs/`, `packet/`.

```bash
# From stdin
cat long-transcript.txt | julia-reader -o ~/my-project

# From file
julia-reader -f ./notes.md -o ~/my-project -m gpt-4o

# No API (smoke test / CI)
julia-reader -f ./notes.md --no-llm --quiet
```

Flags:

- `-o` / `--out` — project directory for `_reader/` (default: current directory)
- `-m` / `--model` — override model for this run
- `--base-url` — override API base URL
- `--no-llm` — skip HTTP; local fallback summaries only
- `--quiet` — suppress colored ritual progress lines
- `--env-file` — dotenv path (default `.env`)
- `--max-pages-per-chunk` — max pages per chunk (default: 1; set >1 for multi-page)
- `--book-name` — override book name for directory naming and manifest

### Multi-book processing

Julia Reader processes one document per invocation. To build Chronicles for multiple books (e.g., an essay collection), run it once per file with a shared output directory:

```bash
for doc in essays/*.txt; do
  julia-reader --input "$doc" --output ./chronicles --book-name "$(basename "$doc" .txt)"
done
```

Each run produces an independent Chronicle under `./chronicles/_reader/`. See **[CLI reference](docs/JuliaReaderCLI/cli-reference.md)** for full flag documentation and examples.

## Agent take loop (preserved)

1. **Ingest** — normalize, sentence map, lake strings, breaks.  
2. **Chunk** — bounded tokens, subject heuristics.  
3. **Per-chunk LLM** — JSON chunk summary + live summary update (silent HTTP; no harness streaming).  
4. **Plan + write** — `book_plan.json`, chapter folders, pages, index, preface.  
5. **Packet + validate** — Harper-style packet shards + `validation_report.md`.

## Lore / colors

ANSI palette lives in `src/julia_reader/theme.py`. Progress lines follow the Reader ritual names (Archive Charm, Scourgify, Sentence Scrying, Augury, …).

## Contributing

PRs welcome: calmer break detection, quieter prompts, better JSON discipline per provider, tests, and packaging. Keep dependencies minimal so this stays easy to fork and embed.

## Changelog

### v1.0.0 (2025-05-10)

First stable release of the Julia Reader terminal bundle.

- **Terminal bundle** — self-contained CLI under `terminal/` with `setup.sh`, `bin/julia`, and `bin/julia-reader` launchers.
- **Distributable tarball** — `bash scripts/build-terminal-bundle.sh` produces a portable archive that installs from vendored source with no repository access required.
- **Dune (2021) demo chronicle** — expanded chapter pages and validation report in the Next.js demo.
- **New modules** — `error_logger.py` and `output_scaffold.py` for structured error tracking and Chronicle directory scaffolding.
- **Test suite** — integration tests for the generalized pipeline and validation.
- **Model configuration** — `scripts/configure-model.sh` for interactive LLM provider setup.
- **CLI reference** — full flag documentation in `docs/JuliaReaderCLI/`.
- **Smoke-tested** — distributable tarball verified end-to-end in a clean-room environment (checksums pass, setup succeeds, `julia-reader --no-llm` produces a complete Chronicle).

**Download:** `julia-reader-terminal-v1.0.0.tar.gz` (48 KB)
**SHA-256:** `259001b9e22532c8389fc6c3e51f8945da25bf7600ad51c461bab82ceaf2abb5`

---

## License

MIT — see `LICENSE`.
