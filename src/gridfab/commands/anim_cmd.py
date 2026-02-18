"""Animation management commands: add, list, delete named animations."""

from pathlib import Path

from gridfab.core.animation import (
    discover_frames,
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
