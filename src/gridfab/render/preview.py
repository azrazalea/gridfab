"""Preview rendering with checkerboard background for transparent pixels."""

from PIL import Image

from gridfab.core.palette import hex_to_rgb

PREVIEW_SCALE = 8
CHECKER_LIGHT = (220, 220, 220)
CHECKER_DARK = (180, 180, 180)
CHECKER_SIZE = 4  # checkerboard square size in source pixels


def render_preview(
    colors: list[list[str | None]],
    width: int,
    height: int,
    scale: int = PREVIEW_SCALE,
) -> Image.Image:
    """Render a resolved color grid to a preview image.

    Transparent pixels are shown as a checkerboard pattern.
    Returns an RGBA PIL Image.
    """
    img_w = width * scale
    img_h = height * scale
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))

    for r, row in enumerate(colors):
        for c, color in enumerate(row):
            if color is not None:
                rgba = (*hex_to_rgb(color), 255)
            else:
                checker = ((r // CHECKER_SIZE) + (c // CHECKER_SIZE)) % 2
                rgba = (*(CHECKER_LIGHT if checker == 0 else CHECKER_DARK), 255)

            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((c * scale + dx, r * scale + dy), rgba)

    return img
