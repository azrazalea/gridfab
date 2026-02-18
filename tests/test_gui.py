"""Tests for gridfab.gui — pure functions only (no tkinter event loop)."""

import pytest
from gridfab.gui import (
    checker_color, cell_display_color, _contrast_color,
    format_status_text, grid_line_config,
    zoom_step, cell_at_coords, fit_zoom_level,
    cursor_preview_color, eyedropper_pick,
    palette_key_to_index, palette_index_to_alias,
    render_frame_thumbnail, frame_strip_layout,
    blend_hex_colors, onion_skin_color,
    playback_frame_sequence, frame_interval_ms,
    frame_cell_at_coords, side_by_side_layout,
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


# ===================================================================
# Onion skinning pure functions
# ===================================================================

class TestBlendHexColors:
    def test_full_opacity_returns_fg(self):
        """Alpha 1.0 returns foreground color."""
        assert blend_hex_colors("#FF0000", "#0000FF", 1.0) == "#FF0000"

    def test_zero_opacity_returns_bg(self):
        """Alpha 0.0 returns background color."""
        assert blend_hex_colors("#FF0000", "#0000FF", 0.0) == "#0000FF"

    def test_half_blend(self):
        """50% alpha blends evenly."""
        result = blend_hex_colors("#FF0000", "#0000FF", 0.5)
        # Red channel: round(255*0.5) = 128, Blue: round(255*0.5) = 128
        assert result == "#800080"

    def test_quarter_blend(self):
        """25% alpha gives mostly background."""
        result = blend_hex_colors("#FFFFFF", "#000000", 0.25)
        # Each channel: round(255*0.25) = 64
        assert result == "#404040"


class TestOnionSkinColor:
    def test_prev_opaque_cur_opaque(self):
        """Both opaque: blends prev over current."""
        result = onion_skin_color("#FF0000", "#0000FF", 0.5)
        assert result == "#800080"

    def test_prev_transparent_cur_opaque(self):
        """Previous frame transparent, current opaque: returns current."""
        result = onion_skin_color(None, "#0000FF", 0.5)
        assert result == "#0000FF"

    def test_prev_opaque_cur_transparent(self):
        """Previous frame opaque, current transparent: blends prev over checker."""
        result = onion_skin_color("#FF0000", None, 0.25)
        # Should be a valid hex color
        assert result.startswith("#")
        assert len(result) == 7

    def test_both_transparent(self):
        """Both transparent: returns None (still transparent)."""
        result = onion_skin_color(None, None, 0.5)
        assert result is None


# ===================================================================
# Playback pure functions
# ===================================================================

class TestPlaybackFrameSequence:
    def test_named_animation(self):
        """Returns frame list for a named animation."""
        animations = {"walk": {"frames": [1, 2, 3], "fps": 8, "loop": True}}
        assert playback_frame_sequence(animations, "walk", [1, 2, 3, 4]) == [1, 2, 3]

    def test_all_frames_when_no_name(self):
        """None name returns all frames."""
        animations = {"walk": {"frames": [1, 2], "fps": 8, "loop": True}}
        assert playback_frame_sequence(animations, None, [1, 2, 3]) == [1, 2, 3]

    def test_unknown_animation_returns_all(self):
        """Unknown animation name falls back to all frames."""
        animations = {"walk": {"frames": [1, 2], "fps": 8, "loop": True}}
        assert playback_frame_sequence(animations, "run", [1, 2, 3]) == [1, 2, 3]

    def test_empty_all_frames(self):
        """Empty all_frames returns empty list."""
        assert playback_frame_sequence({}, None, []) == []


class TestFrameIntervalMs:
    def test_8_fps(self):
        """8 FPS = 125ms interval."""
        assert frame_interval_ms(8) == 125

    def test_1_fps(self):
        """1 FPS = 1000ms interval."""
        assert frame_interval_ms(1) == 1000

    def test_60_fps(self):
        """60 FPS = ~17ms interval."""
        assert frame_interval_ms(60) == 17

    def test_clamps_minimum(self):
        """0 or negative FPS clamps to 1 FPS (1000ms)."""
        assert frame_interval_ms(0) == 1000
        assert frame_interval_ms(-5) == 1000


# ===================================================================
# Side-by-side view pure functions
# ===================================================================

class TestFrameCellAtCoords:
    """Tests for frame_cell_at_coords — maps canvas pixel to (frame, row, col)."""

    def test_first_frame_top_left(self):
        """Click at (0,0) maps to frame 0, row 0, col 0."""
        f, r, c = frame_cell_at_coords(0, 0, 16, 4, 4, 3, 8)
        assert (f, r, c) == (0, 0, 0)

    def test_first_frame_interior(self):
        """Click inside first frame maps correctly."""
        # cell_size=16, so pixel (33, 17) = col 2, row 1
        f, r, c = frame_cell_at_coords(33, 17, 16, 4, 4, 3, 8)
        assert (f, r, c) == (0, 1, 2)

    def test_second_frame(self):
        """Click in second frame area maps to frame 1."""
        # Frame 0 occupies x=[0, 64), gap=[64, 72), Frame 1 occupies x=[72, 136)
        # grid_w=4, cell_size=16 → frame_pixel_w = 64, gap=8
        # x=72 is start of frame 1, col 0
        f, r, c = frame_cell_at_coords(72, 0, 16, 4, 4, 3, 8)
        assert (f, r, c) == (1, 0, 0)

    def test_third_frame(self):
        """Click in third frame maps to frame 2."""
        # Frame 2 starts at x = 2*(64+8) = 144
        f, r, c = frame_cell_at_coords(144, 0, 16, 4, 4, 3, 8)
        assert (f, r, c) == (2, 0, 0)

    def test_gap_between_frames(self):
        """Click in the gap returns (None, None, None)."""
        # Gap is at x=[64, 72)
        f, r, c = frame_cell_at_coords(65, 0, 16, 4, 4, 3, 8)
        assert (f, r, c) == (None, None, None)

    def test_below_grid(self):
        """Click below all frame grids returns (None, None, None)."""
        # grid_h=4, cell_size=16 → height=64, so y=65 is OOB
        f, r, c = frame_cell_at_coords(0, 65, 16, 4, 4, 3, 8)
        assert (f, r, c) == (None, None, None)

    def test_past_last_frame(self):
        """Click past the last frame returns (None, None, None)."""
        # 3 frames: total_w = 3*64 + 2*8 = 208, so x=210 is OOB
        f, r, c = frame_cell_at_coords(210, 0, 16, 4, 4, 3, 8)
        assert (f, r, c) == (None, None, None)

    def test_negative_coords(self):
        """Negative coordinates return (None, None, None)."""
        f, r, c = frame_cell_at_coords(-5, 10, 16, 4, 4, 3, 8)
        assert (f, r, c) == (None, None, None)

    def test_single_frame(self):
        """Single frame with no gaps works correctly."""
        f, r, c = frame_cell_at_coords(0, 0, 16, 4, 4, 1, 8)
        assert (f, r, c) == (0, 0, 0)

    def test_last_pixel_of_frame(self):
        """Last pixel of a frame still maps to that frame's last cell."""
        # Frame 0 last pixel: x=63, y=63 → col=3, row=3
        f, r, c = frame_cell_at_coords(63, 63, 16, 4, 4, 3, 8)
        assert (f, r, c) == (0, 3, 3)

    def test_wrapped_second_row(self):
        """Click in a frame on the second row with viewport wrapping."""
        # 4 frames, stride=72, viewport_w=150 → cols_per_row=2
        # Frame 2 is at row 1, col 0 → (x=0, y=72)
        f, r, c = frame_cell_at_coords(0, 72, 16, 4, 4, 4, 8, viewport_w=150)
        assert (f, r, c) == (2, 0, 0)

    def test_wrapped_second_row_second_col(self):
        """Click in frame 3 on second row, second column."""
        # Frame 3 is at row 1, col 1 → (x=72, y=72)
        f, r, c = frame_cell_at_coords(72, 72, 16, 4, 4, 4, 8, viewport_w=150)
        assert (f, r, c) == (3, 0, 0)

    def test_wrapped_gap_between_rows(self):
        """Click in vertical gap between rows returns None."""
        # Row 0 ends at y=64, row 1 starts at y=72, gap at y=65
        f, r, c = frame_cell_at_coords(0, 65, 16, 4, 4, 4, 8, viewport_w=150)
        assert (f, r, c) == (None, None, None)

    def test_wrapped_past_last_frame(self):
        """Click at position of nonexistent frame in partial last row."""
        # 3 frames, cols_per_row=2 → row 1 has only frame 2 at col 0
        # Click at col 1 of row 1 → frame_idx 3 which doesn't exist
        f, r, c = frame_cell_at_coords(72, 72, 16, 4, 4, 3, 8, viewport_w=150)
        assert (f, r, c) == (None, None, None)

    def test_wrapped_interior_cell(self):
        """Click inside a wrapped frame maps to correct cell."""
        # Frame 2 at row 1, col 0 → origin (0, 72)
        # Click at (33, 72+17) = (33, 89) → local (33, 17) → col 2, row 1
        f, r, c = frame_cell_at_coords(33, 89, 16, 4, 4, 4, 8, viewport_w=150)
        assert (f, r, c) == (2, 1, 2)


class TestSideBySideLayout:
    """Tests for side_by_side_layout — computes total dims and per-frame offsets."""

    def test_basic_three_frames(self):
        """Three frames with known dimensions (single row, no viewport)."""
        total_w, total_h, offsets = side_by_side_layout(3, 4, 4, 16, 8)
        # Each frame: 4*16 = 64px wide, 3 frames + 2 gaps of 8
        assert total_w == 3 * 64 + 2 * 8  # 208
        assert total_h == 4 * 16  # 64
        assert offsets == [(0, 0), (72, 0), (144, 0)]

    def test_single_frame(self):
        """Single frame has no gaps."""
        total_w, total_h, offsets = side_by_side_layout(1, 8, 8, 16, 8)
        assert total_w == 128
        assert total_h == 128
        assert offsets == [(0, 0)]

    def test_zero_frames(self):
        """Zero frames returns zero dimensions and empty offsets."""
        total_w, total_h, offsets = side_by_side_layout(0, 4, 4, 16, 8)
        assert total_w == 0
        assert total_h == 0
        assert offsets == []

    def test_offsets_x_monotonic_single_row(self):
        """X-offsets increase when all frames fit in one row."""
        _, _, offsets = side_by_side_layout(5, 4, 4, 16, 8)
        for i in range(1, len(offsets)):
            assert offsets[i][0] > offsets[i - 1][0]

    def test_gap_zero(self):
        """Zero gap means frames are adjacent."""
        total_w, _, offsets = side_by_side_layout(3, 4, 4, 16, 0)
        assert total_w == 3 * 64  # 192
        assert offsets == [(0, 0), (64, 0), (128, 0)]

    def test_wrapping_two_rows(self):
        """Narrow viewport forces frames into two rows."""
        # 4 frames, frame_pixel_w=64, gap=8, stride=72
        # viewport_w=150 → cols_per_row = 150//72 = 2
        total_w, total_h, offsets = side_by_side_layout(4, 4, 4, 16, 8, viewport_w=150)
        assert offsets == [(0, 0), (72, 0), (0, 72), (72, 72)]
        assert total_w == 2 * 72 - 8  # 136
        assert total_h == 2 * 72 - 8  # 136

    def test_wrapping_three_rows(self):
        """Very narrow viewport forces one frame per row."""
        # viewport_w=72 → cols_per_row = 72//72 = 1
        _, total_h, offsets = side_by_side_layout(3, 4, 4, 16, 8, viewport_w=72)
        assert offsets == [(0, 0), (0, 72), (0, 144)]
        assert total_h == 3 * 72 - 8  # 208

    def test_wrapping_partial_last_row(self):
        """Last row may have fewer frames than cols_per_row."""
        # 5 frames, viewport_w=220 → cols_per_row = 220//72 = 3
        _, _, offsets = side_by_side_layout(5, 4, 4, 16, 8, viewport_w=220)
        assert len(offsets) == 5
        # Row 0: frames 0,1,2
        assert offsets[0] == (0, 0)
        assert offsets[1] == (72, 0)
        assert offsets[2] == (144, 0)
        # Row 1: frames 3,4
        assert offsets[3] == (0, 72)
        assert offsets[4] == (72, 72)

    def test_wide_viewport_single_row(self):
        """A very wide viewport keeps everything in one row."""
        _, _, offsets = side_by_side_layout(3, 4, 4, 16, 8, viewport_w=9999)
        assert offsets == [(0, 0), (72, 0), (144, 0)]
