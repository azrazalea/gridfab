"""Tests for gridfab.commands — CLI command functions."""

import pytest
from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.commands.init import cmd_init
from gridfab.commands.edit import (
    cmd_row, cmd_rows, cmd_fill, cmd_rect, cmd_pixel, cmd_pixels, cmd_clear,
)


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

    def test_hex_color(self, sprite_dir: Path):
        cmd_fill(sprite_dir, 0, 0, 0, "#FF0000")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.data[0][0] == "#FF0000"

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

    def test_hex_color(self, sprite_dir: Path):
        cmd_pixel(sprite_dir, 0, 0, "#AABBCC")
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "#AABBCC"

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

    def test_hex_colors(self, sprite_dir: Path):
        cmd_pixels(sprite_dir, ["0,0,#FF0000", "1,1,#00FF00"])
        grid = Grid.load(sprite_dir / "grid.txt")
        assert grid.get(0, 0) == "#FF0000"
        assert grid.get(1, 1) == "#00FF00"

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
