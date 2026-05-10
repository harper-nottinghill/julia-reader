# Julia Reader — Terminal Bundle

**Version 1.0.0**

Self-contained CLI for [julia-reader](../README.md). After a one-time setup you get two launcher scripts:

| Command | Purpose |
|---------|---------|
| `julia reader …` | Two-word launcher (`bin/julia`) |
| `julia-reader …` | Direct launcher (`bin/julia-reader`) |

Both pass the same flags as `python -m julia_reader`: `-f`, `-o`, `-m`, `--no-llm`, `--quiet`, `--env-file`, and more.

---

## Prerequisites

- **Python ≥ 3.10** — check with `python3 --version`.
- **macOS / Linux** — setup is a Bash script (`setup.sh`).
- **curl / git** — only needed if installing via clone.

---

## Installation

1. **Clone the repo** (if you haven't already):

   ```bash
   git clone https://github.com/harper-nottinghill/julia-reader.git
   cd julia-reader
   ```

2. **Run setup** from the `terminal/` directory:

   ```bash
   cd terminal
   bash setup.sh
   ```

   This creates `terminal/.venv`, installs julia-reader in editable mode, and makes all `bin/` scripts executable. Re-running is safe — it skips if the installed version matches (pass `--force` to reinstall).

3. **Add `bin/` to your PATH**:

   ```bash
   export PATH="/absolute/path/to/julia-reader/terminal/bin:$PATH"
   ```

   Add that line to `~/.zshrc` or `~/.bashrc` for persistence.

4. **(Optional) Configure an LLM** — from the **repo root**, run:

   ```bash
   bash scripts/configure-model.sh
   ```

   This writes a `.env` with your API key and base URL (supports OpenAI, Groq, Together, OpenRouter, LM Studio, or custom). You can also set `OPENAI_API_KEY` manually or pass `--env-file /path/to/.env`.

---

## Quick Start

```bash
# Show available flags
julia-reader --help

# Parse a file locally (no LLM needed)
julia-reader -f ./notes.md -o . --no-llm --quiet

# Parse with an LLM (requires .env or OPENAI_API_KEY)
julia-reader -f transcript.txt -o ~/output

# Using the two-word launcher instead
julia reader -f ./doc.txt -o . --no-llm
```

> **Note:** If you also use the Julia programming language, prefer `julia-reader` over `julia reader` to avoid PATH conflicts.

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](../docs/JuliaReaderCLI/cli-reference.md) | Full list of commands and flags |
| [How the Terminal Bundle Works](../docs/JuliaReaderCLI/how-the-terminal-bundle-works.md) | Architecture and internals |
| [Configure Model](../docs/JuliaReaderCLI/configure-model.md) | Setting up LLM providers |
| [Project README](../README.md) | Broader project overview and contributing guide |

---

## Notes

- The virtual environment lives at `terminal/.venv` (git-ignored).
- Version is read from `pyproject.toml` at install time and written to `terminal/.installed-version`.

---

## Developer

### Building a distributable bundle

From the repository root:

    bash scripts/build-terminal-bundle.sh

The output is written to `dist/julia-reader-terminal-vX.Y.Z.tar.gz`.

The archive is self-contained: extract it and run `setup.sh` — no repository access needed. Inside the bundle, setup.sh detects the absence of the full repo and installs from vendored source instead.

#### What goes into the bundle

| File / Directory | Purpose |
|---|---|
| `bin/` | Executable entry points (`julia`, `julia-reader`) |
| `setup.sh` | One-time environment setup |
| `vendor/julia_reader/` | Vendored application source |
| `README.md` | User-facing instructions |
| `VERSION` | Machine-readable version string and build date |
| `CHECKSUMS.txt` | SHA-256 integrity manifest for all files |

#### Verifying a bundle

```bash
bash scripts/build-terminal-bundle.sh
tmpdir=$(mktemp -d)
tar -xzf dist/julia-reader-terminal-v*.tar.gz -C "$tmpdir"
# Inspect contents
ls "$tmpdir/bin" "$tmpdir/setup.sh" "$tmpdir/VERSION" "$tmpdir/CHECKSUMS.txt"
# Verify checksums
cd "$tmpdir" && sha256sum -c CHECKSUMS.txt
# Smoke-test setup
bash "$tmpdir/setup.sh"
rm -rf "$tmpdir"
```

#### Cleaning

    rm -rf dist/
