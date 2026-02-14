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

1. **Run the FULL test suite**: `python -m pytest -v` (not just the files you changed)
2. **Write tests first** when adding new features (TDD). At minimum, write automated tests before committing — manual tests supplement but don't replace automated ones
3. **Update CHANGELOG.md**: Add entries under `[Unreleased]` using Keep a Changelog categories (Added, Changed, Deprecated, Removed, Fixed, Security)
4. **Update INSTRUCTIONS.md**: If any user-facing behavior changed (CLI commands, GUI features, file formats, config options), reflect it in INSTRUCTIONS.md — including the suggested LLM prompt section if CLI commands changed
5. **Update skills**: If CLI commands changed, update `skills/gridfab-create/SKILL.md` (end-user skill) to match
6. **Commit incrementally**: One commit per feature/fix, not one big commit at the end

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

## Testing

- Tests go in `tests/` using pytest with `tmp_path` fixtures (no filesystem mocking)
- Shared fixtures are in `tests/conftest.py` (`sprite_dir`, `sprite_dir_with_config`, `sample_grid`, etc.)
- Test both happy paths and error cases — check error messages with `pytest.raises(ValueError, match="...")`
- The test plan is in `.claude/plans/` — consult it for coverage goals and conventions
- Run coverage with: `python -m pytest --cov=gridfab --cov-report=term-missing`

## Code Style

- Follow existing patterns in the codebase
- Don't add docstrings, comments, or type annotations to code you didn't change
- Keep functions small and focused
- Fail loudly with clear error messages including line numbers and context — LLMs need good errors to self-correct

## Adding a New CLI Command

1. Add the command function in `src/gridfab/commands/edit.py` (or a new file if it's a new category)
2. Add argparse subcommand + dispatch in `src/gridfab/cli.py`
3. Write tests in `tests/test_commands.py`
4. Update the CLI docstring at the top of `cli.py`
5. Update INSTRUCTIONS.md (reference section + LLM prompt section)
6. Update `skills/gridfab-create/SKILL.md` command table and examples

## Palette Alias Rules

Aliases are 1-2 characters, case-sensitive, no case-insensitive duplicates, extended ASCII only, cannot start with `#`. `.` is reserved for transparent.

## Pull Request Process

1. Create a branch for your change
2. Make focused commits with clear messages
3. Ensure all tests pass
4. Update CHANGELOG.md and INSTRUCTIONS.md as needed
5. Submit PR with a clear description
