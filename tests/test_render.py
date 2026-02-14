"""Tests for gridfab.render — image output verification."""

import pytest
from gridfab.render.preview import render_preview, PREVIEW_SCALE, CHECKER_LIGHT, CHECKER_DARK
from gridfab.render.export import render_export
from gridfab.render.ico import render_ico
from gridfab.core.palette import hex_to_rgb


def _make_colors(width, height, fill=None):
    """Helper: create a resolved color grid."""
    return [[fill] * width for _ in range(height)]


class TestRenderExport:
    def test_image_dimensions(self):
        colors = _make_colors(4, 3, "#FF0000")
        img = render_export(colors, 4, 3, scale=1)
        assert img.size == (4, 3)

    def test_scaled_dimensions(self):
        colors = _make_colors(4, 3, "#FF0000")
        img = render_export(colors, 4, 3, scale=4)
        assert img.size == (16, 12)

    def test_correct_pixel_color(self):
        colors = _make_colors(2, 2, "#CC3333")
        img = render_export(colors, 2, 2, scale=1)
        r, g, b, a = img.getpixel((0, 0))
        assert (r, g, b) == hex_to_rgb("#CC3333")
        assert a == 255

    def test_transparent_pixels(self):
        colors = _make_colors(2, 2, None)
        img = render_export(colors, 2, 2, scale=1)
        r, g, b, a = img.getpixel((0, 0))
        assert a == 0

    def test_scale_fills_block(self):
        colors = [["#FF0000", None], [None, "#00FF00"]]
        img = render_export(colors, 2, 2, scale=4)
        # Top-left 4x4 block should all be red
        for dy in range(4):
            for dx in range(4):
                r, g, b, a = img.getpixel((dx, dy))
                assert (r, g, b, a) == (255, 0, 0, 255)
        # Top-right 4x4 block should be transparent
        r, g, b, a = img.getpixel((4, 0))
        assert a == 0

    def test_non_square_grid(self):
        colors = _make_colors(3, 5, "#AABBCC")
        img = render_export(colors, 3, 5, scale=2)
        assert img.size == (6, 10)


class TestRenderPreview:
    def test_image_dimensions(self):
        colors = _make_colors(4, 4, None)
        img = render_preview(colors, 4, 4, scale=PREVIEW_SCALE)
        assert img.size == (4 * PREVIEW_SCALE, 4 * PREVIEW_SCALE)

    def test_colored_pixel(self):
        colors = [["#FF0000"]]
        img = render_preview(colors, 1, 1, scale=1)
        r, g, b, a = img.getpixel((0, 0))
        assert (r, g, b) == (255, 0, 0)
        assert a == 255

    def test_transparent_shows_checkerboard(self):
        colors = [[None]]
        img = render_preview(colors, 1, 1, scale=1)
        r, g, b, a = img.getpixel((0, 0))
        # Should be one of the checker colors, not transparent
        assert a == 255
        assert (r, g, b) in (CHECKER_LIGHT, CHECKER_DARK)

    def test_checkerboard_alternates(self):
        # Use a grid large enough to span checker blocks
        colors = _make_colors(8, 8, None)
        img = render_preview(colors, 8, 8, scale=1)
        # Pixel at (0,0) and pixel at (4,0) should differ (different checker blocks)
        c1 = img.getpixel((0, 0))[:3]
        c2 = img.getpixel((4, 0))[:3]
        assert c1 != c2

    def test_not_transparent(self):
        """Preview should never have transparent pixels."""
        colors = _make_colors(4, 4, None)
        img = render_preview(colors, 4, 4, scale=1)
        for y in range(4):
            for x in range(4):
                assert img.getpixel((x, y))[3] == 255


class TestRenderIco:
    def test_returns_correct_number_of_images(self):
        colors = _make_colors(4, 4, "#FF0000")
        images = render_ico(colors, 4, 4)
        assert len(images) == 4  # default: [16, 32, 48, 256]

    def test_image_sizes(self):
        colors = _make_colors(4, 4, "#FF0000")
        images = render_ico(colors, 4, 4)
        expected_sizes = [16, 32, 48, 256]
        for img, size in zip(images, expected_sizes):
            assert img.size == (size, size)

    def test_rejects_non_square(self):
        colors = _make_colors(4, 3, "#FF0000")
        with pytest.raises(ValueError, match="square"):
            render_ico(colors, 4, 3)

    def test_custom_sizes(self):
        colors = _make_colors(4, 4, "#FF0000")
        images = render_ico(colors, 4, 4, sizes=[32, 64])
        assert len(images) == 2
        assert images[0].size == (32, 32)
        assert images[1].size == (64, 64)

    def test_pixel_colors_preserved(self):
        """A colored pixel should survive scaling and resize."""
        # 2x2 grid: top-left red, rest transparent
        colors = [["#FF0000", None], [None, None]]
        images = render_ico(colors, 2, 2, sizes=[16])
        img = images[0]
        # Top-left quadrant (0,0) should be red
        r, g, b, a = img.getpixel((0, 0))
        assert (r, g, b) == (255, 0, 0)
        assert a == 255
