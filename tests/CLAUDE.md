# tests/ — Test Suite

pytest-based tests for the GridFab package.

## Structure

- **`fixtures/`** — Sample grid.txt and palette.txt files used by tests
- **`test_grid.py`** — Grid load/save, manipulation, bounds checking
- **`test_palette.py`** — Palette load/save, alias validation, resolution
- **`test_commands.py`** — CLI command functions with valid and invalid inputs
- **`test_render.py`** — Image rendering output verification

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

## Conventions

- Use `tmp_path` fixture for test directories (pytest auto-cleanup)
- Test both happy paths and error cases (check error messages)
- Fixture files in `fixtures/` should be minimal examples
