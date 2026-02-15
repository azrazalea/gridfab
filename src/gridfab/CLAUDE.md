# src/gridfab/ — Python Package

The main GridFab Python package, installed via `pip install gridfab`.

## Module Responsibilities

- **`__init__.py`** — Package version (`__version__`)
- **`__main__.py`** — Entry point for `python -m gridfab`
- **`cli.py`** — CLI argument parsing with argparse, dispatches to command modules
- **`gui.py`** — tkinter GUI editor with undo/redo, palette sidebar, canvas painting

## Subpackages

- **`core/`** — Data structures: Grid, Palette. No rendering, no I/O beyond file read/write.
- **`render/`** — Image generation using Pillow. Preview (checkerboard bg) and export (transparent bg).
- **`commands/`** — CLI command implementations. Each command function takes a directory Path and arguments.
- **`tagger/`** — Interactive tileset tagger GUI with AI-assisted naming. Entry points: `gridfab tag` and `gridfab-tagger`.

## Conventions

- All errors raise `ValueError`, `FileNotFoundError`, or `FileExistsError` with descriptive messages
- The CLI catches these and prints `ERROR:` to stderr
- Grid coordinates are always (row, col), 0-indexed
- All file I/O uses `newline="\n"` for cross-platform consistency
