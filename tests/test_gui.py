"""Tests for gridfab.gui — pure functions only (no tkinter event loop)."""

import pytest
from gridfab.gui import (
    checker_color, cell_display_color, _contrast_color,
    format_status_text, grid_line_config,
    zoom_step, cell_at_coords, fit_zoom_level,
    cursor_preview_color, eyedropper_pick,
    palette_key_to_index, palette_index_to_alias,
    render_frame_thumbnail, frame_strip_layout,
    CHECKER_LIGHT, CHECKER_DARK, ZOOM_LEVELS,
    TOOL_BRUSH, TOOL_EYEDROPPER, TOOL_FILL,
)
from gridfab.core.palette import Palette
from gridfab.core.grid import Grid, TRANSPARENT


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


class TestZoomStep:
    def test_zoom_in_from_default(self):
        assert zoom_step(16, 1) == 24

    def test_zoom_out_from_default(self):
        assert zoom_step(16, -1) == 8

    def test_zoom_in_at_max(self):
        assert zoom_step(ZOOM_LEVELS[-1], 1) == ZOOM_LEVELS[-1]

    def test_zoom_out_at_min(self):
        assert zoom_step(ZOOM_LEVELS[0], -1) == ZOOM_LEVELS[0]

    def test_zoom_in_steps_through_levels(self):
        level = ZOOM_LEVELS[0]
        for expected in ZOOM_LEVELS[1:]:
            level = zoom_step(level, 1)
            assert level == expected


class TestCellAtCoords:
    def test_top_left_corner(self):
        r, c = cell_at_coords(0, 0, 16, 4, 4)
        assert (r, c) == (0, 0)

    def test_within_bounds(self):
        r, c = cell_at_coords(33, 17, 16, 4, 4)
        assert (r, c) == (1, 2)

    def test_out_of_bounds(self):
        r, c = cell_at_coords(100, 100, 16, 4, 4)
        assert (r, c) == (None, None)

    def test_negative_coords(self):
        r, c = cell_at_coords(-5, 10, 16, 4, 4)
        assert (r, c) == (None, None)


class TestFitZoomLevel:
    def test_small_grid_fits_large(self):
        level = fit_zoom_level(8, 8, 800, 600)
        assert level >= 16

    def test_large_grid_zooms_out(self):
        level = fit_zoom_level(256, 256, 800, 600)
        assert level < 16

    def test_result_is_valid_zoom_level(self):
        level = fit_zoom_level(32, 32, 800, 600)
        assert level in ZOOM_LEVELS


class TestCursorPreviewColor:
    def test_alias_resolves_to_hex(self):
        palette = Palette({"R": "#CC3333"})
        assert cursor_preview_color("R", palette) == "#CC3333"

    def test_transparent_returns_indicator(self):
        palette = Palette()
        color = cursor_preview_color(".", palette)
        assert color == "#FF6666"

    def test_inline_hex_returned_as_is(self):
        palette = Palette()
        assert cursor_preview_color("#AABBCC", palette) == "#AABBCC"


class TestToolConstants:
    def test_tools_are_distinct(self):
        assert TOOL_BRUSH != TOOL_EYEDROPPER
        assert TOOL_BRUSH != TOOL_FILL
        assert TOOL_EYEDROPPER != TOOL_FILL


class TestEyedropperPick:
    def test_picks_alias(self):
        grid = Grid.blank(4, 4)
        grid.set(1, 2, "R")
        assert eyedropper_pick(grid, 1, 2) == "R"

    def test_picks_transparent(self):
        grid = Grid.blank(4, 4)
        assert eyedropper_pick(grid, 0, 0) == TRANSPARENT

    def test_picks_inline_hex(self):
        grid = Grid.blank(4, 4)
        grid.set(0, 0, "#AABB11")
        assert eyedropper_pick(grid, 0, 0) == "#AABB11"

    def test_returns_none_for_invalid_coords(self):
        grid = Grid.blank(4, 4)
        assert eyedropper_pick(grid, None, None) is None


class TestPaletteKeyToIndex:
    def test_key_1_returns_0(self):
        assert palette_key_to_index("1") == 0

    def test_key_9_returns_8(self):
        assert palette_key_to_index("9") == 8

    def test_key_0_returns_9(self):
        assert palette_key_to_index("0") == 9

    def test_invalid_key_returns_none(self):
        assert palette_key_to_index("a") is None


class TestPaletteIndexToAlias:
    def test_index_0_is_first_alias(self):
        aliases = ["R", "B", "G"]
        assert palette_index_to_alias(0, aliases) == "R"

    def test_index_out_of_range(self):
        aliases = ["R", "B"]
        assert palette_index_to_alias(5, aliases) is None

    def test_empty_list(self):
        assert palette_index_to_alias(0, []) is None


# ===================================================================
# Frame strip pure functions
# ===================================================================

class TestRenderFrameThumbnail:
    def test_basic_resolution(self):
        """Resolves grid data through palette to hex colors."""
        palette = Palette({"R": "#FF0000", "B": "#0000FF"})
        grid_data = [["R", "B"], [".", "R"]]
        colors = render_frame_thumbnail(grid_data, palette)
        assert colors[0][0] == "#FF0000"
        assert colors[0][1] == "#0000FF"
        assert colors[1][0] is None  # transparent
        assert colors[1][1] == "#FF0000"

    def test_all_transparent(self):
        """All transparent returns all None."""
        palette = Palette()
        grid_data = [[".", "."], [".", "."]]
        colors = render_frame_thumbnail(grid_data, palette)
        assert all(c is None for row in colors for c in row)


class TestFrameStripLayout:
    def test_basic_layout(self):
        """Returns positions for thumbnails."""
        positions = frame_strip_layout(3, thumb_size=32, padding=4)
        assert len(positions) == 3
        assert positions[0] == 4  # first x position with padding
        assert positions[1] == 4 + 32 + 4
        assert positions[2] == 4 + (32 + 4) * 2

    def test_single_frame(self):
        """Single frame has one position."""
        positions = frame_strip_layout(1, thumb_size=32, padding=4)
        assert len(positions) == 1

    def test_zero_frames(self):
        """Zero frames returns empty list."""
        positions = frame_strip_layout(0, thumb_size=32, padding=4)
        assert positions == []
