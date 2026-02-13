# core/ — Data Structures

Pure data structures and file I/O. No rendering, no CLI logic.

## Modules

- **`grid.py`** — `Grid` class: load/save grid.txt, get/set cells, fill, flood fill, flip, snapshot/restore
- **`palette.py`** — `Palette` class: load/save palette.txt, resolve aliases to hex, validate alias rules

## Key Design Decisions

- Grid dimensions are inferred from the file (not hardcoded). The `gridfab.json` config provides defaults for new grids.
- Palette supports 1-2 char aliases per the spec. Case-insensitive duplicates are rejected.
- `resolve_grid()` on Palette converts an entire grid of raw values to hex colors for rendering.
- `TRANSPARENT = "."` is defined here and used everywhere.
