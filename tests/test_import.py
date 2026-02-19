"""Tests for the import command: image → grid.txt + palette.txt conversion."""

import json

import pytest
from pathlib import Path
from PIL import Image

from gridfab.commands.import_cmd import (
    generate_alias_sequence,
    image_to_grid_and_palette,
    import_single,
    import_tilesheet,
    cmd_import,
    save_sprite,
)


# ---------------------------------------------------------------------------
# Helpers to create test images
# ---------------------------------------------------------------------------

def make_solid_image(w, h, color):
    """Create a solid-color RGBA image."""
    img = Image.new("RGBA", (w, h), color)
    return img


def make_transparent_image(w, h):
    """Create a fully transparent image."""
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def make_multicolor_image():
    """Create a 4x4 image with 4 colors in quadrants."""
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    # Top-left: red
    for r in range(2):
        for c in range(2):
            img.putpixel((c, r), (255, 0, 0, 255))
    # Top-right: green
    for r in range(2):
        for c in range(2, 4):
            img.putpixel((c, r), (0, 255, 0, 255))
    # Bottom-left: blue
    for r in range(2, 4):
        for c in range(2):
            img.putpixel((c, r), (0, 0, 255, 255))
    # Bottom-right: transparent (already set)
    return img


def make_tilesheet(tile_w, tile_h, tiles):
    """Create a tilesheet image from a list of tile specs.

    tiles: list of (col, row, color_rgba) — each tile filled with that color.
    Returns a sheet large enough to fit all tiles.
    """
    max_col = max(col for col, row, _ in tiles) + 1
    max_row = max(row for col, row, _ in tiles) + 1
    img = Image.new("RGBA", (max_col * tile_w, max_row * tile_h), (0, 0, 0, 0))
    for col, row, color in tiles:
        for y in range(row * tile_h, (row + 1) * tile_h):
            for x in range(col * tile_w, (col + 1) * tile_w):
                img.putpixel((x, y), color)
    return img


# ---------------------------------------------------------------------------
# Alias generation
# ---------------------------------------------------------------------------

class TestAliasGeneration:
    def test_starts_with_uppercase(self):
        seq = generate_alias_sequence()
        assert next(seq) == "A"
        assert next(seq) == "B"

    def test_uppercase_then_digits(self):
        seq = generate_alias_sequence()
        aliases = [next(seq) for _ in range(36)]
        assert aliases[0] == "A"
        assert aliases[25] == "Z"
        assert aliases[26] == "0"
        assert aliases[35] == "9"

    def test_two_char_after_singles(self):
        seq = generate_alias_sequence()
        # Skip 26 letters + 10 digits = 36 single-char
        for _ in range(36):
            next(seq)
        assert next(seq) == "AA"
        assert next(seq) == "AB"

    def test_no_case_collisions(self):
        """All aliases should be unique even case-insensitively."""
        seq = generate_alias_sequence()
        seen = set()
        for _ in range(712):
            alias = next(seq)
            lower = alias.lower()
            assert lower not in seen, f"Case collision: {alias}"
            seen.add(lower)

    def test_total_count(self):
        """Should produce exactly 712 aliases (26 + 10 + 676)."""
        seq = generate_alias_sequence()
        aliases = []
        for _ in range(712):
            aliases.append(next(seq))
        assert len(aliases) == 712


# ---------------------------------------------------------------------------
# image_to_grid_and_palette
# ---------------------------------------------------------------------------

