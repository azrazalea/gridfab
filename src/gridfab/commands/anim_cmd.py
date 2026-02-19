"""Animation management commands: add, list, delete, sheet, gif export."""

import json
from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.core.animation import (
    discover_frames,
    frame_path,
    load_animations,
    save_animations,
    validate_animation,
)


def cmd_anim_add(
    directory: Path,
    name: str,
    frames: list[int],
    fps: int = 8,
    loop: bool = True,
) -> None:
    """Add a named animation to animation.json."""
    existing_frames = discover_frames(directory)
    if not existing_frames:
        raise ValueError(
            "no frames found — use 'gridfab frame add' to create frames first"
        )

    validate_animation(name, frames, existing_frames)

    anims = load_animations(directory)
    if name in anims:
        raise ValueError(
            f"animation '{name}' already exists — delete it first or use a different name"
        )

    anims[name] = {"frames": frames, "fps": fps, "loop": loop}
    save_animations(directory, anims)
    print(f"Animation '{name}' added ({len(frames)} frames, {fps} FPS, loop={loop}).")


def cmd_anim_list(directory: Path) -> None:
    """Print all defined animations."""
    anims = load_animations(directory)
    if not anims:
        print("No animations defined. Use 'gridfab anim add' to create one.")
        return

    for name, anim in anims.items():
        frames = anim["frames"]
        fps = anim.get("fps", 8)
        loop = anim.get("loop", True)
        print(f"  {name}: frames={frames}, fps={fps}, loop={loop}")


def cmd_anim_delete(directory: Path, name: str) -> None:
    """Delete a named animation from animation.json."""
    anims = load_animations(directory)
    if name not in anims:
        raise ValueError(
            f"animation '{name}' not found"
        )

    del anims[name]
    save_animations(directory, anims)
    print(f"Animation '{name}' deleted.")


def _load_anim_frames(directory: Path, name: str) -> tuple[list[list[list[str | None]]], dict]:
    """Load resolved color grids for all frames of a named animation.

    Returns (frames_colors, anim_dict).
    """
    anims = load_animations(directory)
    if name not in anims:
        raise ValueError(f"animation '{name}' not found")

    anim = anims[name]
    palette_path = directory / "palette.txt"
    palette = Palette.load(palette_path)
    frames_colors = []
    for f in anim["frames"]:
        grid = Grid.load(frame_path(directory, f), palette_path=palette_path)
        colors = palette.resolve_grid(grid.data)
        frames_colors.append(colors)
    return frames_colors, anim


def cmd_anim_sheet(
    directory: Path,
    name: str,
    scale: int = 1,
    layout: str = "horizontal",
    columns: int | None = None,
) -> None:
    """Export a spritesheet PNG + JSON metadata for a named animation."""
    from gridfab.render.spritesheet import render_spritesheet

    frames_colors, anim = _load_anim_frames(directory, name)

    # Get dimensions from first frame
    grid = Grid.load(frame_path(directory, anim["frames"][0]),
                     palette_path=directory / "palette.txt")
    fps = anim.get("fps", 8)
    loop = anim.get("loop", True)

    img, meta = render_spritesheet(
        frames_colors, grid.width, grid.height,
        scale=scale, layout=layout, columns=columns,
        anim_name=name, fps=fps, loop=loop,
    )

    # Add sprite name to metadata
    meta["sprite"] = name

    png_path = directory / f"{name}_sheet.png"
    json_path = directory / f"{name}_sheet.json"
    img.save(str(png_path))
    with open(json_path, "w", newline="\n") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print(f"Spritesheet exported: {png_path} ({img.size[0]}x{img.size[1]})")
    print(f"Metadata: {json_path}")


def cmd_anim_sheets(
    directory: Path,
    scale: int = 1,
    layout: str = "horizontal",
) -> None:
    """Export spritesheets for all defined animations."""
    anims = load_animations(directory)
    if not anims:
        raise ValueError("no animations defined")

    for name in anims:
        cmd_anim_sheet(directory, name, scale=scale, layout=layout)


def cmd_anim_gif(
    directory: Path,
    name: str,
    scale: int = 1,
) -> None:
    """Export an animated GIF for a named animation."""
    from gridfab.render.gif import render_gif

    frames_colors, anim = _load_anim_frames(directory, name)

    grid = Grid.load(frame_path(directory, anim["frames"][0]),
                     palette_path=directory / "palette.txt")
    fps = anim.get("fps", 8)
    loop = anim.get("loop", True)

    images, duration = render_gif(
        frames_colors, grid.width, grid.height,
        scale=scale, fps=fps, loop=loop,
    )

    gif_path = directory / f"{name}.gif"
    # Save animated GIF
    loop_count = 0 if loop else 1  # 0 = infinite loop in GIF spec
    images[0].save(
        str(gif_path),
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=loop_count,
        disposal=2,  # restore to background between frames
    )
    print(f"GIF exported: {gif_path} ({len(images)} frames, {fps} FPS)")
