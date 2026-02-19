"""Frame management commands: add, delete, select, list."""

from pathlib import Path

from gridfab.core.grid import Grid
from gridfab.core.animation import (
    discover_frames,
    is_animated,
    is_anim_subdir,
    frame_path,
    max_frame_number,
    load_state,
    save_state,
    load_animations,
    save_animations,
    load_subdir_animation,
    resolve_palette_path,
)


import json


def _update_subdir_anim_add(directory: Path, frame_num: int) -> None:
    """Append a local frame number to the subdir's animation.json frame list."""
    anim = load_subdir_animation(directory)
    anim["frames"].append(frame_num)
    anim_path = directory / "animation.json"
    with open(anim_path, "w", newline="\n") as f:
        json.dump(anim, f, indent=2)
        f.write("\n")


def _update_subdir_anim_delete(directory: Path, frame_num: int) -> None:
    """Remove a local frame from subdir's animation.json and renumber higher refs."""
    anim = load_subdir_animation(directory)
    new_frames = []
    for ref in anim["frames"]:
        if isinstance(ref, int):
            if ref == frame_num:
                continue
            elif ref > frame_num:
                new_frames.append(ref - 1)
            else:
                new_frames.append(ref)
        else:
            # base:N references are unaffected by local renumbering
            new_frames.append(ref)
    anim["frames"] = new_frames
    anim_path = directory / "animation.json"
    with open(anim_path, "w", newline="\n") as f:
        json.dump(anim, f, indent=2)
        f.write("\n")


def _get_dimensions_for_subdir(directory: Path) -> tuple[int, int]:
    """Get grid dimensions for a new frame in an animation subdirectory.

    Uses existing local frames, or falls back to parent frames/config.
    """
    palette_path = resolve_palette_path(directory)
    frames = discover_frames(directory)
    if frames:
        src = Grid.load(frame_path(directory, frames[0]), palette_path=palette_path)
        return src.width, src.height
    # Fall back to parent frames
    parent = directory.parent
    parent_frames = discover_frames(parent)
    if parent_frames:
        src = Grid.load(frame_path(parent, parent_frames[0]), palette_path=palette_path)
        return src.width, src.height
    # Fall back to grid.txt
    grid_txt = parent / "grid.txt"
    if grid_txt.exists():
        src = Grid.load(grid_txt, palette_path=palette_path)
        return src.width, src.height
    # Fall back to config
    from gridfab.core.grid import get_grid_dimensions
    return get_grid_dimensions(directory)


def cmd_frame_add(
    directory: Path,
    from_frame: int | None = None,
    blank: bool = False,
) -> None:
    """Add a new frame to the sprite.

    First call on a grid.txt-only directory renames grid.txt -> frame_001.txt
    to transition into animated mode. Then adds a new frame:
    - Default: copy active frame
    - --from N: copy from specific frame
    - --blank: create transparent frame with same dimensions

    In an animation subdirectory, also updates the subdir's animation.json.
    """
    in_subdir = is_anim_subdir(directory)
    palette_path = resolve_palette_path(directory)
    frames = discover_frames(directory)

    if not frames and not in_subdir:
        # First frame add: convert from single-frame to animated
        grid_path = directory / "grid.txt"
        if not grid_path.exists():
            raise FileNotFoundError(
                f"No grid.txt found in {directory} — run 'gridfab init' first"
            )
        grid_path.rename(frame_path(directory, 1))
        frames = [1]
        save_state(directory, {"active_frame": 1})

    new_num = max_frame_number(directory) + 1
    new_path = frame_path(directory, new_num)

    if blank or (in_subdir and not frames):
        # For subdir with no frames, create blank with inherited dimensions
        if frames:
            src = Grid.load(frame_path(directory, frames[0]), palette_path=palette_path)
            w, h = src.width, src.height
        else:
            w, h = _get_dimensions_for_subdir(directory)
        new_grid = Grid.blank(w, h)
        new_grid.save(new_path)
    elif from_frame is not None:
        src_path = frame_path(directory, from_frame)
        if not src_path.exists():
            raise FileNotFoundError(
                f"frame {from_frame} does not exist "
                f"(available: {frames})"
            )
        src = Grid.load(src_path, palette_path=palette_path)
        src.save(new_path)
    else:
        # Copy active frame
        state = load_state(directory)
        active = state.get("active_frame", frames[0])
        src = Grid.load(frame_path(directory, active), palette_path=palette_path)
        src.save(new_path)

    save_state(directory, {"active_frame": new_num})

    # In an animation subdir, auto-append to animation.json
    if in_subdir:
        _update_subdir_anim_add(directory, new_num)

    print(f"Added frame {new_num} ({new_path.name}).")


