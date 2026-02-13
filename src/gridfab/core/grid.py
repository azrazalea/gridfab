"""Grid: the central data structure for GridFab sprites.

A Grid is a 2D array of string values where each cell is either:
- "." for transparent
- A 1-2 character palette alias (e.g. "R", "SK")
- An inline "#RRGGBB" hex color
"""

from __future__ import annotations

import json
from pathlib import Path

TRANSPARENT = "."

DEFAULT_WIDTH = 32
DEFAULT_HEIGHT = 32


def load_config(directory: Path) -> dict:
    """Load gridfab.json config from a sprite directory, or return defaults."""
    config_path = directory / "gridfab.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def get_grid_dimensions(directory: Path) -> tuple[int, int]:
    """Get grid dimensions from config, or return defaults."""
    config = load_config(directory)
    grid_config = config.get("grid", {})
    width = grid_config.get("width", DEFAULT_WIDTH)
    height = grid_config.get("height", DEFAULT_HEIGHT)
    return width, height


class Grid:
    """A 2D grid of palette aliases or hex colors.

    The grid is stored as a list of rows, where each row is a list of
    string values. This matches the grid.txt file format exactly.
    """

    def __init__(self, width: int, height: int, data: list[list[str]]):
        self.width = width
        self.height = height
        self.data = data

    @classmethod
    def blank(cls, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> Grid:
        """Create a blank (all transparent) grid."""
        data = [[TRANSPARENT] * width for _ in range(height)]
        return cls(width, height, data)

    @classmethod
    def load(cls, path: Path) -> Grid:
        """Load a grid from a text file.

        The file format is one row per line, with space-separated values.
        Grid dimensions are inferred from the file contents.
        """
        if not path.exists():
            raise FileNotFoundError(f"{path} not found — run 'gridfab init' first")

        rows: list[list[str]] = []
        with open(path) as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.rstrip("\n")
                if line.strip() == "":
                    raise ValueError(f"{path}:{line_num}: unexpected blank line")
                values = line.split()
                rows.append(values)

        if not rows:
            raise ValueError(f"{path}: file is empty")

        width = len(rows[0])
        for i, row in enumerate(rows):
            if len(row) != width:
                raise ValueError(
                    f"{path}:{i + 1}: expected {width} values "
                    f"(matching row 1), got {len(row)}"
                )

        return cls(width, len(rows), rows)

    def save(self, path: Path) -> None:
        """Save the grid to a text file."""
        with open(path, "w", newline="\n") as f:
            for row in self.data:
                f.write(" ".join(row) + "\n")

    def get(self, row: int, col: int) -> str:
        """Get the value at (row, col)."""
        self._check_bounds(row, col)
        return self.data[row][col]

    def set(self, row: int, col: int, value: str) -> None:
        """Set the value at (row, col)."""
        self._check_bounds(row, col)
        self.data[row][col] = value

    def set_row(self, row: int, values: list[str]) -> None:
        """Replace an entire row with new values."""
        self._check_row(row)
        if len(values) != self.width:
            raise ValueError(
                f"expected {self.width} values for row, got {len(values)}"
            )
        self.data[row] = list(values)

    def fill_row(self, row: int, col_start: int, col_end: int, value: str) -> None:
        """Fill a horizontal span in a single row."""
        self._check_row(row)
        self._check_col(col_start)
        self._check_col(col_end)
        if col_end < col_start:
            raise ValueError(
                f"col_end ({col_end}) must be >= col_start ({col_start})"
            )
        for c in range(col_start, col_end + 1):
            self.data[row][c] = value

    def fill_rect(self, r0: int, c0: int, r1: int, c1: int, value: str) -> None:
        """Fill a rectangular region with a single value."""
        self._check_row(r0)
        self._check_row(r1)
        self._check_col(c0)
        self._check_col(c1)
        if r1 < r0:
            raise ValueError(f"r1 ({r1}) must be >= r0 ({r0})")
        if c1 < c0:
            raise ValueError(f"c1 ({c1}) must be >= c0 ({c0})")
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                self.data[r][c] = value

    def flood_fill(self, row: int, col: int, value: str) -> None:
        """4-connected flood fill starting from (row, col).

        Fills all contiguous cells matching the target alias with the new value.
        """
        self._check_bounds(row, col)
        target = self.data[row][col]
        if target == value:
            return
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if r < 0 or r >= self.height or c < 0 or c >= self.width:
                continue
            if self.data[r][c] != target:
                continue
            self.data[r][c] = value
            stack.extend([(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)])

    def flip_horizontal(self) -> None:
        """Flip the grid left-right."""
        for row in self.data:
            row.reverse()

    def flip_vertical(self) -> None:
        """Flip the grid top-bottom."""
        self.data.reverse()

    def snapshot(self) -> list[list[str]]:
        """Return a deep copy of the grid data (for undo)."""
        return [row[:] for row in self.data]

    def restore(self, snapshot: list[list[str]]) -> None:
        """Restore grid data from a snapshot."""
        self.data = [row[:] for row in snapshot]

    def _check_bounds(self, row: int, col: int) -> None:
        self._check_row(row)
        self._check_col(col)

    def _check_row(self, row: int) -> None:
        if row < 0 or row >= self.height:
            raise ValueError(
                f"row must be 0-{self.height - 1}, got {row}"
            )

    def _check_col(self, col: int) -> None:
        if col < 0 or col >= self.width:
            raise ValueError(
                f"col must be 0-{self.width - 1}, got {col}"
            )

    def __repr__(self) -> str:
        return f"Grid({self.width}x{self.height})"
