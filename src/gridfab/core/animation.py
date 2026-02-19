"""Animation: frame discovery, state management, and animation metadata.

Multi-frame sprites use frame_NNN.txt files (001-999, 1-based, zero-padded).
All frames share a single palette.txt. Named animations are stored in
animation.json with frame lists, FPS, and loop flags.

A directory with only grid.txt is a valid single-frame sprite. Animation
features activate when frame_NNN.txt files exist.
"""

import json
import re
from pathlib import Path

_FRAME_RE = re.compile(r"^frame_(\d{3})\.txt$")

STATE_FILE = ".gridfab_state"
ANIM_FILE = "animation.json"


def discover_frames(directory: Path) -> list[int]:
    """Scan directory for frame_NNN.txt files, return sorted frame numbers."""
    frames = []
    for p in directory.iterdir():
        m = _FRAME_RE.match(p.name)
        if m:
            frames.append(int(m.group(1)))
    frames.sort()
    return frames


def is_animated(directory: Path) -> bool:
    """True if any frame_NNN.txt files exist in the directory."""
    return len(discover_frames(directory)) > 0


def frame_path(directory: Path, frame_num: int) -> Path:
    """Return the path for a given frame number (zero-padded, 1-based)."""
    return directory / f"frame_{frame_num:03d}.txt"


def resolve_grid_path(directory: Path, frame: int | None = None) -> Path:
    """Resolve the correct grid file path.

    Priority:
    1. If frame is given explicitly (--frame flag), use that frame file
    2. If animated dir (has frame_NNN.txt), read active frame from .gridfab_state
    3. If non-animated dir, use grid.txt

    Raises FileNotFoundError if the resolved file doesn't exist.
    """
    if frame is not None:
        path = frame_path(directory, frame)
        if not path.exists():
            raise FileNotFoundError(
                f"{path.name} not found in {directory}"
            )
        return path

    frames = discover_frames(directory)
    if frames:
        state = load_state(directory)
        active = state.get("active_frame", frames[0])
        path = frame_path(directory, active)
        if not path.exists():
            raise FileNotFoundError(
                f"{path.name} not found in {directory}"
            )
        return path

    return directory / "grid.txt"


def load_state(directory: Path) -> dict:
    """Load .gridfab_state JSON, or return empty dict if missing."""
    path = directory / STATE_FILE
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(directory: Path, state: dict) -> None:
    """Write .gridfab_state JSON."""
    path = directory / STATE_FILE
    with open(path, "w", newline="\n") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def load_animations(directory: Path) -> dict:
    """Load animation definitions from root animation.json and subdirectories.

    Old-style animations (in root animation.json) and new-style subdirectory
    animations coexist. Subdir animations get their name from the folder name.
    """
    anims = {}
    path = directory / ANIM_FILE
    if path.exists():
        with open(path) as f:
            anims = json.load(f)

    # Discover animation subdirectories
    for subdir in discover_anim_dirs(directory):
        name = subdir.name
        if name not in anims:
            anims[name] = load_subdir_animation(subdir)

    return anims


def save_animations(directory: Path, anims: dict) -> None:
    """Write animation.json."""
    path = directory / ANIM_FILE
    with open(path, "w", newline="\n") as f:
        json.dump(anims, f, indent=2)
        f.write("\n")


def validate_animation(
    name: str, frames: list[int], existing_frames: list[int]
) -> None:
    """Validate that an animation definition is valid.

    Raises ValueError if frames list is empty or references non-existent frames.
    """
    if not frames:
        raise ValueError(
            f"animation '{name}' must have at least one frame"
        )
    existing = set(existing_frames)
    for f in frames:
        if f not in existing:
            raise ValueError(
                f"animation '{name}' references frame {f}, "
                f"but it doesn't exist (available: {sorted(existing)})"
            )


def resolve_palette_path(directory: Path) -> Path:
    """Find palette.txt in directory or its parent.

    Resolves the path first so that Path(".") works correctly.
    Raises FileNotFoundError if neither location has palette.txt.
    """
    directory = directory.resolve()
    local = directory / "palette.txt"
    if local.exists():
        return local
    parent = directory.parent / "palette.txt"
    if parent.exists():
        return parent
    raise FileNotFoundError(
        f"palette.txt not found in {directory} or {directory.parent}"
    )