class TestImageToGridAndPalette:
    def test_solid_red(self):
        img = make_solid_image(4, 4, (255, 0, 0, 255))
        grid_data, palette_entries = image_to_grid_and_palette(img)
        assert len(grid_data) == 4
        assert len(grid_data[0]) == 4
        # All cells should have the same alias
        alias = grid_data[0][0]
        assert alias != "."
        for row in grid_data:
            for cell in row:
                assert cell == alias
        # Palette should have exactly one color
        assert len(palette_entries) == 1
        assert palette_entries[alias] == "#FF0000"

    def test_fully_transparent(self):
        img = make_transparent_image(4, 4)
        grid_data, palette_entries = image_to_grid_and_palette(img)
        for row in grid_data:
            for cell in row:
                assert cell == "."
        assert len(palette_entries) == 0

    def test_multicolor(self):
        img = make_multicolor_image()
        grid_data, palette_entries = image_to_grid_and_palette(img)
        # Should have 3 colors (red, green, blue) + transparent
        assert len(palette_entries) == 3
        # Top-left should be same alias
        assert grid_data[0][0] == grid_data[0][1] == grid_data[1][0] == grid_data[1][1]
        # Bottom-right should be transparent
        assert grid_data[2][2] == "."
        assert grid_data[3][3] == "."

    def test_alpha_threshold(self):
        """Pixels with alpha < threshold should be transparent."""
        img = Image.new("RGBA", (2, 2), (255, 0, 0, 127))
        # Default threshold is 128, so alpha=127 → transparent
        grid_data, palette_entries = image_to_grid_and_palette(img, alpha_threshold=128)
        for row in grid_data:
            for cell in row:
                assert cell == "."

        # With threshold=127, alpha=127 → opaque
        grid_data2, palette_entries2 = image_to_grid_and_palette(img, alpha_threshold=127)
        assert grid_data2[0][0] != "."
        assert len(palette_entries2) == 1

    def test_existing_colors_reused(self):
        """When existing_colors is provided, aliases should be reused."""
        img = make_solid_image(2, 2, (255, 0, 0, 255))
        existing = {"#FF0000": "R"}
        grid_data, palette_entries = image_to_grid_and_palette(
            img, existing_colors=existing,
        )
        for row in grid_data:
            for cell in row:
                assert cell == "R"
        assert palette_entries["R"] == "#FF0000"

    def test_rgb_mode_image(self):
        """Should handle RGB images (no alpha channel) — all pixels opaque."""
        img = Image.new("RGB", (2, 2), (0, 128, 255))
        grid_data, palette_entries = image_to_grid_and_palette(img)
        assert grid_data[0][0] != "."
        assert len(palette_entries) == 1
        assert list(palette_entries.values())[0] == "#0080FF"


# ---------------------------------------------------------------------------
# save_sprite
# ---------------------------------------------------------------------------

class TestSaveSprite:
    def test_creates_files(self, tmp_path):
        out = tmp_path / "my_sprite"
        grid_data = [["A", "."], [".", "A"]]
        palette_entries = {"A": "#FF0000"}
        save_sprite(grid_data, palette_entries, out, width=2, height=2)

        assert (out / "grid.txt").exists()
        assert (out / "palette.txt").exists()
        assert (out / "gridfab.json").exists()

    def test_grid_content(self, tmp_path):
        out = tmp_path / "sprite"
        grid_data = [["A", "B"], [".", "A"]]
        palette_entries = {"A": "#FF0000", "B": "#00FF00"}
        save_sprite(grid_data, palette_entries, out, width=2, height=2)

        content = (out / "grid.txt").read_text()
        assert content == "A. B.\n.. A.\n"

    def test_palette_content(self, tmp_path):
        out = tmp_path / "sprite"
        grid_data = [["A", "."]]
        palette_entries = {"A": "#FF0000"}
        save_sprite(grid_data, palette_entries, out, width=2, height=1)

        content = (out / "palette.txt").read_text()
        assert "A=#FF0000" in content

    def test_config_dimensions(self, tmp_path):
        out = tmp_path / "sprite"
        grid_data = [["A"] * 8 for _ in range(6)]
        palette_entries = {"A": "#FF0000"}
        save_sprite(grid_data, palette_entries, out, width=8, height=6)

        config = json.loads((out / "gridfab.json").read_text())
        assert config["grid"]["width"] == 8
        assert config["grid"]["height"] == 6

    def test_metadata_written(self, tmp_path):
        out = tmp_path / "sprite"
        grid_data = [["A"]]
        palette_entries = {"A": "#FF0000"}
        metadata = {"description": "A red pixel", "tags": ["test"]}
        save_sprite(grid_data, palette_entries, out, width=1, height=1,
                     metadata=metadata)

        meta = json.loads((out / "metadata.json").read_text())
        assert meta["description"] == "A red pixel"

    def test_no_metadata_file_without_metadata(self, tmp_path):
        out = tmp_path / "sprite"
        grid_data = [["A"]]
        palette_entries = {"A": "#FF0000"}
        save_sprite(grid_data, palette_entries, out, width=1, height=1)

        assert not (out / "metadata.json").exists()


