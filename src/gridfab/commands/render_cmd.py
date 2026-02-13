"""The 'render' command: generate preview.png with checkerboard background."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.render.preview import render_preview, PREVIEW_SCALE


def cmd_render(directory: Path) -> None:
    """Render a preview image with checkerboard transparency background."""
    grid = Grid.load(directory / "grid.txt")
    palette = Palette.load(directory / "palette.txt")
    colors = palette.resolve_grid(grid.data)

    img = render_preview(colors, grid.width, grid.height, PREVIEW_SCALE)
    output = directory / "preview.png"
    img.save(str(output))

    size = max(grid.width, grid.height) * PREVIEW_SCALE
    print(f"Rendered {output} ({grid.width * PREVIEW_SCALE}x{grid.height * PREVIEW_SCALE})")
