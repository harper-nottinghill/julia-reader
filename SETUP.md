# Setup Guide

This guide helps a new user install and run **Julia Reader** locally.

## 1. Requirements

- Python 3.10+
- A terminal
- Optional: an OpenAI-compatible LLM endpoint

The harness has no required third-party Python packages.

## 2. Quick Setup

From the project folder:

```bash
./scripts/setup.sh
```

The setup script will:

- create `.venv/` if needed
- install the package in editable mode
- copy `.env.example` to `.env` if `.env` does not exist
- run a local no-LLM smoke test
- print the next command to try

## 3. Add An LLM

Recommended — guided presets (OpenAI, Groq, Together, OpenRouter, LM Studio, or custom URL):

```bash
bash scripts/configure-model.sh
```

That merges a marked block into `.env` (see `docs/JuliaReaderCLI/configure-model.md`). Or edit `.env` by hand:

```bash
JULIA_READER_API_KEY=sk-...
JULIA_READER_BASE_URL=https://api.openai.com/v1
JULIA_READER_MODEL=gpt-4o-mini
```

Any endpoint that supports the OpenAI-compatible shape works:

```text
POST /v1/chat/completions
```

The model call is intentionally simple: one system message, one user message, JSON response expected.

## 4. Run It

With a file:

```bash
source .venv/bin/activate
julia-reader -f ./notes.md -o .
```

With stdin:

```bash
cat transcript.txt | julia-reader -o .
```

Offline smoke test:

```bash
julia-reader -f ./notes.md --no-llm
```

Output appears under:

```text
_reader/YYYY-MM-DD_HH-MM-SS_slug/
```

## 5. Common Issues

`No API key`

Set `JULIA_READER_API_KEY` in `.env`, or export `OPENAI_API_KEY`.

`command not found: julia-reader`

Activate the venv:

```bash
source .venv/bin/activate
```

or run directly:

```bash
PYTHONPATH=src python3 -m julia_reader --help
```

`LLM response did not contain JSON`

The harness retries once, then falls back to local heuristic summaries. The run folder is preserved and errors are written to:

```text
_reader/.../logs/errors.log
```