def resolve_config_path(directory: Path) -> Path | None:
    """Find gridfab.json in directory or its parent. Returns None if missing."""
    directory = directory.resolve()
    local = directory / "gridfab.json"
    if local.exists():
        return local
    parent = directory.parent / "gridfab.json"
    if parent.exists():
        return parent
    return None


def is_anim_subdir(directory: Path) -> bool:
    """True if directory is an animation subdirectory of a sprite root.

    An animation subdirectory has frame_NNN.txt files or an animation.json,
    AND its parent is a sprite root (has grid.txt or frame_NNN.txt files).
    Resolves the path first so that Path(".") works correctly.
    """
    directory = directory.resolve()
    has_frames = bool(discover_frames(directory))
    has_anim_json = (directory / ANIM_FILE).exists()
    if not has_frames and not has_anim_json:
        return False
    parent = directory.parent
    if (parent / "grid.txt").exists():
        return True
    if discover_frames(parent):
        return True
    return False


def discover_anim_dirs(directory: Path) -> list[Path]:
    """Find subdirectories that contain frame_NNN.txt files. Returns sorted list."""
    result = []
    if not directory.is_dir():
        return result
    for child in directory.iterdir():
        if child.is_dir() and discover_frames(child):
            result.append(child)
    result.sort(key=lambda p: p.name)
    return result


def parse_frame_ref(ref) -> tuple[str, int]:
    """Parse a frame reference from animation.json.

    - int → ("local", N)
    - "base:N" → ("base", N)

    Raises ValueError for invalid references.
    """
    if isinstance(ref, int):
        return ("local", ref)
    if isinstance(ref, str) and ref.startswith("base:"):
        try:
            num = int(ref[5:])
            return ("base", num)
        except ValueError:
            pass
    raise ValueError(f"invalid frame reference: {ref!r}")


def resolve_frame_path(ref, directory: Path) -> Path:
    """Resolve a frame reference to a file path.

    Resolves the path first so that Path(".") works correctly.
    - int → directory/frame_NNN.txt
    - "base:N" → directory.parent/frame_NNN.txt
    """
    directory = directory.resolve()
    kind, num = parse_frame_ref(ref)
    if kind == "base":
        return frame_path(directory.parent, num)
    return frame_path(directory, num)


def load_subdir_animation(directory: Path) -> dict:
    """Load simplified animation.json from an animation subdirectory.

    Returns {"frames": [...], "fps": N, "loop": bool}.
    If animation.json is missing, returns a default empty structure.
    """
    path = directory / ANIM_FILE
    if not path.exists():
        return {"frames": [], "fps": 8, "loop": True}
    with open(path) as f:
        data = json.load(f)
    data.setdefault("fps", 8)
    data.setdefault("loop", True)
    data.setdefault("frames", [])
    return data


def max_frame_number(directory: Path) -> int:
    """Return the highest frame number, or 0 if no frames exist."""
    frames = discover_frames(directory)
    return frames[-1] if frames else 0


def swap_frame_files(directory: Path, frame_a: int, frame_b: int) -> None:
    """Swap two frame files using a temp name to avoid collision.

    Raises FileNotFoundError if either frame file doesn't exist.
    """
    if frame_a == frame_b:
        return
    path_a = frame_path(directory, frame_a)
    path_b = frame_path(directory, frame_b)
    if not path_a.exists():
        raise FileNotFoundError(f"{path_a.name} not found in {directory}")
    if not path_b.exists():
        raise FileNotFoundError(f"{path_b.name} not found in {directory}")
    tmp = directory / f"frame_{frame_a:03d}.txt.tmp"
    path_a.rename(tmp)
    path_b.rename(path_a)
    tmp.rename(path_b)


def update_animations_after_swap(animations: dict, frame_a: int, frame_b: int) -> dict:
    """Update animation frame references after a swap.

    Every occurrence of frame_a becomes frame_b and vice versa.
    Returns a new dict (does not mutate input).
    """
    if frame_a == frame_b:
        return animations
    result = {}
    for name, anim in animations.items():
        new_anim = dict(anim)
        new_frames = []
        for f in anim.get("frames", []):
            if f == frame_a:
                new_frames.append(frame_b)
            elif f == frame_b:
                new_frames.append(frame_a)
            else:
                new_frames.append(f)
        new_anim["frames"] = new_frames
        result[name] = new_anim
    return result
