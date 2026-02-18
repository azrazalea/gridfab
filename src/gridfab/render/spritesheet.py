"""Spritesheet assembly: pack animation frames into a single PNG."""

import math

from PIL import Image

from gridfab.render.export import render_export


def render_spritesheet(
    frames_colors: list[list[list[str | None]]],
    width: int,
    height: int,
    scale: int = 1,
    layout: str = "horizontal",
    columns: int | None = None,
    anim_name: str = "default",
    fps: int = 8,
    loop: bool = True,
) -> tuple[Image.Image, dict]:
    """Assemble frames into a spritesheet PNG with metadata.

    Args:
        frames_colors: List of resolved color grids (one per frame)
        width, height: Grid dimensions (before scaling)
        scale: Pixel scale factor
        layout: "horizontal", "vertical", or "grid"
        columns: Columns for grid layout (default: auto)
        anim_name: Name for the animation in metadata
        fps: Frames per second
        loop: Whether the animation loops

    Returns:
        (image, metadata_dict) tuple
    """
    n = len(frames_colors)
    fw = width * scale
    fh = height * scale
    duration_ms = round(1000 / fps)

    # Compute layout
    if layout == "vertical":
        cols = 1
        rows = n
    elif layout == "grid":
        cols = columns or math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
    else:  # horizontal
        cols = n
        rows = 1

    img_w = cols * fw
    img_h = rows * fh
    sheet = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))

    frame_meta = []
    for i, colors in enumerate(frames_colors):
        if layout == "vertical":
            col, row = 0, i
        elif layout == "grid":
            col = i % cols
            row = i // cols
        else:
            col, row = i, 0

        x = col * fw
        y = row * fh
        frame_img = render_export(colors, width, height, scale)
        sheet.paste(frame_img, (x, y))
        frame_meta.append({
            "x": x, "y": y, "w": fw, "h": fh,
            "duration": duration_ms,
        })

    metadata = {
        "frame_size": {"w": fw, "h": fh},
        "animations": {
            anim_name: {
                "frames": frame_meta,
                "loop": loop,
            }
        },
    }

    return sheet, metadata
