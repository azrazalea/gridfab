"""Edit commands: row, rows, fill, rect — modify grid.txt contents."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette


def _load(directory: Path) -> tuple[Grid, Palette]:
    """Load grid and palette from a sprite directory."""
    grid = Grid.load(directory / "grid.txt")
    palette = Palette.load(directory / "palette.txt")
    return grid, palette


def _validate_values(values: list[str], palette: Palette) -> None:
    """Validate that all values are resolvable palette entries."""
    for i, v in enumerate(values):
        palette.resolve(v, f"position {i}")


def cmd_row(directory: Path, row_num: int, values: list[str]) -> None:
    """Replace a single row in the grid."""
    grid, palette = _load(directory)

    if len(values) != grid.width:
        raise ValueError(
            f"expected {grid.width} values for row, got {len(values)}"
        )

    _validate_values(values, palette)
    grid.set_row(row_num, values)
    grid.save(directory / "grid.txt")
    print(f"Row {row_num} updated.")


def cmd_rows(directory: Path, start: int, end: int, values: list[str]) -> None:
    """Replace a range of rows (inclusive) in the grid."""
    grid, palette = _load(directory)

    num_rows = end - start + 1
    expected = num_rows * grid.width
    if len(values) != expected:
        raise ValueError(
            f"expected {expected} values for {num_rows} rows "
            f"({start}-{end}), got {len(values)}"
        )

    _validate_values(values, palette)

    for i in range(num_rows):
        row_values = values[i * grid.width : (i + 1) * grid.width]
        grid.set_row(start + i, row_values)

    grid.save(directory / "grid.txt")
    print(f"Rows {start}-{end} updated.")


def cmd_fill(directory: Path, row: int, col_start: int, col_end: int, color: str) -> None:
    """Fill a horizontal span in a single row."""
    grid, palette = _load(directory)
    palette.resolve(color, "fill color")
    grid.fill_row(row, col_start, col_end, color)
    grid.save(directory / "grid.txt")
    print(f"Row {row}, cols {col_start}-{col_end} filled with {color}.")


def cmd_rect(
    directory: Path, r0: int, c0: int, r1: int, c1: int, color: str
) -> None:
    """Fill a rectangular region with one color."""
    grid, palette = _load(directory)
    palette.resolve(color, "rect color")
    grid.fill_rect(r0, c0, r1, c1, color)
    grid.save(directory / "grid.txt")
    print(f"Rect ({r0},{c0})-({r1},{c1}) filled with {color}.")


def cmd_pixel(directory: Path, row: int, col: int, color: str) -> None:
    """Set a single pixel by coordinate."""
    grid, palette = _load(directory)
    palette.resolve(color, "pixel color")
    grid.set(row, col, color)
    grid.save(directory / "grid.txt")
    print(f"Pixel ({row},{col}) set to {color}.")


def cmd_pixels(directory: Path, specs: list[str]) -> None:
    """Set multiple pixels from comma-separated triplets: row,col,color."""
    grid, palette = _load(directory)

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
        palette.resolve(color, f"pixel spec #{i + 1}")
        placements.append((row, col, color))

    for row, col, color in placements:
        grid.set(row, col, color)

    grid.save(directory / "grid.txt")
    print(f"{len(placements)} pixel(s) set.")
