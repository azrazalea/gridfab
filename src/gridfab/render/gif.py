"""Animated GIF rendering: convert animation frames to GIF."""

from PIL import Image

from gridfab.render.export import render_export


def render_gif(
    frames_colors: list[list[list[str | None]]],
    width: int,
    height: int,
    scale: int = 1,
    fps: int = 8,
    loop: bool = True,
) -> tuple[list[Image.Image], int]:
    """Render animation frames as a list of RGBA images for GIF assembly.

    Args:
        frames_colors: List of resolved color grids (one per frame)
        width, height: Grid dimensions (before scaling)
        scale: Pixel scale factor
        fps: Frames per second
        loop: Whether the animation loops (for metadata, not embedded here)

    Returns:
        (list_of_images, duration_ms) tuple
    """
    duration_ms = round(1000 / fps)
    images = []
    for colors in frames_colors:
        img = render_export(colors, width, height, scale)
        images.append(img)
    return images, duration_ms
