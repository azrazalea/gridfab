"""Tests for gridfab.commands — CLI command functions."""

import json
import pytest
from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.animation import (
    discover_frames, frame_path, save_state, load_state,
)
from gridfab.commands.init import cmd_init
from gridfab.commands.edit import (
    cmd_row, cmd_rows, cmd_fill, cmd_rect, cmd_pixel, cmd_pixels, cmd_clear,
)
from gridfab.commands.frame_cmd import cmd_frame_add
from gridfab.commands.render_cmd import cmd_render
from gridfab.commands.export_cmd import cmd_export, cmd_palette, cmd_palette_rename
from gridfab.commands.icon_cmd import cmd_icon


class TestCmdInit:
    def test_creates_files(self, tmp_path: Path):
        cmd_init(tmp_path, 4, 4)
        assert (tmp_path / "grid.txt").exists()
        assert (tmp_path / "palette.txt").exists()
        assert (tmp_path / "gridfab.json").exists()

    def test_correct_dimensions(self, tmp_path: Path):
        cmd_init(tmp_path, 8, 16)
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.width == 8
        assert grid.height == 16

    def test_rejects_existing_grid(self, tmp_path: Path):
        cmd_init(tmp_path, 4, 4)
        with pytest.raises(FileExistsError, match="already exists"):
            cmd_init(tmp_path, 4, 4)

    def test_keeps_existing_palette(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("R=#FF0000\n")
        cmd_init(tmp_path, 4, 4)
        assert "R=#FF0000" in (tmp_path / "palette.txt").read_text()

    def test_creates_subdirs(self, tmp_path: Path):
        sub = tmp_path / "a" / "b"
        cmd_init(sub, 4, 4)
        assert (sub / "grid.txt").exists()


class TestCmdRow:
    def test_replaces_row(self, sprite_dir: Path):
        cmd_row(sprite_dir, 0, ["R", "B", "R", "B"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.data[0] == ["R", "B", "R", "B"]

    def test_wrong_value_count(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="expected 4 values"):
            cmd_row(sprite_dir, 0, ["R", "B"])

    def test_invalid_alias(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="unknown palette alias"):
            cmd_row(sprite_dir, 0, ["R", "NOPE", "R", "R"])

    def test_out_of_bounds(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="row must be"):
            cmd_row(sprite_dir, 10, ["R", "R", "R", "R"])


class TestCmdRows:
    def test_replaces_range(self, sprite_dir: Path):
        # 2 rows x 4 cols = 8 values
        cmd_rows(sprite_dir, 0, 1, ["R", "B", "R", "B", "G", "G", "G", "G"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.data[0] == ["R", "B", "R", "B"]
        assert grid.data[1] == ["G", "G", "G", "G"]

    def test_wrong_total_values(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="expected 8 values"):
            cmd_rows(sprite_dir, 0, 1, ["R", "B", "R"])


class TestCmdFill:
    def test_fills_span(self, sprite_dir: Path):
        cmd_fill(sprite_dir, 0, 1, 2, "R")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.data[0] == [".", "R", "R", "."]

    def test_hex_auto_alias(self, sprite_dir: Path):
        """Hex color should auto-generate an alias instead of writing hex to grid."""
        cmd_fill(sprite_dir, 0, 0, 0, "#FF0000")
        grid = Grid.load(sprite_dir / "grid.txt")
        # Should be an alias, not raw hex
        assert not grid.data[0][0].startswith("#")
        assert len(grid.data[0][0]) <= 2
        # Palette should contain the new color
        from gridfab.core.palette import Palette
        palette = Palette.load(sprite_dir / "palette.txt")
        assert palette.resolve(grid.data[0][0]) == "#FF0000"

    def test_invalid_color(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="unknown palette alias"):
            cmd_fill(sprite_dir, 0, 0, 0, "NOPE")


class TestCmdRect:
    def test_fills_rectangle(self, sprite_dir: Path):
        cmd_rect(sprite_dir, 0, 0, 1, 1, "B")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.data[0][:2] == ["B", "B"]
        assert grid.data[1][:2] == ["B", "B"]
        assert grid.data[0][2] == "."

    def test_invalid_color(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="unknown palette alias"):
            cmd_rect(sprite_dir, 0, 0, 1, 1, "NOPE")


class TestCmdPixel:
    def test_sets_single_pixel(self, sprite_dir: Path):
        cmd_pixel(sprite_dir, 2, 3, "R")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(2, 3) == "R"
        # Other pixels unchanged
        assert grid.get(0, 0) == "."
        assert grid.get(2, 2) == "."

    def test_hex_auto_alias(self, sprite_dir: Path):
        """Hex color should auto-generate an alias."""
        cmd_pixel(sprite_dir, 0, 0, "#AABBCC")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert not grid.get(0, 0).startswith("#")
        from gridfab.core.palette import Palette
        palette = Palette.load(sprite_dir / "palette.txt")
        assert palette.resolve(grid.get(0, 0)) == "#AABBCC"

    def test_invalid_color(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="unknown palette alias"):
            cmd_pixel(sprite_dir, 0, 0, "NOPE")

    def test_out_of_bounds_row(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="row must be"):
            cmd_pixel(sprite_dir, 99, 0, "R")

    def test_out_of_bounds_col(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="col must be"):
            cmd_pixel(sprite_dir, 0, 99, "R")

    def test_transparent(self, sprite_dir: Path):
        cmd_pixel(sprite_dir, 0, 0, "R")
        cmd_pixel(sprite_dir, 0, 0, ".")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "."


class TestCmdPixels:
    def test_sets_multiple_pixels(self, sprite_dir: Path):
        cmd_pixels(sprite_dir, ["0,0,R", "1,1,B", "2,2,G"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "R"
        assert grid.get(1, 1) == "B"
        assert grid.get(2, 2) == "G"

    def test_hex_auto_alias(self, sprite_dir: Path):
        """Hex colors should auto-generate aliases."""
        cmd_pixels(sprite_dir, ["0,0,#FF0000", "1,1,#00FF00"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert not grid.get(0, 0).startswith("#")
        assert not grid.get(1, 1).startswith("#")
        from gridfab.core.palette import Palette
        palette = Palette.load(sprite_dir / "palette.txt")
        assert palette.resolve(grid.get(0, 0)) == "#FF0000"
        assert palette.resolve(grid.get(1, 1)) == "#00FF00"

    def test_bad_spec_too_few_parts(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="expected row,col,color"):
            cmd_pixels(sprite_dir, ["0,0"])

    def test_bad_spec_too_many_parts(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="expected row,col,color"):
            cmd_pixels(sprite_dir, ["0,0,R,extra"])

    def test_bad_spec_non_integer_row(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="row must be integer"):
            cmd_pixels(sprite_dir, ["abc,0,R"])

    def test_bad_spec_non_integer_col(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="col must be integer"):
            cmd_pixels(sprite_dir, ["0,abc,R"])

    def test_invalid_color_in_batch(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="unknown palette alias"):
            cmd_pixels(sprite_dir, ["0,0,R", "1,1,NOPE"])

    def test_validates_all_before_writing(self, sprite_dir: Path):
        """Bad pixel in batch should not write any pixels."""
        with pytest.raises(ValueError):
            cmd_pixels(sprite_dir, ["0,0,R", "1,1,NOPE"])
        grid = Grid.load(sprite_dir / "grid.txt")
        # First pixel should NOT have been written since validation failed
        assert grid.get(0, 0) == "."

    def test_single_pixel_via_pixels(self, sprite_dir: Path):
        cmd_pixels(sprite_dir, ["3,3,B"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(3, 3) == "B"


class TestHexAutoAlias:
    def test_reuses_existing_color(self, sprite_dir: Path):
        """If hex color already in palette, use the existing alias."""
        # sprite_dir has R=#CC3333
        cmd_pixel(sprite_dir, 0, 0, "#CC3333")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "R"

    def test_generates_new_alias(self, sprite_dir: Path):
        """New hex color gets a new alias added to palette."""
        cmd_pixel(sprite_dir, 0, 0, "#123456")
        grid = Grid.load(sprite_dir / "grid.txt")
        alias = grid.get(0, 0)
        assert not alias.startswith("#")
        from gridfab.core.palette import Palette
        palette = Palette.load(sprite_dir / "palette.txt")
        assert palette.resolve(alias) == "#123456"


class TestCmdClear:
    def test_clears_all_pixels(self, sprite_dir: Path):
        cmd_fill(sprite_dir, 0, 0, 3, "R")
        cmd_clear(sprite_dir)
        grid = Grid.load(sprite_dir / "grid.txt")
        assert all(v == "." for row in grid.data for v in row)

    def test_preserves_dimensions(self, sprite_dir: Path):
        cmd_clear(sprite_dir)
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.width == 4
        assert grid.height == 4

    def test_already_blank(self, sprite_dir: Path):
        """Clearing a blank grid should not error."""
        cmd_clear(sprite_dir)
        grid = Grid.load(sprite_dir / "grid.txt")
        assert all(v == "." for row in grid.data for v in row)

    def test_missing_grid(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            cmd_clear(tmp_path)


class TestCmdRender:
    def test_creates_preview(self, sprite_dir: Path):
        cmd_render(sprite_dir)
        assert (sprite_dir / "preview.png").exists()

    def test_missing_grid(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            cmd_render(tmp_path)


class TestCmdExport:
    def test_creates_output_pngs(self, sprite_dir_with_config: Path):
        cmd_export(sprite_dir_with_config)
        assert (sprite_dir_with_config / "output.png").exists()
        assert (sprite_dir_with_config / "output_2x.png").exists()

    def test_missing_grid(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            cmd_export(tmp_path)


class TestCmdPalette:
    def test_displays_entries(self, sprite_dir: Path, capsys):
        cmd_palette(sprite_dir)
        captured = capsys.readouterr()
        assert "R" in captured.out
        assert "#CC3333" in captured.out

    def test_empty_palette(self, tmp_path: Path, capsys):
        (tmp_path / "palette.txt").write_text("# empty\n")
        cmd_palette(tmp_path)
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            cmd_palette(tmp_path)


class TestCmdIcon:
    def test_creates_icon_files(self, sprite_dir_with_config: Path):
        cmd_icon(sprite_dir_with_config)
        assert (sprite_dir_with_config / "icon.ico").exists()
        assert (sprite_dir_with_config / "icon.icns").exists()

    def test_missing_grid(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            cmd_icon(tmp_path)

    def test_non_square_grid(self, tmp_path: Path):
        """A 4x3 rectangular grid should raise ValueError."""
        (tmp_path / "grid.txt").write_text(
            ". . . .\n"
            ". . . .\n"
            ". . . .\n"
        )
        (tmp_path / "palette.txt").write_text("R=#CC3333\n")
        with pytest.raises(ValueError, match="square"):
            cmd_icon(tmp_path)


# ===================================================================
# Frame-aware edit commands (--frame integration)
# ===================================================================

@pytest.fixture
def animated_sprite(tmp_path):
    """Create a 4x4 animated sprite with 2 frames."""
    (tmp_path / "palette.txt").write_text("R=#CC3333\nB=#0000FF\nG=#00CC00\n")
    (tmp_path / "grid.txt").write_text(
        ". . . .\n. . . .\n. . . .\n. . . .\n"
    )
    cmd_frame_add(tmp_path)  # creates frame_001 + frame_002
    return tmp_path


class TestFrameAwarePixel:
    def test_pixel_with_explicit_frame(self, animated_sprite):
        """pixel with frame=1 edits frame_001.txt."""
        cmd_pixel(animated_sprite, 0, 0, "R", frame=1)
        grid = Grid.load(frame_path(animated_sprite, 1))
        assert grid.get(0, 0) == "R"
        # frame 2 should be unchanged
        grid2 = Grid.load(frame_path(animated_sprite, 2))
        assert grid2.get(0, 0) == "."

    def test_pixel_without_frame_uses_active(self, animated_sprite):
        """pixel without --frame in animated dir uses active frame from state."""
        # active is frame 2 (set by frame add)
        cmd_pixel(animated_sprite, 1, 1, "B")
        grid2 = Grid.load(frame_path(animated_sprite, 2))
        assert grid2.get(1, 1) == "B"

    def test_pixel_non_animated_uses_grid_txt(self, sprite_dir):
        """pixel on non-animated dir still uses grid.txt."""
        cmd_pixel(sprite_dir, 0, 0, "R")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "R"


class TestFrameAwareRow:
    def test_row_with_frame(self, animated_sprite):
        cmd_row(animated_sprite, 0, ["R", "B", "R", "B"], frame=1)
        grid = Grid.load(frame_path(animated_sprite, 1))
        assert grid.data[0] == ["R", "B", "R", "B"]


class TestFrameAwareFill:
    def test_fill_with_frame(self, animated_sprite):
        cmd_fill(animated_sprite, 0, 0, 3, "G", frame=1)
        grid = Grid.load(frame_path(animated_sprite, 1))
        assert grid.data[0] == ["G", "G", "G", "G"]


class TestFrameAwareClear:
    def test_clear_with_frame(self, animated_sprite):
        cmd_pixel(animated_sprite, 0, 0, "R", frame=1)
        cmd_clear(animated_sprite, frame=1)
        grid = Grid.load(frame_path(animated_sprite, 1))
        assert all(v == "." for row in grid.data for v in row)


class TestFrameAwareRender:
    def test_render_with_frame(self, animated_sprite):
        cmd_render(animated_sprite, frame=1)
        assert (animated_sprite / "preview.png").exists()


class TestFrameAwareExport:
    def test_export_with_frame(self, animated_sprite):
        config = {"grid": {"width": 4, "height": 4}, "export": {"scales": [1]}}
        (animated_sprite / "gridfab.json").write_text(json.dumps(config))
        cmd_export(animated_sprite, frame=1)
        assert (animated_sprite / "output.png").exists()


# ===================================================================
# Palette rename
# ===================================================================

class TestCmdPaletteRename:
    def test_renames_alias_in_palette(self, sprite_dir: Path):
        """Rename R→RD in palette."""
        cmd_pixel(sprite_dir, 0, 0, "R")
        cmd_palette_rename(sprite_dir, "R", "RD")
        from gridfab.core.palette import Palette
        palette = Palette.load(sprite_dir / "palette.txt")
        assert "RD" in palette.entries
        assert "R" not in palette.entries
        assert palette.resolve("RD") == "#CC3333"

    def test_renames_alias_in_grid(self, sprite_dir: Path):
        """Grid should have new alias after rename."""
        cmd_pixel(sprite_dir, 0, 0, "R")
        cmd_palette_rename(sprite_dir, "R", "RD")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "RD"

    def test_renames_in_frame_files(self, sprite_dir: Path):
        """Rename should update frame_NNN.txt files too."""
        cmd_pixel(sprite_dir, 0, 0, "R")
        cmd_frame_add(sprite_dir)  # converts to animated
        cmd_palette_rename(sprite_dir, "R", "RD")
        grid = Grid.load(sprite_dir / "frame_001.txt")
        assert grid.get(0, 0) == "RD"

    def test_rejects_nonexistent_alias(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="not found"):
            cmd_palette_rename(sprite_dir, "X", "Y")

    def test_rejects_invalid_new_alias(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="reserved"):
            cmd_palette_rename(sprite_dir, "R", "A.")

    def test_rejects_too_long_alias(self, sprite_dir: Path):
        with pytest.raises(ValueError, match="1-2 characters"):
            cmd_palette_rename(sprite_dir, "R", "ABC")

    def test_rejects_case_insensitive_collision(self, sprite_dir: Path):
        """Can't rename to alias that collides case-insensitively with existing."""
        # sprite_dir has R, B, G
        with pytest.raises(ValueError, match="conflicts"):
            cmd_palette_rename(sprite_dir, "R", "b")

    def test_same_alias_noop(self, sprite_dir: Path):
        """Renaming to same alias should raise."""
        with pytest.raises(ValueError, match="same as old"):
            cmd_palette_rename(sprite_dir, "R", "R")
