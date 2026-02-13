"""The 'export' command: export PNGs at multiple scales with true transparency."""

import json
from pathlib import Path

from gridfab.core.grid import Grid, load_config
from gridfab.core.palette import Palette
from gridfab.render.export import render_export


def cmd_export(directory: Path) -> None:
    """Export final PNGs at configured scales with true transparency."""
    grid = Grid.load(directory / "grid.txt")
    palette = Palette.load(directory / "palette.txt")
    colors = palette.resolve_grid(grid.data)

    config = load_config(directory)
    scales = config.get("export", {}).get("scales", [1, 4, 8, 16])

    for scale in scales:
        img = render_export(colors, grid.width, grid.height, scale)
        if scale == 1:
            name = "output.png"
        else:
            name = f"output_{scale}x.png"
        output = directory / name
        img.save(str(output))
        w = grid.width * scale
        h = grid.height * scale
        print(f"Exported {output} ({w}x{h})")


def cmd_palette(directory: Path) -> None:
    """Display the current palette."""
    palette_path = directory / "palette.txt"
    if not palette_path.exists():
        raise FileNotFoundError(
            f"No palette.txt found in {directory} — run 'gridfab init' first"
        )

    palette = Palette.load(palette_path)
    entries = palette.colors

    if not entries:
        print("Palette is empty. Add entries to palette.txt: ALIAS=#RRGGBB")
        return

    print("Current palette:")
    for alias, color in sorted(entries.items()):
        print(f"  {alias} = {color if color else 'transparent'}")
