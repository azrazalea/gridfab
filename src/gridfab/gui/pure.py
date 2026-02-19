"""Pure functions and constants for GridFab GUI — no tkinter imports."""

from pathlib import Path

from gridfab.core.grid import TRANSPARENT
from gridfab.core.palette import Palette
from gridfab.core.animation import discover_frames, ANIM_FILE
from gridfab.gui.i18n import _

ZOOM_LEVELS = [4, 8, 16, 24, 32, 48]
DEFAULT_CELL_SIZE = 16
CHECKER_LIGHT = "#DCDCDC"
CHECKER_DARK = "#B4B4B4"

TOOL_BRUSH = "Brush"
TOOL_EYEDROPPER = "Eyedropper"
TOOL_FILL = "Fill"

SWATCH_COLS = 3


def checker_color(r: int, c: int) -> str:
    """Return checkerboard color for a transparent cell."""
    return CHECKER_LIGHT if (r // 2 + c // 2) % 2 == 0 else CHECKER_DARK


def _contrast_color(hex_color: str) -> str:
    """Return black or white for readable text on the given background."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000000" if luminance > 128 else "#FFFFFF"


def format_status_text(
    cursor_pos: tuple[int, int] | None,
    selected: str,
    selected_hex: str | None,
    grid_w: int,
    grid_h: int,
    modified: bool,
    tool_name: str,
    zoom_pct: int,
    file_path: str,
) -> str:
    """Build the status bar text from current editor state (pure function)."""
    parts: list[str] = []
    if cursor_pos is not None:
        parts.append(f"({cursor_pos[0]}, {cursor_pos[1]})")
    if selected == TRANSPARENT:
        parts.append(_("Transparent"))
    else:
        color_str = selected
        if selected_hex:
            color_str += f" {selected_hex}"
        parts.append(color_str)
    parts.append(f"{grid_w}x{grid_h}")
    parts.append(f"{zoom_pct}%")
    parts.append(tool_name)
    if modified:
        parts.append(_("[Modified]"))
    parts.append(file_path)
    return "  |  ".join(parts)


def grid_line_config(visible: bool) -> dict:
    """Return canvas rectangle outline/width settings for grid lines."""
    if visible:
        return {"outline": "#333333", "width": 0.5}
    return {"outline": "", "width": 0}


def zoom_step(current: int, direction: int) -> int:
    """Return the next zoom level in the given direction (+1 or -1)."""
    try:
        idx = ZOOM_LEVELS.index(current)
    except ValueError:
        idx = ZOOM_LEVELS.index(DEFAULT_CELL_SIZE)
    new_idx = max(0, min(len(ZOOM_LEVELS) - 1, idx + direction))
    return ZOOM_LEVELS[new_idx]


def cell_at_coords(
    x: int, y: int, cell_size: int, w: int, h: int,
) -> tuple[int | None, int | None]:
    """Convert pixel coordinates to grid (row, col), or (None, None) if out of bounds."""
    if x < 0 or y < 0:
        return None, None
    c = x // cell_size
    r = y // cell_size
    if 0 <= r < h and 0 <= c < w:
        return r, c
    return None, None


def fit_zoom_level(grid_w: int, grid_h: int, viewport_w: int, viewport_h: int) -> int:
    """Find the largest zoom level that fits the grid in the viewport."""
    best = ZOOM_LEVELS[0]
    for level in ZOOM_LEVELS:
        if grid_w * level <= viewport_w and grid_h * level <= viewport_h:
            best = level
    return best


def cursor_preview_color(selected: str, palette: Palette) -> str:
    """Return the border color for the cursor preview rectangle."""
    if selected == TRANSPARENT:
        return "#FF6666"
    if selected in palette.entries and palette.entries[selected]:
        return palette.entries[selected]
    if selected.startswith("#") and len(selected) == 7:
        return selected
    return "#FF00FF"


def palette_key_to_index(key: str) -> int | None:
    """Convert a keyboard key (1-9, 0) to a 0-based palette index."""
    if key in "123456789":
        return int(key) - 1
    if key == "0":
        return 9
    return None


def palette_index_to_alias(index: int, aliases: list[str]) -> str | None:
    """Return the palette alias at the given index, or None if out of range."""
    if 0 <= index < len(aliases):
        return aliases[index]
    return None


def render_frame_thumbnail(
    grid_data: list[list[str]], palette: Palette,
) -> list[list[str | None]]:
    """Resolve grid data to hex colors for a frame thumbnail."""
    return palette.resolve_grid(grid_data)


def frame_strip_layout(num_frames: int, thumb_size: int = 32, padding: int = 4) -> list[int]:
    """Compute x positions for frame thumbnails in the strip."""
    return [padding + i * (thumb_size + padding) for i in range(num_frames)]


def blend_hex_colors(fg: str, bg: str, alpha: float) -> str:
    """Alpha-blend two hex colors. Returns #RRGGBB."""
    fr, fg_g, fb = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
    br, bg_g, bb = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    r = round(fr * alpha + br * (1 - alpha))
    g = round(fg_g * alpha + bg_g * (1 - alpha))
    b = round(fb * alpha + bb * (1 - alpha))
    return f"#{r:02X}{g:02X}{b:02X}"


def onion_skin_color(
    prev_color: str | None, cur_color: str | None, opacity: float,
) -> str | None:
    """Compute display color with onion skin overlay.

    Blends previous frame's color over current frame's display color.
    Returns None only if both are transparent.
    """
    if prev_color is None and cur_color is None:
        return None
    if prev_color is None:
        return cur_color
    if cur_color is None:
        # Blend prev over a neutral gray checkerboard color
        return blend_hex_colors(prev_color, CHECKER_LIGHT, opacity)
    return blend_hex_colors(prev_color, cur_color, opacity)


def playback_frame_sequence(
    animations: dict, anim_name: str | None, all_frames: list[int],
) -> list[int]:
    """Return the frame sequence for playback.

    If anim_name matches a named animation, return its frame list.
    Otherwise return all_frames.
    """
    if anim_name is not None and anim_name in animations:
        return animations[anim_name].get("frames", all_frames)
    return list(all_frames)


def frame_interval_ms(fps: int) -> int:
    """Convert FPS to millisecond interval between frames."""
    if fps <= 0:
        fps = 1
    return round(1000 / fps)


def frame_cell_at_coords(
    x: int, y: int, cell_size: int, grid_w: int, grid_h: int,
    num_frames: int, gap: int, viewport_w: int = 0,
) -> tuple[int | None, int | None, int | None]:
    """Map canvas pixel to (frame_idx, row, col) in side-by-side layout.

    When *viewport_w* > 0 the layout wraps frames into multiple rows.
    Returns (None, None, None) for gaps between frames or out-of-bounds.
    """
    if x < 0 or y < 0:
        return None, None, None
    frame_pixel_w = grid_w * cell_size
    frame_pixel_h = grid_h * cell_size
    col_stride = frame_pixel_w + gap
    row_stride = frame_pixel_h + gap
    if col_stride == 0 or row_stride == 0:
        return None, None, None

    if viewport_w > 0 and col_stride > 0:
        cols_per_row = max(1, viewport_w // col_stride)
    else:
        cols_per_row = num_frames if num_frames > 0 else 1

    frame_col = x // col_stride
    frame_row = y // row_stride
    if frame_col >= cols_per_row:
        return None, None, None
    frame_idx = frame_row * cols_per_row + frame_col
    if frame_idx >= num_frames:
        return None, None, None

    local_x = x - frame_col * col_stride
    local_y = y - frame_row * row_stride
    if local_x >= frame_pixel_w or local_y >= frame_pixel_h:
        # In a gap (horizontal or vertical)
        return None, None, None
    c = local_x // cell_size
    r = local_y // cell_size
    return frame_idx, r, c


def side_by_side_layout(
    num_frames: int, grid_w: int, grid_h: int, cell_size: int, gap: int,
    viewport_w: int = 0,
) -> tuple[int, int, list[tuple[int, int]]]:
    """Compute total canvas dimensions and per-frame (x, y) offsets for SBS view.

    Frames wrap into rows when *viewport_w* is positive and narrower than a
    single row would need.  With ``viewport_w=0`` (default) all frames sit in
    one row — preserving the old behaviour.
    """
    if num_frames == 0:
        return 0, 0, []
    frame_pixel_w = grid_w * cell_size
    frame_pixel_h = grid_h * cell_size
    stride = frame_pixel_w + gap

    if viewport_w > 0 and stride > 0:
        cols_per_row = max(1, viewport_w // stride)
    else:
        cols_per_row = num_frames  # single row

    num_rows = (num_frames + cols_per_row - 1) // cols_per_row
    total_w = min(num_frames, cols_per_row) * stride - gap
    total_h = num_rows * (frame_pixel_h + gap) - gap

    offsets: list[tuple[int, int]] = []
    for i in range(num_frames):
        col = i % cols_per_row
        row = i // cols_per_row
        offsets.append((col * stride, row * (frame_pixel_h + gap)))
    return total_w, total_h, offsets


def anim_dir_choices(sprite_root: Path) -> list[str]:
    """Return dropdown choices for animation directory selector.

    Returns ["(Base)"] + sorted names of animation subdirectories.
    A subdirectory qualifies if it has frame_NNN.txt files or animation.json.
    """
    choices = ["(Base)"]
    if not sprite_root.is_dir():
        return choices
    for child in sorted(sprite_root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if discover_frames(child) or (child / ANIM_FILE).exists():
            choices.append(child.name)
    return choices


def eyedropper_pick(grid, r: int | None, c: int | None) -> str | None:
    """Return the raw grid value at (r, c), or None if out of bounds."""
    if r is None or c is None:
        return None
    return grid.data[r][c]


def cell_display_color(val: str, palette: Palette, r: int, c: int) -> str:
    """Resolve a grid value to a display color string for tkinter."""
    if val == TRANSPARENT:
        return checker_color(r, c)
    if val in palette.entries and palette.entries[val] is not None:
        return palette.entries[val]
    if val.startswith("#") and len(val) == 7:
        return val
    return "#FF00FF"  # unknown = magenta