# ---------------------------------------------------------------------------
# import_single (mode 1 & 2)
# ---------------------------------------------------------------------------

class TestImportSingle:
    def test_single_image(self, tmp_path):
        img_path = tmp_path / "test.png"
        img = make_solid_image(4, 4, (255, 0, 0, 255))
        img.save(str(img_path))

        out = tmp_path / "my_sprite"
        import_single(img_path, out)

        assert (out / "grid.txt").exists()
        assert (out / "palette.txt").exists()
        assert (out / "gridfab.json").exists()

        # Verify grid dimensions
        config = json.loads((out / "gridfab.json").read_text())
        assert config["grid"]["width"] == 4
        assert config["grid"]["height"] == 4

    def test_with_transparency(self, tmp_path):
        img_path = tmp_path / "test.png"
        img = make_multicolor_image()
        img.save(str(img_path))

        out = tmp_path / "sprite"
        import_single(img_path, out)

        content = (out / "grid.txt").read_text()
        lines = content.strip().split("\n")
        # Bottom-right 2x2 should be transparent (padded as "..")
        last_row = lines[3].split()
        assert last_row[2] == ".."
        assert last_row[3] == ".."

    def test_output_dir_already_has_grid(self, tmp_path):
        """Should raise if output dir already contains grid.txt."""
        img_path = tmp_path / "test.png"
        make_solid_image(2, 2, (255, 0, 0, 255)).save(str(img_path))

        out = tmp_path / "existing"
        out.mkdir()
        (out / "grid.txt").write_text(". .\n. .\n")

        with pytest.raises(FileExistsError, match="grid.txt"):
            import_single(img_path, out)

    def test_image_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            import_single(tmp_path / "nope.png", tmp_path / "out")


# ---------------------------------------------------------------------------
# import_tilesheet (mode 3)
# ---------------------------------------------------------------------------

class TestImportTilesheet:
    def test_two_tile_sheet(self, tmp_path):
        """2x1 tilesheet with two different tiles."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),  # tile (0,0) = red
            (1, 0, (0, 0, 255, 255)),  # tile (1,0) = blue
        ])
        sheet.save(str(img_path))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out)

        assert (out / "tile_0_0" / "grid.txt").exists()
        assert (out / "tile_1_0" / "grid.txt").exists()

    def test_shared_palette(self, tmp_path):
        """All tiles in a tilesheet should share the same palette."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (1, 0, (0, 0, 255, 255)),
        ])
        sheet.save(str(img_path))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out)

        p1 = (out / "tile_0_0" / "palette.txt").read_text()
        p2 = (out / "tile_1_0" / "palette.txt").read_text()
        assert p1 == p2

    def test_skips_empty_tiles(self, tmp_path):
        """Fully transparent tiles should be skipped."""
        img_path = tmp_path / "sheet.png"
        # 2x2 tilesheet: only (0,0) has content
        sheet = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(4):
            for x in range(4):
                sheet.putpixel((x, y), (255, 0, 0, 255))
        sheet.save(str(img_path))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out)

        assert (out / "tile_0_0" / "grid.txt").exists()
        assert not (out / "tile_1_0").exists()
        assert not (out / "tile_0_1").exists()
        assert not (out / "tile_1_1").exists()

    def test_coordinate_naming(self, tmp_path):
        """Tile directories should be named tile_COL_ROW."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (2, 1, (0, 255, 0, 255)),
        ])
        sheet.save(str(img_path))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out)

        assert (out / "tile_0_0").is_dir()
        assert (out / "tile_2_1").is_dir()

    def test_with_index(self, tmp_path):
        """Tilesheet with index.json should use sprite names."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (1, 0, (0, 0, 255, 255)),
        ])
        sheet.save(str(img_path))

        index = {
            "tile_size": [4, 4],
            "columns": 2,
            "sprites": {
                "hero": {
                    "row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1,
                    "description": "The hero", "tags": ["player"],
                    "tile_type": "character",
                },
                "enemy": {
                    "row": 0, "col": 1, "tiles_x": 1, "tiles_y": 1,
                    "description": "An enemy", "tags": ["npc"],
                    "tile_type": "character",
                },
            },
        }
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out, index=index_path)

        assert (out / "hero" / "grid.txt").exists()
        assert (out / "enemy" / "grid.txt").exists()

    def test_index_metadata(self, tmp_path):
        """When using index, metadata.json should be created per sprite."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
        ])
        sheet.save(str(img_path))

        index = {
            "tile_size": [4, 4],
            "columns": 1,
            "sprites": {
                "hero": {
                    "row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1,
                    "description": "The hero", "tags": ["player"],
                    "tile_type": "character",
                },
            },
        }
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out, index=index_path)

        meta = json.loads((out / "hero" / "metadata.json").read_text())
        assert meta["description"] == "The hero"
        assert meta["tags"] == ["player"]
        assert meta["tile_type"] == "character"

    def test_index_fallback_to_coords(self, tmp_path):
        """Tiles not in index should use coordinate naming."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (1, 0, (0, 255, 0, 255)),
        ])
        sheet.save(str(img_path))

        # Index only covers (0,0)
        index = {
            "tile_size": [4, 4],
            "columns": 2,
            "sprites": {
                "hero": {
                    "row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1,
                    "description": "", "tags": [], "tile_type": "",
                },
            },
        }
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index))

        out = tmp_path / "output"
        import_tilesheet(img_path, 4, 4, out, index=index_path)

        assert (out / "hero").is_dir()
        assert (out / "tile_1_0").is_dir()

    def test_image_not_divisible_by_tile_size(self, tmp_path):
        """Should raise error if image dimensions aren't divisible by tile size."""
        img_path = tmp_path / "sheet.png"
        # 5x5 image with tile size 4x4
        Image.new("RGBA", (5, 5), (255, 0, 0, 255)).save(str(img_path))

        with pytest.raises(ValueError, match="not divisible"):
            import_tilesheet(img_path, 4, 4, tmp_path / "out")


