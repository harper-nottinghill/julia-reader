# Configure model & API (`configure-model`)

Julia Reader talks to any **OpenAI-compatible** server (`POST …/v1/chat/completions`). Use this script to merge **API key**, **base URL**, **model id**, and optional **extra headers** into `.env` without hand-editing.

## Scripts

| Path | Role |
|------|------|
| [`scripts/configure-model.sh`](../../scripts/configure-model.sh) | Runs [`configure_model.py`](../../scripts/configure_model.py) with your `python3` |
| [`scripts/configure_model.py`](../../scripts/configure_model.py) | Implementation (interactive or flags) |

## Behavior

- Writes (or updates) a **marked block** in `.env`:
  - `# <<< julia-reader-model (managed by configure-model) >>>`
  - …variables…
  - `# <<< end julia-reader-model >>>`
- Any previous managed block is **replaced**; the rest of `.env` is kept.
- The previous `.env` file is saved as **`.env.bak`** when it already existed.

## Interactive (recommended)

From the **repository root**:

```bash
bash scripts/configure-model.sh
```

You’ll be asked:

1. Offline-only mode or API mode  
2. **Preset** gateway (OpenAI, Groq, Together, OpenRouter, LM Studio, or custom URL)  
3. API key (hidden input)  
4. Optional overrides for base URL and model id  
5. Optional JSON for `JULIA_READER_EXTRA_HEADERS` (Azure-style keys, etc.)

## Non-interactive / CI

```bash
# OpenAI (explicit defaults)
bash scripts/configure-model.sh --non-interactive --api-key "$OPENAI_API_KEY"

# Groq — preset fixes base URL + default model; override model if you want
bash scripts/configure-model.sh --non-interactive --preset groq --api-key "$GROQ_API_KEY" --model llama-3.1-8b-instant

# Local LM Studio
bash scripts/configure-model.sh --non-interactive --preset lmstudio --api-key "lm-studio" --model your-export-name

# Offline / smoke tests
bash scripts/configure-model.sh --non-interactive --offline
```

Use **`--env-file path`** to write somewhere other than the repo root `.env`.

## Presets (built-in)

| `--preset` | Default base URL | Default model id |
|------------|------------------|------------------|
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `together` | `https://api.together.xyz/v1` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| `openrouter` | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` |
| `lmstudio` | `http://localhost:1234/v1` | `local-model` |

Defaults are **starting points** — providers change model IDs often; always pass **`--model`** if yours differs.

## Adding a new gateway

You don’t have to patch the script if you use **custom**:

1. Run interactively and choose **custom**, or  
2. Pass **`--base-url`** / **`--model`** without **`--preset`**.

To add a **named preset** for your team, extend the **`PRESETS`** dict in [`scripts/configure_model.py`](../../scripts/configure_model.py) and open a PR.

## CLI usage after configure

Run from the directory that contains `.env` (usually repo root), or pass **`--env-file`** to `julia-reader`:

```bash
julia-reader -f doc.txt -o .
# or
julia-reader --env-file /path/to/.env -f doc.txt -o .
```

Same for **`julia reader`** from the [terminal bundle](../how-the-terminal-bundle-works.md).
