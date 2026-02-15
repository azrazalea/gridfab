"""Tileset image loading and tile-level access."""

from pathlib import Path
from PIL import Image, ImageDraw


class TilesetNavigator:
    """Loads a tileset image and provides tile-level access."""

    def __init__(self, tileset_path: Path, tile_size: int = 32, bg_color: tuple | None = None):
        self.path = tileset_path
        self.tile_size = tile_size
        self.img = Image.open(tileset_path).convert("RGBA")
        self.cols = self.img.width // tile_size
        self.rows = self.img.height // tile_size
        self.empty_tiles: set[tuple[int, int]] = set()
        self._detect_empty(bg_color)

    def _detect_empty(self, bg_color: tuple | None = None):
        """Detect tiles that are fully transparent or match a specified background color.

        Only flags all-transparent tiles by default. Solid-color tiles are NOT
        auto-flagged because they could be valid sprites (plain walls, fills, etc).
        Users can mark additional tiles as empty with the Delete key.
        If bg_color is provided (e.g. (255,255,255) for white), tiles that are
        entirely that color are also flagged as empty.
        """
        ts = self.tile_size
        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.img.crop((c * ts, r * ts, (c + 1) * ts, (r + 1) * ts))
                pixels = list(tile.getdata())
                # All fully transparent
                if all(p[3] == 0 for p in pixels):
                    self.empty_tiles.add((r, c))
                # All match specified background color
                elif bg_color and all(p[:3] == bg_color[:3] for p in pixels):
                    self.empty_tiles.add((r, c))

    def get_tile_image(self, row: int, col: int, tiles_x: int = 1, tiles_y: int = 1) -> Image.Image:
        ts = self.tile_size
        return self.img.crop((col * ts, row * ts, (col + tiles_x) * ts, (row + tiles_y) * ts))

    def get_context_image(self, row: int, col: int, tiles_x: int = 1, tiles_y: int = 1,
                          radius: int = 3) -> tuple[Image.Image, tuple[int, int, int, int]]:
        """Get neighborhood around a tile selection with a highlight border."""
        ts = self.tile_size
        r0 = max(0, row - radius)
        c0 = max(0, col - radius)
        r1 = min(self.rows, row + tiles_y + radius)
        c1 = min(self.cols, col + tiles_x + radius)

        context = self.img.crop((c0 * ts, r0 * ts, c1 * ts, r1 * ts)).copy()

        # Draw highlight rectangle around current selection
        draw = ImageDraw.Draw(context)
        sel_x0 = (col - c0) * ts
        sel_y0 = (row - r0) * ts
        sel_x1 = sel_x0 + tiles_x * ts - 1
        sel_y1 = sel_y0 + tiles_y * ts - 1
        for offset in range(2):
            draw.rectangle(
                [sel_x0 - offset, sel_y0 - offset, sel_x1 + offset, sel_y1 + offset],
                outline=(255, 0, 0, 255),
            )

        return context, (r0, c0, r1, c1)

    def total_tiles(self) -> int:
        return self.rows * self.cols

    def non_empty_count(self) -> int:
        return self.total_tiles() - len(self.empty_tiles)
