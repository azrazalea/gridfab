"""Tests for gridfab.core.grid."""

import pytest
from pathlib import Path

from gridfab.core.grid import Grid, TRANSPARENT


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
