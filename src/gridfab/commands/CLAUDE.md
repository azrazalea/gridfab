# commands/ — CLI Command Implementations

Each module contains functions called by `cli.py`. Commands take a `Path` directory argument.

## Modules

- **`init.py`** — `cmd_init()`: Creates grid.txt, palette.txt, gridfab.json
- **`edit.py`** — `cmd_row()`, `cmd_rows()`, `cmd_fill()`, `cmd_rect()`: Modify grid contents
- **`render_cmd.py`** — `cmd_render()`: Generate preview.png with checkerboard
- **`export_cmd.py`** — `cmd_export()`, `cmd_palette()`: Export PNGs and display palette

## Conventions

- All commands load Grid and Palette from the directory, do their work, save back
- Validation happens before modification (fail fast)
- Success prints a human-readable confirmation message to stdout
- Errors raise ValueError/FileNotFoundError, caught by cli.py
