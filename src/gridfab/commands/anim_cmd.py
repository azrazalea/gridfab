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
    resolve_palette_path,
    is_anim_subdir,
    load_subdir_animation,
    resolve_frame_path,
    discover_anim_dirs,
    parse_frame_ref,
)


def cmd_anim_create(
    directory: Path,
    name: str,
    fps: int = 8,
    loop: bool = True,
) -> None:
    """Create a new animation subdirectory.

    Creates directory/name/ with an empty animation.json.
    Raises FileExistsError if the subdirectory already exists.
    """
    subdir = directory / name
    if subdir.exists():
        raise FileExistsError(
            f"animation directory '{name}' already exists in {directory}"
        )
    subdir.mkdir()
    anim_data = {"frames": [], "fps": fps, "loop": loop}
    with open(subdir / "animation.json", "w", newline="\n") as f:
        json.dump(anim_data, f, indent=2)
        f.write("\n")
    print(f"Animation '{name}' created at {subdir}")
    print(f"  Add frames with: gridfab frame add {subdir}")


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

    Handles both old-style (root animation.json with int frame refs) and
    new-style (subdir animation.json with base:N refs).
    Returns (frames_colors, anim_dict).
    """
    # Check if this is an animation subdirectory
    resolved = directory.resolve()
    if is_anim_subdir(resolved) and name == resolved.name:
        anim = load_subdir_animation(directory)
    else:
        anims = load_animations(directory)
        if name not in anims:
            raise ValueError(f"animation '{name}' not found")
        anim = anims[name]

    palette_path = resolve_palette_path(directory)
    palette = Palette.load(palette_path)
    frames_colors = []
    for ref in anim["frames"]:
        path = resolve_frame_path(ref, directory)
        grid = Grid.load(path, palette_path=palette_path)
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

    # Get dimensions from first frame (resolving base refs)
    first_ref = anim["frames"][0]
    first_path = resolve_frame_path(first_ref, directory)
    palette_path = resolve_palette_path(directory)
    grid = Grid.load(first_path, palette_path=palette_path)
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
    """Export spritesheets for all defined animations.

    Exports both old-style (root animation.json) and new-style (subdirectory)
    animations. Subdirectory animations are exported into their subdirectory.
    """
    # Export root-level animations from animation.json
    root_path = directory / "animation.json"
    if root_path.exists():
        with open(root_path) as f:
            root_anims = json.load(f)
        for name in root_anims:
            cmd_anim_sheet(directory, name, scale=scale, layout=layout)

    # Export subdirectory animations
    for subdir in discover_anim_dirs(directory):
        name = subdir.name
        cmd_anim_sheet(subdir, name, scale=scale, layout=layout)

    # Check if anything was exported
    has_root = root_path.exists() and bool(json.loads(root_path.read_text()))
    has_subdirs = bool(discover_anim_dirs(directory))
    if not has_root and not has_subdirs:
        raise ValueError("no animations defined")


def cmd_anim_gif(
    directory: Path,
    name: str,
    scale: int = 1,
) -> None:
    """Export an animated GIF for a named animation."""
    from gridfab.render.gif import render_gif

    frames_colors, anim = _load_anim_frames(directory, name)

    first_ref = anim["frames"][0]
    first_path = resolve_frame_path(first_ref, directory)
    palette_path = resolve_palette_path(directory)
    grid = Grid.load(first_path, palette_path=palette_path)
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
