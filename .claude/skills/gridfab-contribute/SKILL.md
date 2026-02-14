---
name: gridfab-contribute
description: Guide for contributing code to the GridFab repository. Use when making changes to GridFab's source code, fixing bugs, adding features, or submitting pull requests. Triggers on tasks like "fix this bug", "add a new CLI command", "refactor the renderer", or any code change to the gridfab codebase.
---

# Contributing to GridFab

## Setup

```bash
git clone https://github.com/azrazalea/gridfab.git
cd gridfab
pip install -e ".[dev]"
python -m pytest
```

## Before Every Commit

1. **Run tests**: `python -m pytest tests/ -v`
2. **Update CHANGELOG.md**: Add entries under `[Unreleased]` using Keep a Changelog categories (Added, Changed, Deprecated, Removed, Fixed, Security)
3. **Update INSTRUCTIONS.md**: If any user-facing behavior changed (CLI commands, GUI features, file formats, config options), reflect it in INSTRUCTIONS.md — including the suggested LLM prompt section if CLI commands changed

## Architecture Rules

- **Text-as-truth**: `grid.txt` IS the artwork. Never break backward compatibility with this format (space-separated values, one row per line, `.` for transparent)
- **CLI-first**: Every editing operation must be available via CLI
- **Minimal dependencies**: Python 3.10+ stdlib + Pillow only
- **File-system sync**: GUI and CLI coordinate through the filesystem, no sockets or IPC
- **Project = directory**: A sprite is a directory containing `grid.txt`, `palette.txt`, and generated outputs

## Project Layout

```
src/gridfab/          # Python package (src layout)
  cli.py              # CLI entry point (argparse)
  gui.py              # tkinter GUI
  core/               # Grid + Palette data structures
  render/             # Image rendering (Pillow)
  commands/           # CLI command implementations
tools/                # Standalone utility scripts
examples/             # Example sprites
tests/                # pytest test suite (fixtures in tests/fixtures/)
```

## Code Style

- Follow existing patterns in the codebase
- Don't add docstrings, comments, or type annotations to code you didn't change
- Keep functions small and focused
- Fail loudly with clear error messages including line numbers and context — LLMs need good errors to self-correct

## Palette Alias Rules

Aliases are 1-2 characters, case-sensitive, no case-insensitive duplicates, extended ASCII only, cannot start with `#`. `.` is reserved for transparent.

## Pull Request Process

1. Create a branch for your change
2. Make focused commits with clear messages
3. Ensure all tests pass
4. Update CHANGELOG.md and INSTRUCTIONS.md as needed
5. Submit PR with a clear description
