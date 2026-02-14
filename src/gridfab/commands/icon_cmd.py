"""The 'icon' command: export a .ico file with multiple icon sizes."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.render.ico import render_ico, DEFAULT_ICO_SIZES


def cmd_icon(directory: Path) -> None:
    """Export an icon.ico file from a square sprite."""
    grid = Grid.load(directory / "grid.txt")
    palette = Palette.load(directory / "palette.txt")
    colors = palette.resolve_grid(grid.data)

    images = render_ico(colors, grid.width, grid.height)

    path = directory / "icon.ico"
    # ICO saving: use the largest image and let Pillow generate all sizes
    ico_sizes = [(s, s) for s in DEFAULT_ICO_SIZES]
    images[-1].save(str(path), format="ICO", sizes=ico_sizes)

    sizes_str = ", ".join(str(s) for s in DEFAULT_ICO_SIZES)
    print(f"Exported icon.ico ({sizes_str})")
