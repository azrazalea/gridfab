"""Edit commands: row, rows, fill, rect — modify grid.txt contents."""

import re
from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette, validate_hex_color
from gridfab.core.animation import resolve_grid_path

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _load(directory: Path, frame: int | None = None) -> tuple[Grid, Palette, Path]:
    """Load grid and palette from a sprite directory.

    Returns the resolved grid path so callers save to the same file.
    """
    palette_path = directory / "palette.txt"
    grid_path = resolve_grid_path(directory, frame)
    grid = Grid.load(grid_path, palette_path=palette_path)
    palette = Palette.load(palette_path)
    return grid, palette, grid_path


def _resolve_hex(value: str, palette: Palette, palette_path: Path) -> str:
    """If value is a hex color, resolve to an alias (reusing or generating).

    Returns the alias. Saves palette if a new alias was added.
    """
    if not _HEX_COLOR_RE.match(value):
        return value

    validate_hex_color(value)
    upper = value.upper()

    # Check if color already in palette (reverse lookup)
    for alias, color in palette.entries.items():
        if color is not None and color.upper() == upper:
            return alias

    # Generate a new alias
    alias = palette.next_available_alias()
    palette.entries[alias] = upper
    palette.save(palette_path)
    return alias


def _validate_values(values: list[str], palette: Palette, palette_path: Path) -> list[str]:
    """Validate values, auto-converting hex colors to aliases. Returns resolved list."""
    resolved = []
    for i, v in enumerate(values):
        v = _resolve_hex(v, palette, palette_path)
        palette.resolve(v, f"position {i}")
        resolved.append(v)
    return resolved


def _resolve_color(color: str, palette: Palette, palette_path: Path, context: str) -> str:
    """Resolve a single color value, auto-converting hex to alias."""
    color = _resolve_hex(color, palette, palette_path)
    palette.resolve(color, context)
    return color


def cmd_row(directory: Path, row_num: int, values: list[str], frame: int | None = None) -> None:
    """Replace a single row in the grid."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"

    if len(values) != grid.width:
        raise ValueError(
            f"expected {grid.width} values for row, got {len(values)}"
        )

    values = _validate_values(values, palette, palette_path)
    grid.set_row(row_num, values)
    grid.save(grid_path)
    print(f"Row {row_num} updated.")


def cmd_rows(directory: Path, start: int, end: int, values: list[str], frame: int | None = None) -> None:
    """Replace a range of rows (inclusive) in the grid."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"

    num_rows = end - start + 1
    expected = num_rows * grid.width
    if len(values) != expected:
        raise ValueError(
            f"expected {expected} values for {num_rows} rows "
            f"({start}-{end}), got {len(values)}"
        )

    values = _validate_values(values, palette, palette_path)

    for i in range(num_rows):
        row_values = values[i * grid.width : (i + 1) * grid.width]
        grid.set_row(start + i, row_values)

    grid.save(grid_path)
    print(f"Rows {start}-{end} updated.")


def cmd_fill(directory: Path, row: int, col_start: int, col_end: int, color: str, frame: int | None = None) -> None:
    """Fill a horizontal span in a single row."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"
    color = _resolve_color(color, palette, palette_path, "fill color")
    grid.fill_row(row, col_start, col_end, color)
    grid.save(grid_path)
    print(f"Row {row}, cols {col_start}-{col_end} filled with {color}.")


def cmd_rect(
    directory: Path, r0: int, c0: int, r1: int, c1: int, color: str, frame: int | None = None
) -> None:
    """Fill a rectangular region with one color."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"
    color = _resolve_color(color, palette, palette_path, "rect color")
    grid.fill_rect(r0, c0, r1, c1, color)
    grid.save(grid_path)
    print(f"Rect ({r0},{c0})-({r1},{c1}) filled with {color}.")


def cmd_clear(directory: Path, frame: int | None = None) -> None:
    """Reset all grid cells to transparent, preserving dimensions."""
    grid, _palette, grid_path = _load(directory, frame)
    for r in range(grid.height):
        for c in range(grid.width):
            grid.data[r][c] = "."
    grid.save(grid_path)
    print(f"Grid cleared ({grid.width}x{grid.height}, all transparent).")


def cmd_pixel(directory: Path, row: int, col: int, color: str, frame: int | None = None) -> None:
    """Set a single pixel by coordinate."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"
    color = _resolve_color(color, palette, palette_path, "pixel color")
    grid.set(row, col, color)
    grid.save(grid_path)
    print(f"Pixel ({row},{col}) set to {color}.")


def cmd_pixels(directory: Path, specs: list[str], frame: int | None = None) -> None:
    """Set multiple pixels from comma-separated triplets: row,col,color."""
    grid, palette, grid_path = _load(directory, frame)
    palette_path = directory / "palette.txt"

    placements = []
    for i, spec in enumerate(specs):
        parts = spec.split(",")
        if len(parts) != 3:
            raise ValueError(
                f"pixel spec #{i + 1} '{spec}': expected row,col,color "
                f"(3 comma-separated values), got {len(parts)}"
            )
        try:
            row = int(parts[0])
        except ValueError:
            raise ValueError(f"pixel spec #{i + 1} '{spec}': row must be integer")
        try:
            col = int(parts[1])
        except ValueError:
            raise ValueError(f"pixel spec #{i + 1} '{spec}': col must be integer")
        color = parts[2]
        color = _resolve_color(color, palette, palette_path, f"pixel spec #{i + 1}")
        placements.append((row, col, color))

    for row, col, color in placements:
        grid.set(row, col, color)

    grid.save(grid_path)
    print(f"{len(placements)} pixel(s) set.")
