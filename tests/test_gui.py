"""Tests for gridfab.gui — pure functions only (no tkinter event loop)."""

import pytest
from gridfab.gui import (
    checker_color, cell_display_color, _contrast_color,
    format_status_text, grid_line_config,
    CHECKER_LIGHT, CHECKER_DARK,
)
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


class TestContrastColor:
    def test_black_background_returns_white(self):
        assert _contrast_color("#000000") == "#FFFFFF"

    def test_white_background_returns_black(self):
        assert _contrast_color("#FFFFFF") == "#000000"

    def test_dark_blue_returns_white(self):
        assert _contrast_color("#000080") == "#FFFFFF"

    def test_yellow_returns_black(self):
        assert _contrast_color("#FFFF00") == "#000000"

    def test_mid_gray_threshold(self):
        # luminance = 0.299*128 + 0.587*128 + 0.114*128 = 128
        # luminance <= 128, so white text
        assert _contrast_color("#808080") == "#FFFFFF"
        # Slightly brighter → black text
        assert _contrast_color("#818181") == "#000000"


class TestFormatStatusText:
    def test_with_cursor_position(self):
        text = format_status_text(
            cursor_pos=(5, 10), selected="R", selected_hex="#CC3333",
            grid_w=32, grid_h=32, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "(5, 10)" in text

    def test_no_cursor_position(self):
        text = format_status_text(
            cursor_pos=None, selected="R", selected_hex="#CC3333",
            grid_w=32, grid_h=32, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "(5, 10)" not in text

    def test_selected_color_and_hex(self):
        text = format_status_text(
            cursor_pos=None, selected="SK", selected_hex="#FFCCAA",
            grid_w=16, grid_h=16, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "SK" in text
        assert "#FFCCAA" in text

    def test_transparent_selected(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=16, grid_h=16, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "Transparent" in text

    def test_dimensions(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=64, grid_h=48, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "64x48" in text

    def test_modified_flag(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=16, grid_h=16, modified=True, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "[Modified]" in text

    def test_not_modified(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=16, grid_h=16, modified=False, tool_name="Brush",
            zoom_pct=100, file_path="knight",
        )
        assert "[Modified]" not in text

    def test_tool_name(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=16, grid_h=16, modified=False, tool_name="Fill",
            zoom_pct=100, file_path="knight",
        )
        assert "Fill" in text

    def test_zoom_percentage(self):
        text = format_status_text(
            cursor_pos=None, selected=".", selected_hex=None,
            grid_w=16, grid_h=16, modified=False, tool_name="Brush",
            zoom_pct=200, file_path="knight",
        )
        assert "200%" in text


class TestGridLineConfig:
    def test_visible_returns_outline(self):
        cfg = grid_line_config(True)
        assert cfg["outline"] == "#333333"
        assert cfg["width"] > 0

    def test_hidden_returns_empty_outline(self):
        cfg = grid_line_config(False)
        assert cfg["outline"] == ""
        assert cfg["width"] == 0
