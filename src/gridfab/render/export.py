"""Export rendering with true transparency for game engine use."""

from PIL import Image

from gridfab.core.palette import hex_to_rgb


def render_export(
    colors: list[list[str | None]],
    width: int,
    height: int,
    scale: int = 1,
) -> Image.Image:
    """Render a resolved color grid to an export image.

    Transparent pixels remain fully transparent (RGBA 0,0,0,0).
    Returns an RGBA PIL Image.
    """
    img_w = width * scale
    img_h = height * scale
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))

    for r, row in enumerate(colors):
        for c, color in enumerate(row):
            if color is None:
                continue
            rgba = (*hex_to_rgb(color), 255)
            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((c * scale + dx, r * scale + dy), rgba)

    return img
