"""Tests for gridfab.core.grid."""

import json
import pytest
from pathlib import Path

from gridfab.core.grid import Grid, TRANSPARENT, _is_valid_cell, load_config, get_grid_dimensions


class TestGridBlank:
    def test_default_size(self):
        grid = Grid.blank()
        assert grid.width == 32
        assert grid.height == 32
        assert all(v == TRANSPARENT for row in grid.data for v in row)

    def test_custom_size(self):
        grid = Grid.blank(8, 16)
        assert grid.width == 8
        assert grid.height == 16
        assert len(grid.data) == 16
        assert len(grid.data[0]) == 8


class TestGridLoadSave:
    def test_round_trip(self, sample_grid: Path):
        grid = Grid.load(sample_grid / "grid.txt")
        assert grid.width == 4
        assert grid.height == 4

        output = sample_grid / "output_grid.txt"
        grid.save(output)
        reloaded = Grid.load(output)

        assert reloaded.data == grid.data

    def test_load_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            Grid.load(tmp_path / "nonexistent.txt")


class TestGridManipulation:
    def test_get_set(self, sample_grid: Path):
        grid = Grid.load(sample_grid / "grid.txt")
        assert grid.get(0, 0) == "."
        assert grid.get(0, 2) == "R"

        grid.set(0, 0, "R")
        assert grid.get(0, 0) == "R"

    def test_bounds_check(self, sample_grid: Path):
        grid = Grid.load(sample_grid / "grid.txt")
        with pytest.raises(ValueError, match="row must be"):
            grid.get(10, 0)
        with pytest.raises(ValueError, match="col must be"):
            grid.get(0, 10)

    def test_fill_rect(self, sample_grid: Path):
        grid = Grid.load(sample_grid / "grid.txt")
        grid.fill_rect(0, 0, 1, 1, "B")
        assert grid.get(0, 0) == "B"
        assert grid.get(0, 1) == "B"
        assert grid.get(1, 0) == "B"
        assert grid.get(1, 1) == "B"

    def test_fill_rect_reversed_rows(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="r1.*must be >= r0"):
            grid.fill_rect(3, 0, 1, 3, "R")

    def test_fill_rect_reversed_cols(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="c1.*must be >= c0"):
            grid.fill_rect(0, 3, 3, 1, "R")

    def test_flood_fill_same_value(self):
        grid = Grid.blank(4, 4)
        grid.set(0, 0, "R")
        grid.flood_fill(0, 0, "R")  # no-op, target == value
        assert grid.get(0, 0) == "R"

    def test_flood_fill(self):
        grid = Grid.blank(4, 4)
        grid.set(0, 0, "R")
        grid.set(0, 1, "R")
        grid.set(1, 0, "R")
        grid.flood_fill(0, 0, "B")
        assert grid.get(0, 0) == "B"
        assert grid.get(0, 1) == "B"
        assert grid.get(1, 0) == "B"
        assert grid.get(1, 1) == "."  # not connected

    def test_flip_horizontal(self):
        grid = Grid.blank(4, 1)
        grid.data[0] = ["R", ".", ".", "."]
        grid.flip_horizontal()
        assert grid.data[0] == [".", ".", ".", "R"]

    def test_flip_vertical(self):
        grid = Grid.blank(1, 3)
        grid.data[0] = ["R"]
        grid.data[1] = ["."]
        grid.data[2] = ["B"]
        grid.flip_vertical()
        assert grid.data[0] == ["B"]
        assert grid.data[2] == ["R"]

    def test_snapshot_restore(self, sample_grid: Path):
        grid = Grid.load(sample_grid / "grid.txt")
        snap = grid.snapshot()
        grid.fill_rect(0, 0, 3, 3, "X")
        assert grid.get(0, 0) == "X"
        grid.restore(snap)
        assert grid.get(0, 0) == "."


class TestGridRepr:
    def test_repr(self):
        grid = Grid.blank(8, 16)
        assert repr(grid) == "Grid(8x16)"


class TestGridSetRow:
    def test_replaces_row(self):
        grid = Grid.blank(4, 4)
        grid.set_row(1, ["R", "B", "R", "B"])
        assert grid.data[1] == ["R", "B", "R", "B"]

    def test_wrong_length(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="expected 4 values"):
            grid.set_row(0, ["R", "B"])

    def test_out_of_bounds(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="row must be"):
            grid.set_row(5, [".", ".", ".", "."])


