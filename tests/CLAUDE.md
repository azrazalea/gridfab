# tests/ — Test Suite

pytest-based tests for the GridFab package.

## Structure

- **`conftest.py`** — Shared fixtures: `sprite_dir`, `sprite_dir_with_config`, `sample_grid`, `sample_palette`, `sample_sprite`
- **`fixtures/`** — Sample grid.txt and palette.txt files used by tests
- **`test_grid.py`** — Grid load/save, manipulation, auto-repair, bounds checking, config loading
- **`test_palette.py`** — Palette load/save, alias validation, resolution
- **`test_commands.py`** — CLI command functions: init, row, rows, fill, rect, pixel, pixels, clear
- **`test_gui.py`** — GUI pure functions: checker_color, cell_display_color

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest -v                                      # all tests
python -m pytest --cov=gridfab --cov-report=term-missing # with coverage
```

## Conventions

- Use `tmp_path` fixture for test directories (pytest auto-cleanup)
- Use `sprite_dir` from conftest for command tests (4x4 blank grid + R/B/G palette)
- Test both happy paths and error cases (check error messages with `match=`)
- Write tests first when adding new features
- Always run the full suite before committing, not just changed files
