# Julia Reader — terminal bundle

Self-contained CLI setup for the same **julia-reader** harness as the repo root (`python -m julia_reader`). After setup you can run:

| Command | Meaning |
|--------|---------|
| `julia reader …` | Two-word launcher (this folder’s `bin/julia`) |
| `julia-reader …` | Direct launcher (`bin/julia-reader` → venv console script) |

Both accept the same flags as the main project: `-f`, `-o`, `-m`, `--no-llm`, `--quiet`, `--env-file`, etc.

## One-time setup

From this directory:

```bash
bash setup.sh
```

Then put `bin` on your `PATH`:

```bash
export PATH="/absolute/path/to/julia-reader/terminal/bin:$PATH"
```

(Add that line to `~/.zshrc` or `~/.bashrc` if you want it permanent.)

## Examples

```bash
julia reader --help
julia reader -f ../demo/nextjs-reader/content/dune-2021-transcript.txt -o ~/out --no-llm --quiet
julia-reader -f ./doc.txt -o . --no-llm
```

With API keys, from the **repository root** run **`bash scripts/configure-model.sh`** (presets for OpenAI, Groq, Together, OpenRouter, LM Studio, or custom URL). Then run the CLI from that directory so `.env` loads, or pass **`--env-file /path/to/.env`**. Omit **`--no-llm`** when using an API.

## Notes

- **venv** lives at `terminal/.venv` (ignored by git).
- If you use the **Julia language** as well, avoid putting `terminal/bin` ahead of Julia’s real binary, or use `julia-reader` instead of `julia reader`.

## More detail

See **[docs/JuliaReaderCLI/](../docs/JuliaReaderCLI/)** — especially _How the terminal bundle works_ and the CLI reference.