def cmd_frame_delete(directory: Path, frame_num: int) -> None:
    """Delete a frame and renumber remaining frames contiguously.

    Updates .gridfab_state and animation.json references.
    In an animation subdirectory, also updates the subdir's animation.json.
    Cannot delete the only remaining frame.
    """
    in_subdir = is_anim_subdir(directory)
    frames = discover_frames(directory)

    if frame_num not in frames:
        raise ValueError(
            f"frame {frame_num} does not exist (available: {frames})"
        )

    if len(frames) == 1:
        raise ValueError("cannot delete the only frame")

    # Delete the file
    frame_path(directory, frame_num).unlink()

    # Renumber higher frames downward using temp names to avoid collision
    higher = [f for f in frames if f > frame_num]
    # First pass: rename to temp names
    for f in higher:
        src = frame_path(directory, f)
        tmp = directory / f"{src.name}.tmp"
        src.rename(tmp)
    # Second pass: rename from temp to final names
    for f in higher:
        tmp = directory / f"frame_{f:03d}.txt.tmp"
        dst = frame_path(directory, f - 1)
        tmp.rename(dst)

    # Update subdir animation.json if in an animation subdirectory
    if in_subdir:
        _update_subdir_anim_delete(directory, frame_num)
    else:
        # Update root animation.json: remove refs to deleted frame, decrement higher
        anims = load_animations(directory)
        if anims:
            for name, anim in anims.items():
                new_frames = []
                for f in anim["frames"]:
                    if f == frame_num:
                        continue  # removed
                    elif f > frame_num:
                        new_frames.append(f - 1)
                    else:
                        new_frames.append(f)
                anim["frames"] = new_frames
            # Remove animations with no frames left
            anims = {k: v for k, v in anims.items() if v["frames"]}
            save_animations(directory, anims)

    # Update state
    state = load_state(directory)
    active = state.get("active_frame", 1)
    if active == frame_num or active > max_frame_number(directory):
        active = 1
    elif active > frame_num:
        active -= 1
    save_state(directory, {"active_frame": active})

    print(f"Deleted frame {frame_num}.")


def cmd_frame_select(directory: Path, frame_num: int) -> None:
    """Set the active frame."""
    frames = discover_frames(directory)
    if frame_num not in frames:
        raise ValueError(
            f"frame {frame_num} does not exist (available: {frames})"
        )
    save_state(directory, {"active_frame": frame_num})
    print(f"Active frame set to {frame_num}.")


def cmd_frame_copy_rect(
    directory: Path,
    r0: int, c0: int, r1: int, c1: int,
    src_frame: int,
    dst_frame: int,
) -> None:
    """Copy a rectangular region from one frame to another."""
    frames = discover_frames(directory)
    for f in (src_frame, dst_frame):
        if f not in frames:
            raise ValueError(
                f"frame {f} does not exist (available: {frames})"
            )

    palette_path = resolve_palette_path(directory)
    src = Grid.load(frame_path(directory, src_frame), palette_path=palette_path)
    dst = Grid.load(frame_path(directory, dst_frame), palette_path=palette_path)

    # Validate bounds against source grid
    for label, r, c in [("r0", r0, c0), ("r1", r1, c1)]:
        if r < 0 or r >= src.height or c < 0 or c >= src.width:
            raise ValueError(f"{label} ({r},{c}) out of bounds for {src.width}x{src.height} grid")

    if dst.width != src.width or dst.height != src.height:
        raise ValueError("source and destination frames have different dimensions")

    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            dst.data[r][c] = src.data[r][c]

    dst.save(frame_path(directory, dst_frame))
    w = c1 - c0 + 1
    h = r1 - r0 + 1
    print(f"Copied {w}x{h} rect ({r0},{c0})-({r1},{c1}) from frame {src_frame} to frame {dst_frame}.")


def cmd_frame_list(directory: Path) -> None:
    """Print all frames with active marker."""
    frames = discover_frames(directory)
    if not frames:
        print("No frames found (single-frame sprite with grid.txt).")
        return

    state = load_state(directory)
    active = state.get("active_frame", frames[0])

    for f in frames:
        marker = " *" if f == active else ""
        print(f"  {frame_path(directory, f).name}{marker}")