# ---------------------------------------------------------------------------
# cmd_import (dispatcher)
# ---------------------------------------------------------------------------

class TestCmdImport:
    def test_single_mode(self, tmp_path):
        """No tile_size → single image mode."""
        img_path = tmp_path / "test.png"
        make_solid_image(4, 4, (0, 128, 255, 255)).save(str(img_path))

        out = tmp_path / "sprite"
        cmd_import(img_path, out)
        assert (out / "grid.txt").exists()

    def test_single_tile_mode(self, tmp_path):
        """tile_size + tile → extract single tile."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (1, 0, (0, 0, 255, 255)),
        ])
        sheet.save(str(img_path))

        out = tmp_path / "my_tile"
        cmd_import(img_path, out, tile_size=(4, 4), tile_pos=(1, 0))
        assert (out / "grid.txt").exists()
        # Verify it extracted the blue tile (col=1, row=0)
        from gridfab.core.grid import Grid
        from gridfab.core.palette import Palette
        grid = Grid.load(out / "grid.txt")
        palette = Palette.load(out / "palette.txt")
        color = palette.resolve(grid.data[0][0])
        assert color == "#0000FF"

    def test_single_tile_out_of_bounds(self, tmp_path):
        """Requesting a tile outside the image should raise error."""
        img_path = tmp_path / "sheet.png"
        make_solid_image(8, 4, (255, 0, 0, 255)).save(str(img_path))

        with pytest.raises(ValueError, match="out of bounds"):
            cmd_import(img_path, tmp_path / "out",
                       tile_size=(4, 4), tile_pos=(5, 0))

    def test_tilesheet_mode(self, tmp_path):
        """tile_size without tile → whole tilesheet mode."""
        img_path = tmp_path / "sheet.png"
        sheet = make_tilesheet(4, 4, [
            (0, 0, (255, 0, 0, 255)),
            (1, 0, (0, 0, 255, 255)),
        ])
        sheet.save(str(img_path))

        out = tmp_path / "output"
        cmd_import(img_path, out, tile_size=(4, 4))
        assert (out / "tile_0_0").is_dir()
        assert (out / "tile_1_0").is_dir()

    def test_default_output_from_image_name(self, tmp_path):
        """When output is None, derive directory name from image filename."""
        img_path = tmp_path / "hero_sprite.png"
        make_solid_image(4, 4, (255, 0, 0, 255)).save(str(img_path))

        cmd_import(img_path, None)
        out = img_path.parent / "hero_sprite"
        assert (out / "grid.txt").exists()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_1x1_image(self, tmp_path):
        """Single pixel image should work."""
        img_path = tmp_path / "pixel.png"
        make_solid_image(1, 1, (42, 42, 42, 255)).save(str(img_path))

        out = tmp_path / "sprite"
        import_single(img_path, out)

        content = (out / "grid.txt").read_text().strip()
        assert content != "."  # Should be a color alias, not transparent

    def test_many_unique_colors(self, tmp_path):
        """Image with many unique colors should get unique aliases."""
        img = Image.new("RGBA", (10, 10))
        # Put 100 different colors
        for y in range(10):
            for x in range(10):
                r = (x * 25) % 256
                g = (y * 25) % 256
                img.putpixel((x, y), (r, g, 128, 255))

        grid_data, palette_entries = image_to_grid_and_palette(img)

        # All aliases should be unique
        aliases = set()
        for row in grid_data:
            for cell in row:
                if cell != ".":
                    aliases.add(cell)

        # Number of palette entries should match number of unique aliases
        assert len(palette_entries) == len(aliases)
        # No duplicate hex values
        colors = list(palette_entries.values())
        assert len(colors) == len(set(colors))

    def test_palette_mode_image(self, tmp_path):
        """Should handle palette-mode (P) PNG images."""
        img = Image.new("P", (4, 4))
        img.putpalette([255, 0, 0] * 256)  # all red
        img_path = tmp_path / "palimg.png"
        img.save(str(img_path))

        out = tmp_path / "sprite"
        import_single(img_path, out)
        assert (out / "grid.txt").exists()


# ---------------------------------------------------------------------------
# Multi-format support
# ---------------------------------------------------------------------------

class TestMultiFormat:
    """Verify import works with non-PNG image formats."""

    def _import_and_verify(self, tmp_path, filename, fmt, color, has_alpha=True):
        """Save an image in the given format, import it, verify grid.txt."""
        img = make_solid_image(4, 4, color)
        img_path = tmp_path / filename
        img.save(str(img_path), format=fmt)

        out = tmp_path / "sprite"
        import_single(img_path, out)

        assert (out / "grid.txt").exists()
        assert (out / "palette.txt").exists()

        content = (out / "grid.txt").read_text().strip()
        lines = content.split("\n")
        assert len(lines) == 4
        for line in lines:
            vals = line.split()
            assert len(vals) == 4
            if has_alpha:
                assert all(v != "." for v in vals)

        return out

    def test_bmp_import(self, tmp_path):
        """BMP format should import successfully."""
        self._import_and_verify(
            tmp_path, "test.bmp", "BMP", (255, 0, 0, 255),
        )

    def test_gif_import(self, tmp_path):
        """GIF format should import successfully."""
        self._import_and_verify(
            tmp_path, "test.gif", "GIF", (255, 0, 0, 255),
        )

    def test_webp_import(self, tmp_path):
        """WebP format should import successfully."""
        self._import_and_verify(
            tmp_path, "test.webp", "WEBP", (255, 0, 0, 255),
        )

    def test_tiff_import(self, tmp_path):
        """TIFF format should import successfully."""
        self._import_and_verify(
            tmp_path, "test.tiff", "TIFF", (255, 0, 0, 255),
        )

    def test_jpeg_import(self, tmp_path):
        """JPEG format (no alpha) should import with all pixels opaque."""
        img = Image.new("RGB", (4, 4), (255, 0, 0))
        img_path = tmp_path / "test.jpg"
        img.save(str(img_path), format="JPEG")

        out = tmp_path / "sprite"
        import_single(img_path, out)

        assert (out / "grid.txt").exists()
        content = (out / "grid.txt").read_text().strip()
        lines = content.split("\n")
        assert len(lines) == 4
        for line in lines:
            vals = line.split()
            assert len(vals) == 4
            # All pixels should be opaque (no transparent pixels)
            assert all(v != "." for v in vals)
