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
    """Load animation.json, or return empty dict if missing."""
    path = directory / ANIM_FILE
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


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


def max_frame_number(directory: Path) -> int:
    """Return the highest frame number, or 0 if no frames exist."""
    frames = discover_frames(directory)
    return frames[-1] if frames else 0
