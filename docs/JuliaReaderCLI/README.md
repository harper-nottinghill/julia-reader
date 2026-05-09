# Julia Reader CLI — docs index

This folder documents the **command-line** Julia Reader harness and the optional **`terminal/`** bundle.

| Doc | What it covers |
|-----|----------------|
| **[How the terminal bundle works](how-the-terminal-bundle-works.md)** | What `terminal/setup.sh`, `bin/julia`, and `bin/julia-reader` do under the hood |
| **[CLI reference](cli-reference.md)** | Flags, env vars, output layout — same behavior as `python -m julia_reader` |

Related files elsewhere in the repo:

- [`terminal/README.md`](../../terminal/README.md) — quick start from the `terminal/` directory  
- [`SETUP.md`](../../SETUP.md) — full repo setup (root `.venv`, `.env`, smoke test)  
- Root [`README.md`](../../README.md) — project overview and install  
- [`pyproject.toml`](../../pyproject.toml) — `[project.scripts]` entry point `julia-reader`

There is **one** Python CLI implementation (`julia_reader.cli:main`). The terminal bundle does not fork behavior — it only wraps installs and launch commands.
