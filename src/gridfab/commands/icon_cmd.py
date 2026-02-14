"""The 'icon' command: export icon files (.ico + .icns) with multiple sizes."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.render.ico import render_ico, DEFAULT_ICO_SIZES


def cmd_icon(directory: Path) -> None:
    """Export icon.ico and icon.icns from a square sprite."""
    grid = Grid.load(directory / "grid.txt")
    palette = Palette.load(directory / "palette.txt")
    colors = palette.resolve_grid(grid.data)

    images = render_ico(colors, grid.width, grid.height)

    sizes_str = ", ".join(str(s) for s in DEFAULT_ICO_SIZES)

    # ICO: use the largest image and let Pillow generate all sizes
    ico_path = directory / "icon.ico"
    ico_sizes = [(s, s) for s in DEFAULT_ICO_SIZES]
    images[-1].save(str(ico_path), format="ICO", sizes=ico_sizes)

    # ICNS: same approach for macOS
    icns_path = directory / "icon.icns"
    icns_sizes = [(s, s) for s in DEFAULT_ICO_SIZES]
    images[-1].save(str(icns_path), format="ICNS", sizes=icns_sizes)

    print(f"Exported icon.ico + icon.icns ({sizes_str})")