class TestGridFillRow:
    def test_fills_span(self):
        grid = Grid.blank(4, 4)
        grid.fill_row(0, 1, 2, "R")
        assert grid.data[0] == [".", "R", "R", "."]

    def test_single_cell(self):
        grid = Grid.blank(4, 4)
        grid.fill_row(0, 2, 2, "B")
        assert grid.data[0] == [".", ".", "B", "."]

    def test_reversed_range(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="col_end.*must be >= col_start"):
            grid.fill_row(0, 3, 1, "R")

    def test_out_of_bounds(self):
        grid = Grid.blank(4, 4)
        with pytest.raises(ValueError, match="col must be"):
            grid.fill_row(0, 0, 5, "R")


class TestGridAutoRepair:
    def test_skips_blank_lines(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("R R\n\n. .\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.height == 2
        assert grid.data[0] == ["R", "R"]
        assert grid.data[1] == [".", "."]

    def test_trims_extra_columns(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text(". . R\n. . R B EXTRA\n. . R\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.width == 3
        assert grid.data[1] == [".", ".", "R"]
        captured = capsys.readouterr()
        assert "trimmed 2 extra column(s)" in captured.err

    def test_pads_short_rows(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text("R R R\nR\nR R R\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.width == 3
        assert grid.data[1] == ["R", ".", "."]
        captured = capsys.readouterr()
        assert "padded 2 missing column(s)" in captured.err

    def test_replaces_invalid_values(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text(". TOOLONG . .\n. . . .\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.data[0][1] == "."
        captured = capsys.readouterr()
        assert "replaced invalid value 'TOOLONG'" in captured.err

    def test_replaces_bad_hex(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text("#ZZZZZZ . . .\n. . . .\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.data[0][0] == "."
        captured = capsys.readouterr()
        assert "replaced invalid value '#ZZZZZZ'" in captured.err

    def test_keeps_valid_hex(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("#FF0000 . . .\n. . . .\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.data[0][0] == "#FF0000"

    def test_saves_repaired_file(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("R R\nR R R EXTRA\n")
        Grid.load(tmp_path / "grid.txt")
        # Reloading should find no issues (file was auto-saved)
        content = (tmp_path / "grid.txt").read_text()
        assert content == "R R\nR R\n"

    def test_no_repairs_no_output(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text(". R\nR .\n")
        Grid.load(tmp_path / "grid.txt")
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_repair_report_format(self, tmp_path: Path, capsys):
        (tmp_path / "grid.txt").write_text("R R R EXTRA\n. .\n")
        Grid.load(tmp_path / "grid.txt")
        captured = capsys.readouterr()
        assert "GRID AUTO-REPAIR" in captured.err
        assert "issue(s) fixed automatically" in captured.err
        assert "Review the changes above" in captured.err

    def test_empty_file_still_errors(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("")
        with pytest.raises(ValueError, match="file is empty"):
            Grid.load(tmp_path / "grid.txt")

    def test_1x1_grid(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("R\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.width == 1
        assert grid.height == 1
        assert grid.data[0] == ["R"]

    def test_non_square_grid(self, tmp_path: Path):
        (tmp_path / "grid.txt").write_text("R B\nR B\nR B\n")
        grid = Grid.load(tmp_path / "grid.txt")
        assert grid.width == 2
        assert grid.height == 3


class TestIsValidCell:
    def test_transparent(self):
        assert _is_valid_cell(".") is True

    def test_single_char_alias(self):
        assert _is_valid_cell("R") is True

    def test_two_char_alias(self):
        assert _is_valid_cell("SK") is True

    def test_valid_hex(self):
        assert _is_valid_cell("#FF0000") is True

    def test_too_long_alias(self):
        assert _is_valid_cell("ABC") is False

    def test_bad_hex(self):
        assert _is_valid_cell("#ZZZZZZ") is False

    def test_short_hex(self):
        assert _is_valid_cell("#FFF") is False

    def test_empty_string(self):
        assert _is_valid_cell("") is False


class TestLoadConfig:
    def test_missing_config(self, tmp_path: Path):
        assert load_config(tmp_path) == {}

    def test_valid_config(self, tmp_path: Path):
        import json
        config = {"grid": {"width": 16, "height": 16}, "export": {"scales": [1, 4]}}
        (tmp_path / "gridfab.json").write_text(json.dumps(config))
        result = load_config(tmp_path)
        assert result["grid"]["width"] == 16


class TestGetGridDimensions:
    def test_defaults_without_config(self, tmp_path: Path):
        w, h = get_grid_dimensions(tmp_path)
        assert w == 32
        assert h == 32

    def test_reads_from_config(self, tmp_path: Path):
        import json
        config = {"grid": {"width": 8, "height": 16}}
        (tmp_path / "gridfab.json").write_text(json.dumps(config))
        w, h = get_grid_dimensions(tmp_path)
        assert w == 8
        assert h == 16
