"""ICO rendering: multi-size icon generation for .ico export."""

from PIL import Image

from gridfab.render.export import render_export

DEFAULT_ICO_SIZES = [16, 32, 48, 256]


def render_ico(
    colors: list[list[str | None]],
    width: int,
    height: int,
    sizes: list[int] | None = None,
) -> list[Image.Image]:
    """Render a resolved color grid to multiple icon sizes.

    The grid must be square (width == height). For each target size,
    renders at the best integer scale and resizes to exact dimensions.

    Returns a list of RGBA PIL Images, one per requested size.
    """
    if width != height:
        raise ValueError(
            f"Icon export requires a square grid, got {width}x{height}"
        )

    if sizes is None:
        sizes = DEFAULT_ICO_SIZES

    images = []
    for size in sizes:
        scale = max(1, size // width)
        img = render_export(colors, width, height, scale=scale)
        img = img.resize((size, size), Image.NEAREST)
        images.append(img)

    return images
