"""Tests for gridfab.gui — pure functions only (no tkinter event loop)."""

import pytest
from gridfab.gui import checker_color, cell_display_color, CHECKER_LIGHT, CHECKER_DARK
from gridfab.core.palette import Palette


class TestCheckerColor:
    def test_returns_light_or_dark(self):
        color = checker_color(0, 0)
        assert color in (CHECKER_LIGHT, CHECKER_DARK)

    def test_alternates_between_blocks(self):
        assert checker_color(0, 0) != checker_color(0, 2)

    def test_same_within_block(self):
        assert checker_color(0, 0) == checker_color(0, 1)
        assert checker_color(0, 0) == checker_color(1, 0)


class TestCellDisplayColor:
    def test_transparent_shows_checker(self):
        palette = Palette()
        color = cell_display_color(".", palette, 0, 0)
        assert color in (CHECKER_LIGHT, CHECKER_DARK)

    def test_known_alias(self):
        palette = Palette({"R": "#CC3333"})
        assert cell_display_color("R", palette, 0, 0) == "#CC3333"

    def test_inline_hex(self):
        palette = Palette()
        assert cell_display_color("#AABBCC", palette, 0, 0) == "#AABBCC"

    def test_unknown_returns_magenta(self):
        palette = Palette()
        assert cell_display_color("??", palette, 0, 0) == "#FF00FF"
