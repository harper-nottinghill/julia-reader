# How the terminal bundle works

The **`terminal/`** directory is an optional **distribution shell** around the same Julia Reader package as the rest of the repo. It does not contain a second implementation of the reader — only a dedicated virtualenv, install glue, and thin shell scripts.

## Components

### 1. `terminal/setup.sh`

When you run:

```bash
bash terminal/setup.sh
```

this script:

1. Resolves **`terminal/`** as `ROOT` and the **repository root** (parent of `terminal/`) as `REPO`.
2. Creates **`terminal/.venv`** with `python3 -m venv` (override interpreter with `PYTHON=/path/to/python3.12` if needed).
3. Upgrades **`pip`**, **`wheel`**, **`setuptools`** inside that venv.
4. Runs **`pip install -e "$REPO"`**, which installs the **`julia-reader`** package in **editable** mode from the repo’s [`pyproject.toml`](../../pyproject.toml).

Editable install means: changes you make under **`src/julia_reader/`** are picked up on the next CLI run **without reinstalling**, as long as you use this venv’s `julia-reader`.

The venv is listed in **`.gitignore`** (pattern `.venv/`), so it is never committed.

### 2. Console script `julia-reader`

`pip install -e` registers the **`[project.scripts]`** entry:

```toml
julia-reader = "julia_reader.cli:main"
```

So inside **`terminal/.venv/bin/`** you get an executable **`julia-reader`** that calls **`julia_reader.cli:main`**. That is the **same** entry point as when you install from the repo root.

### 3. `terminal/bin/julia-reader` (wrapper)

This is a small **bash** script that:

- Finds **`terminal/.venv/bin/julia-reader`**
- **`exec`**’s it with all arguments unchanged

So **`terminal/bin/julia-reader`** is just a stable path you can put on **`PATH`** without activating the venv manually.

### 4. `terminal/bin/julia` (two-word launcher)

This script implements the **`julia reader …`** spelling:

1. It checks that the first argument is exactly **`reader`**. If not, it prints usage and exits (so plain **`julia`** does **not** start the Julia programming language — see warning below).
2. It **`shift`**s off **`reader`**.
3. It **`exec`**’s **`terminal/.venv/bin/julia-reader`** with the remaining arguments.

So **every** supported invocation looks like:

```text
julia reader [same options as julia-reader]
```

which is equivalent to:

```text
julia-reader [options]
python -m julia_reader [options]    # with PYTHONPATH or activated venv
```

### 5. End-to-end flow

```text
You type:     julia reader -f doc.txt -o ~/proj --no-llm
                    │
                    ▼
terminal/bin/julia   strips "reader", forwards rest
                    │
                    ▼
terminal/.venv/bin/julia-reader   (setuptools console script)
                    │
                    ▼
julia_reader.cli:main()   in src/julia_reader/cli.py
                    │
                    ▼
pipeline.run_reader(...)   same code path as any other install
```

## Why both `julia reader` and `julia-reader`?

- **`julia-reader`** matches the **PyPI-style** console script name and avoids touching the name **`julia`**.
- **`julia reader`** is for teams that want a **two-word** mnemonic; it is implemented **only** as a shell stub, not a second Python binary.

## Conflict with the Julia language

The **`julia`** executable name is used by the **Julia programming language**. If **`terminal/bin`** appears **before** Julia’s real binary on **`PATH`**, then typing **`julia`** alone runs **this** launcher (which only accepts **`julia reader`**).

Mitigations:

- Prefer **`julia-reader`** on **`PATH`**, or  
- Put **`terminal/bin`** **after** Julia’s install on **`PATH`**, or  
- Call the language binary by full path.

## Updating after `git pull`

If dependencies or packaging change, re-run:

```bash
bash terminal/setup.sh
```

Or manually:

```bash
terminal/.venv/bin/pip install -e "$(git rev-parse --show-toplevel)"
```

No separate “terminal version” of the reader logic exists — you are always running **`src/julia_reader`**.
