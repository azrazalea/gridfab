# GridFab — Development Guide

## What This Is

GridFab is a pixel art editor where artwork is stored as plain text (`grid.txt` + `palette.txt`). It has a CLI for LLMs and a tkinter GUI for humans, both operating on the same files.

## Architecture

- **Text-as-truth**: `grid.txt` IS the artwork. GUI and CLI are views/editors of this truth. No binary formats, no databases, no hidden state.
- **File-system sync**: GUI and CLI coordinate through the filesystem. No sockets, no IPC. The GUI has a Refresh button.
- **Project = directory**: A sprite is a directory containing `grid.txt`, `palette.txt`, and generated outputs.
- **CLI-first**: Every editing operation must be available via CLI. The CLI is the API for LLMs.

## Project Layout

```
src/gridfab/          # Python package (src layout)
  cli.py              # CLI entry point (argparse)
  gui.py              # tkinter GUI
  core/               # Grid + Palette data structures
  render/             # Image rendering (Pillow)
  commands/           # CLI command implementations
tools/                # Standalone utility scripts (atlas builder)
examples/             # Example sprites with grid.txt + palette.txt
tests/                # pytest test suite
```

## Project Documentation

- **README.md** — Project overview, quick start, feature summary. Links to all other docs.
- **INSTRUCTIONS.md** — Full user manual: GUI guide, CLI reference, file format details, gridfab.json config options, and a suggested LLM prompt. This is the primary user-facing documentation and is included in build artifacts.
- **CHANGELOG.md** — Version history following [Keep a Changelog](https://keepachangelog.com/) format.
- **CONTRIBUTING.md** — Contributor guidelines, PR process, development setup.
- **CODE_OF_CONDUCT.md** — Contributor Covenant v2.1.
- **LICENSE.md** — AGPLv3 full text.
- **GRIDFAB_PROJECT_SPEC.md** — Full project specification and roadmap.

## Key Rules

1. **Never break backward compatibility with grid.txt format.** Space-separated values, one row per line, `.` for transparent.
2. **Palette aliases are 1-2 characters**, case sensitive, no case-insensitive duplicates, extended ASCII only, cannot start with `#`.
3. **Fail loudly** with clear error messages including line numbers and context. LLMs need good errors to self-correct.
4. **Minimal dependencies**: Python 3.10+ stdlib + Pillow. No numpy, no web frameworks, no databases.
5. **No unnecessary files**: Don't add docstrings/comments/types to code you didn't change.
6. **Update CHANGELOG.md before every commit.** Add entries under `[Unreleased]` using Keep a Changelog categories: Added, Changed, Deprecated, Removed, Fixed, Security.
7. **Update INSTRUCTIONS.md when user-facing behavior changes.** Any new or modified CLI commands, GUI features, file format changes, or config options must be reflected in INSTRUCTIONS.md. This includes the suggested LLM prompt section if CLI commands change.

## Build & CI

GitHub Actions workflow (`.github/workflows/release.yml`) runs on every push to main and on PRs:
- Tests on all 3 platforms (Windows, macOS, Linux)
- Nuitka compilation to native binaries (CLI + GUI)
- Artifacts named with commit SHA (or version tag for releases)
- Build artifacts include: binaries, project docs (README, LICENSE, CHANGELOG, INSTRUCTIONS), source code (`src/`), and tests (`tests/`)
- Tagged releases (`v*`) create GitHub Releases with platform archives

## Common Commands

```bash
pip install -e .                    # Install in dev mode
pip install -e ".[dev]"             # Install with dev deps (pytest)
python -m gridfab init              # Create blank sprite in current dir
python -m gridfab render            # Render preview
python -m gridfab export            # Export PNGs
python -m pytest                    # Run tests
gridfab-gui .                       # Launch GUI
```

## File Format Reference

- **grid.txt**: N rows, M columns, space-separated. Values: `.`, palette alias, or `#RRGGBB`
- **palette.txt**: `ALIAS=#RRGGBB` per line. `#` lines are comments.
- **gridfab.json**: Optional config with `grid.width`, `grid.height`, `export.scales`

## Testing

Tests go in `tests/` using pytest. Fixtures (sample grid/palette files) go in `tests/fixtures/`.

## License

AGPLv3. See LICENSE.md.
