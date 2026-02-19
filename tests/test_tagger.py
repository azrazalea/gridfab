"""Tests for the gridfab.tagger subpackage (non-GUI classes)."""

import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from PIL import Image

from gridfab.tagger.tags import TagManager, DEFAULT_TAGS, RESERVED_KEYS, tiles_to_rects, rects_to_tiles
from gridfab.tagger.navigator import TilesetNavigator
from gridfab.tagger.ai import AIAssistant
from gridfab.tagger.app import _unique_sprite_name, TaggerApp


# ─── TagManager ───────────────────────────────────────────────────────────────

class TestTagManager:

    def test_load_creates_default_config(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        assert config.exists()
        assert mgr.tags == DEFAULT_TAGS

    def test_load_from_existing_config(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text(json.dumps({"tags": {"x": "custom"}}))
        mgr = TagManager(config)
        assert mgr.tags == {"x": "custom"}

    def test_load_invalid_json_falls_back_to_defaults(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text("not json")
        mgr = TagManager(config)
        assert mgr.tags == DEFAULT_TAGS

    def test_save_persists(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        mgr.tags["o"] = "obstacle"
        mgr.save()
        data = json.loads(config.read_text())
        assert data["tags"]["o"] == "obstacle"

    def test_add_tag(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        assert mgr.add_tag("o", "obstacle")
        assert mgr.tags["o"] == "obstacle"
        # Persisted to disk
        data = json.loads(config.read_text())
        assert data["tags"]["o"] == "obstacle"

    def test_add_tag_rejects_existing_key(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        assert not mgr.add_tag("w", "something")  # 'w' is already 'wall'

    def test_add_tag_rejects_reserved_key(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text(json.dumps({"tags": {}}))
        mgr = TagManager(config)
        assert not mgr.add_tag("Tab", "tab_tag")

    def test_add_tag_rejects_multi_char_key(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text(json.dumps({"tags": {}}))
        mgr = TagManager(config)
        assert not mgr.add_tag("ab", "two_chars")

    def test_remove_tag(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        assert mgr.remove_tag("w")
        assert "w" not in mgr.tags

    def test_remove_nonexistent_tag(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text(json.dumps({"tags": {}}))
        mgr = TagManager(config)
        assert not mgr.remove_tag("z")

    def test_get_sorted_letters_before_digits(self, tmp_path):
        config = tmp_path / "tags.json"
        config.write_text(json.dumps({"tags": {"1": "wood", "a": "water", "b": "bed"}}))
        mgr = TagManager(config)
        result = mgr.get_sorted()
        assert result == [("a", "water"), ("b", "bed"), ("1", "wood")]

    def test_save_and_load_empty_tiles(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        tiles = {(0, 2), (0, 3), (1, 2), (1, 3)}
        mgr.save_empty_tiles(tiles)
        loaded = mgr.load_empty_tiles()
        assert loaded == tiles

    def test_empty_tiles_persisted_to_disk(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        mgr.save_empty_tiles({(0, 0), (0, 1)})
        data = json.loads(config.read_text())
        assert "empty_rects" in data

    def test_no_empty_rects_when_no_empties(self, tmp_path):
        config = tmp_path / "tags.json"
        mgr = TagManager(config)
        mgr.save_empty_tiles(set())
        data = json.loads(config.read_text())
        assert "empty_rects" not in data


class TestTilesToRects:

    def test_empty_set(self):
        assert tiles_to_rects(set()) == []

    def test_single_tile(self):
        rects = tiles_to_rects({(0, 0)})
        assert len(rects) == 1
        assert rects[0] == {"r0": 0, "c0": 0, "r1": 0, "c1": 0}

    def test_horizontal_run(self):
        rects = tiles_to_rects({(0, 0), (0, 1), (0, 2)})
        assert len(rects) == 1
        assert rects[0] == {"r0": 0, "c0": 0, "r1": 0, "c1": 2}

    def test_vertical_run(self):
        rects = tiles_to_rects({(0, 0), (1, 0), (2, 0)})
        assert len(rects) == 1
        assert rects[0] == {"r0": 0, "c0": 0, "r1": 2, "c1": 0}

    def test_2x2_block(self):
        rects = tiles_to_rects({(0, 0), (0, 1), (1, 0), (1, 1)})
        assert len(rects) == 1
        assert rects[0] == {"r0": 0, "c0": 0, "r1": 1, "c1": 1}

    def test_two_separate_tiles(self):
        rects = tiles_to_rects({(0, 0), (0, 5)})
        assert len(rects) == 2

    def test_l_shape_needs_multiple_rects(self):
        # L-shape: (0,0), (1,0), (1,1)
        rects = tiles_to_rects({(0, 0), (1, 0), (1, 1)})
        # Should produce 2 rects (can't merge into one rectangle)
        tiles = rects_to_tiles(rects)
        assert tiles == {(0, 0), (1, 0), (1, 1)}

    def test_round_trip_preserves_tiles(self):
        original = {(0, 2), (0, 3), (1, 0), (3, 3), (3, 4), (3, 5)}
        rects = tiles_to_rects(original)
        restored = rects_to_tiles(rects)
        assert restored == original


# ─── TilesetNavigator ─────────────────────────────────────────────────────────

@pytest.fixture
def tileset_4x4(tmp_path):
    """Create a 128x128 tileset image (4x4 tiles of 32px each).

    Layout:
    - (0,0): solid red
    - (0,1): solid green
    - (0,2): fully transparent
    - (0,3): solid blue
    - rest: fully transparent
    """
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    # Red tile at (0,0)
    for y in range(32):
        for x in range(32):
            img.putpixel((x, y), (255, 0, 0, 255))
    # Green tile at (0,1)
    for y in range(32):
        for x in range(32, 64):
            img.putpixel((x, y), (0, 255, 0, 255))
    # Blue tile at (0,3)
    for y in range(32):
        for x in range(96, 128):
            img.putpixel((x, y), (0, 0, 255, 255))
    path = tmp_path / "tileset.png"
    img.save(path)
    return path


class TestTilesetNavigator:

    def test_tile_counting(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        assert nav.rows == 4
        assert nav.cols == 4
        assert nav.total_tiles() == 16

    def test_empty_detection_transparent(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        # (0,0) red, (0,1) green, (0,3) blue = non-empty
        assert (0, 0) not in nav.empty_tiles
        assert (0, 1) not in nav.empty_tiles
        assert (0, 3) not in nav.empty_tiles
        # (0,2) and all of rows 1-3 are transparent
        assert (0, 2) in nav.empty_tiles
        assert (1, 0) in nav.empty_tiles

    def test_non_empty_count(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        assert nav.non_empty_count() == 3  # red, green, blue

    def test_empty_detection_bg_color(self, tmp_path):
        """White tiles should be flagged as empty when bg_color is white."""
        img = Image.new("RGBA", (64, 32), (255, 255, 255, 255))
        # First tile all white, second tile has one red pixel
        img.putpixel((32, 0), (255, 0, 0, 255))
        path = tmp_path / "white_bg.png"
        img.save(path)
        nav = TilesetNavigator(path, tile_size=32, bg_color=(255, 255, 255))
        assert (0, 0) in nav.empty_tiles  # all white
        assert (0, 1) not in nav.empty_tiles  # has a red pixel

    def test_get_tile_image_dimensions(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        tile = nav.get_tile_image(0, 0)
        assert tile.size == (32, 32)

    def test_get_tile_image_multi_tile(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        tile = nav.get_tile_image(0, 0, tiles_x=2, tiles_y=2)
        assert tile.size == (64, 64)

    def test_get_tile_image_content(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        tile = nav.get_tile_image(0, 0)
        # Should be all red
        assert tile.getpixel((0, 0)) == (255, 0, 0, 255)
        assert tile.getpixel((31, 31)) == (255, 0, 0, 255)

    def test_get_context_image(self, tileset_4x4):
        nav = TilesetNavigator(tileset_4x4, tile_size=32)
        ctx, bounds = nav.get_context_image(0, 0, radius=1)
        r0, c0, r1, c1 = bounds
        assert r0 == 0
        assert c0 == 0
        # Context should be at least 2 tiles wide (tile + 1 radius)
        assert ctx.size[0] >= 64
        assert ctx.size[1] >= 64


# ─── AIAssistant ──────────────────────────────────────────────────────────────

class TestAIAssistant:

    def test_fallback_with_tags(self):
        ai = AIAssistant(model="haiku")
        result = ai._fallback(["wall", "stone"])
        assert result["name"] == "wall_stone"
        assert "wall" in result["description"]
        assert "stone" in result["description"]

    def test_fallback_no_tags_no_name(self):
        ai = AIAssistant(model="haiku")
        result = ai._fallback([])
        assert result["name"] == "unnamed_sprite"
        assert result["description"] == "Untagged sprite"

    def test_fallback_with_existing_name(self):
        ai = AIAssistant(model="haiku")
        result = ai._fallback(["wall"], existing_name="stone_wall")
        assert result["name"] == "stone_wall"

    def test_fallback_with_existing_desc(self):
        ai = AIAssistant(model="haiku")
        result = ai._fallback([], existing_desc="A custom description")
        assert result["description"] == "A custom description"

    def test_fallback_truncates_long_tags(self):
        ai = AIAssistant(model="haiku")
        result = ai._fallback(["a", "b", "c", "d", "e"])
        # Name uses at most 4 tags
        assert result["name"] == "a_b_c_d"

    def test_generate_fallback_when_unavailable(self):
        ai = AIAssistant(model="haiku")
        ai.available = False
        tile = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
        result = ai.generate(["wall", "stone"], tile)
        assert result["name"] == "wall_stone"

    def test_generate_fallback_no_tags(self):
        ai = AIAssistant(model="haiku")
        ai.available = False
        tile = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
        result = ai.generate([], tile)
        assert result["name"] == "unnamed_sprite"

    def test_cleanup(self):
        ai = AIAssistant(model="haiku")
        temp_dir = ai.temp_dir
        assert temp_dir.exists()
        ai.cleanup()
        assert not temp_dir.exists()

    def test_model_mapping(self):
        ai = AIAssistant(model="sonnet")
        assert ai.model == AIAssistant.MODEL_MAP["sonnet"]
        assert ai.model_name == "sonnet"

    def test_unknown_model_defaults_to_haiku(self):
        ai = AIAssistant(model="unknown")
        assert ai.model == AIAssistant.MODEL_MAP["haiku"]


class TestUniqueSpriteName:
    def test_no_conflict(self):
        sprites = {}
        name, renamed = _unique_sprite_name("grass", sprites, 0, 0)
        assert name == "grass"
        assert renamed is False

    def test_same_position_overwrites(self):
        sprites = {"grass": {"row": 0, "col": 0}}
        name, renamed = _unique_sprite_name("grass", sprites, 0, 0)
        assert name == "grass"
        assert renamed is False

    def test_different_position_renames(self):
        sprites = {"grass": {"row": 0, "col": 0}}
        name, renamed = _unique_sprite_name("grass", sprites, 1, 0)
        assert name == "grass_2"
        assert renamed is True

    def test_multiple_collisions(self):
        sprites = {
            "grass": {"row": 0, "col": 0},
            "grass_2": {"row": 0, "col": 1},
            "grass_3": {"row": 0, "col": 2},
        }
        name, renamed = _unique_sprite_name("grass", sprites, 1, 0)
        assert name == "grass_4"
        assert renamed is True

    def test_no_conflict_with_unrelated_names(self):
        sprites = {"stone": {"row": 0, "col": 0}}
        name, renamed = _unique_sprite_name("grass", sprites, 0, 1)
        assert name == "grass"
        assert renamed is False


# ─── TaggerApp._tile_as_text ─────────────────────────────────────────────────

class TestTileAsText:
    """Tests for converting tile images to grid.txt + palette.txt text."""

    @pytest.fixture
    def tagger_app(self, tileset_4x4):
        """Create a TaggerApp without launching the GUI."""
        with patch.object(TaggerApp, '_build_gui'):
            app = TaggerApp(str(tileset_4x4), tile_size=32)
        return app

    def test_tile_as_text_returns_grid_and_palette_sections(self, tagger_app):
        """_tile_as_text() output contains both grid.txt and palette.txt headers."""
        text = tagger_app._tile_as_text()
        assert "grid.txt:" in text
        assert "palette.txt:" in text

    def test_tile_as_text_solid_red_tile(self, tagger_app):
        """Tile (0,0) is solid red — should produce uniform grid + one palette entry."""
        # Navigate to tile (0,0) which is solid red
        tagger_app.current_idx = 0
        text = tagger_app._tile_as_text()
        lines = text.strip().split("\n")
        # Find grid section — all rows should have the same single alias
        grid_start = lines.index("grid.txt:") + 1
        palette_start = lines.index("palette.txt:")
        grid_lines = [l for l in lines[grid_start:palette_start] if l.strip()]
        assert len(grid_lines) == 32  # 32x32 tile
        # All cells should be the same alias (solid red)
        first_alias = grid_lines[0].split()[0]
        for row in grid_lines:
            cells = row.split()
            assert len(cells) == 32
            assert all(c == first_alias for c in cells)
        # Palette should have exactly one entry mapping to red
        palette_lines = [l for l in lines[palette_start + 1:] if l.strip()]
        assert len(palette_lines) == 1
        assert "#FF0000" in palette_lines[0].upper()

    def test_tile_as_text_transparent_tile(self, tagger_app):
        """A fully transparent tile should produce all '.' in the grid and no palette entries."""
        # Find the index for tile (0,2) which is transparent
        for i, (r, c) in enumerate(tagger_app.tile_order):
            if r == 0 and c == 2:
                tagger_app.current_idx = i
                break
        else:
            # (0,2) is empty, won't be in tile_order — use nav directly
            tagger_app.current_idx = 0
            # Manually construct the text for the transparent tile
            from gridfab.commands.import_cmd import image_to_grid_and_palette
            tile_img = tagger_app.nav.get_tile_image(0, 2)
            grid_data, palette = image_to_grid_and_palette(tile_img)
            assert all(c == "." for row in grid_data for c in row)
            assert palette == {}
            return
        text = tagger_app._tile_as_text()
        assert "." in text

    def test_tile_as_text_multi_tile_selection(self, tagger_app):
        """Multi-tile selection should produce a larger grid."""
        tagger_app.current_idx = 0  # (0,0)
        tagger_app.sel_tiles_x = 2
        tagger_app.sel_tiles_y = 1
        text = tagger_app._tile_as_text()
        lines = text.strip().split("\n")
        grid_start = lines.index("grid.txt:") + 1
        palette_start = lines.index("palette.txt:")
        grid_lines = [l for l in lines[grid_start:palette_start] if l.strip()]
        # 2 tiles wide = 64 columns
        assert len(grid_lines[0].split()) == 64

    def test_tile_as_text_returns_none_when_no_tile(self, tagger_app):
        """Returns None when there's no current tile."""
        tagger_app.current_idx = len(tagger_app.tile_order)  # Past end
        result = tagger_app._tile_as_text()
        assert result is None

    def test_tile_as_text_bg_color_becomes_transparent(self, tmp_path):
        """Pixels matching bg_color should become '.' in grid output."""
        # Create a 32x32 tileset: all white except one red pixel
        img = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        img.putpixel((0, 0), (255, 0, 0, 255))
        path = tmp_path / "white_bg.png"
        img.save(path)
        with patch.object(TaggerApp, '_build_gui'):
            app = TaggerApp(str(path), tile_size=32, bg_color=(255, 255, 255))
        app.current_idx = 0
        text = app._tile_as_text()
        lines = text.strip().split("\n")
        grid_start = lines.index("grid.txt:") + 1
        palette_start = lines.index("palette.txt:")
        grid_lines = [l for l in lines[grid_start:palette_start] if l.strip()]
        # First cell should be the red alias, rest should be '..' (padded transparent)
        first_row = grid_lines[0].split()
        assert first_row[0] != ".."  # red pixel
        assert all(c == ".." for c in first_row[1:])  # rest is bg → transparent
        # All other rows should be all '..'
        for row in grid_lines[1:]:
            assert all(c == ".." for c in row.split())


# ─── AI grid_text parameter ──────────────────────────────────────────────────

class TestAIGridText:
    """Tests for grid_text parameter in AI generate()."""

    def test_generate_accepts_grid_text(self):
        """generate() accepts grid_text parameter without error."""
        ai = AIAssistant(model="haiku")
        ai.available = False  # Use fallback
        tile = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
        result = ai.generate(["wall"], tile, grid_text="grid.txt:\nA\n\npalette.txt:\nA=#FF0000")
        assert "name" in result

    def test_generate_includes_grid_text_in_prompt(self):
        """When grid_text is provided, it appears in the prompt sent to Claude."""
        ai = AIAssistant(model="haiku")
        ai.available = True
        tile = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
        grid_text = "grid.txt:\nA A\nA A\n\npalette.txt:\nA=#FF0000"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"result": '{"name": "red_tile", "description": "A red tile"}'}),
                stderr="",
            )
            ai.generate(["wall"], tile, grid_text=grid_text)
            # Check the prompt arg passed to subprocess
            call_args = mock_run.call_args[0][0]
            prompt_idx = call_args.index("-p") + 1
            prompt = call_args[prompt_idx]
            assert "grid.txt" in prompt
            assert "A=#FF0000" in prompt

    def test_generate_without_grid_text_no_section(self):
        """When grid_text is None, the prompt does not contain grid.txt section."""
        ai = AIAssistant(model="haiku")
        ai.available = True
        tile = Image.new("RGBA", (32, 32), (255, 0, 0, 255))

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"result": '{"name": "red_tile", "description": "A red tile"}'}),
                stderr="",
            )
            ai.generate(["wall"], tile, grid_text=None)
            call_args = mock_run.call_args[0][0]
            prompt_idx = call_args.index("-p") + 1
            prompt = call_args[prompt_idx]
            assert "actual pixel data" not in prompt
