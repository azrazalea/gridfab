"""The 'render' command: generate preview.png with checkerboard background."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.core.animation import resolve_grid_path, resolve_palette_path
from gridfab.render.preview import render_preview, PREVIEW_SCALE


def cmd_render(directory: Path, frame: int | None = None) -> None:
    """Render a preview image with checkerboard transparency background."""
    grid_path = resolve_grid_path(directory, frame)
    palette_path = resolve_palette_path(directory)
    grid = Grid.load(grid_path, palette_path=palette_path)
    palette = Palette.load(palette_path)
    colors = palette.resolve_grid(grid.data)

    img = render_preview(colors, grid.width, grid.height, PREVIEW_SCALE)
    output = directory / "preview.png"
    img.save(str(output))

    print(f"Rendered {output} ({grid.width * PREVIEW_SCALE}x{grid.height * PREVIEW_SCALE})")
