"""GridFab GUI — tkinter-based pixel art editor.

Left-click to paint with selected color, right-click to erase (transparent).

Usage: gridfab-gui [directory]
  directory: folder containing grid.txt and palette.txt (default: current dir)
"""

import sys
import subprocess
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, colorchooser
from pathlib import Path

from gridfab.core.grid import Grid, TRANSPARENT, get_grid_dimensions
from gridfab.core.palette import Palette
from gridfab.core.animation import (
    discover_frames, is_animated, frame_path, resolve_grid_path,
    load_state, save_state, load_animations, save_animations,
    max_frame_number, swap_frame_files, update_animations_after_swap,
)

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
        parts.append("Transparent")
    else:
        color_str = selected
        if selected_hex:
            color_str += f" {selected_hex}"
        parts.append(color_str)
    parts.append(f"{grid_w}x{grid_h}")
    parts.append(f"{zoom_pct}%")
    parts.append(tool_name)
    if modified:
        parts.append("[Modified]")
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


class PixelEditor:
    def __init__(self, root: tk.Tk, work_dir: Path):
        self.root = root
        self.work_dir = work_dir
        self.palette_path = self.work_dir / "palette.txt"

        self.palette = Palette.load(self.palette_path)

        # Animation state
        self._animated = is_animated(self.work_dir)
        self._active_frame: int | None = None
        if self._animated:
            state = load_state(self.work_dir)
            frames = discover_frames(self.work_dir)
            self._active_frame = state.get("active_frame", frames[0] if frames else 1)

        # Resolve grid path (frame-aware)
        self.grid_path = resolve_grid_path(self.work_dir) if self._animated or (self.work_dir / "grid.txt").exists() else self.work_dir / "grid.txt"

        if self.grid_path.exists():
            self.grid = Grid.load(self.grid_path)
        else:
            w, h = get_grid_dimensions(self.work_dir)
            self.grid = Grid.blank(w, h)

        self.selected = TRANSPARENT
        self.painting = False
        self.modified = False
        self.cursor_pos: tuple[int, int] | None = None
        self.grid_lines_visible = True
        self.cell_size = DEFAULT_CELL_SIZE
        self._preview_rect: int | None = None
        self.tool = TOOL_BRUSH

        # Undo/redo stacks
        self.undo_stack: list[list[list[str]]] = []
        self.redo_stack: list[list[list[str]]] = []
        self.max_undo = 512
        self._stroke_active = False

        # Onion skinning
        self.onion_skin_enabled = False
        self.onion_skin_opacity = 0.25
        self._onion_opacities = [0.25, 0.50, 0.75]
        self._prev_frame_colors: list[list[str | None]] | None = None

        # Playback state
        self._playing = False
        self._play_anim_name: str | None = None
        self._play_fps = 8
        self._play_frame_seq: list[int] = []
        self._play_idx = 0
        self._play_after_id: str | None = None

        # Frame copy/paste
        self._copied_frame_data: list[list[str]] | None = None

        # Side-by-side view
        self._side_by_side = False
        self._frame_grids: dict[int, Grid] = {}
        self._frame_cells: dict[int, list[list[int]]] = {}
        self._frame_offsets: dict[int, tuple[int, int]] = {}
        self._sbs_gap = 8
        self._saved_geometry: str | None = None
        self._sbs_resize_pending = False
        self._sbs_rebuilding = False
        self._sbs_last_viewport_w = 0

        # Multi-frame selection (works in both modes)
        self._selected_frames: set[int] = set()
        self._frame_modified: dict[int, bool] = {}
        self._multi_undo_stack: list[dict[int, list[list[str]]]] = []
        self._multi_redo_stack: list[dict[int, list[list[str]]]] = []

        self._update_title()

        # Set window icon
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                if sys.platform == "win32":
                    root.iconbitmap(str(icon_path))
                else:
                    from PIL import ImageTk, Image as PILImage
                    ico = PILImage.open(icon_path)
                    ico = ico.resize((32, 32), PILImage.NEAREST)
                    self._icon_photo = ImageTk.PhotoImage(ico)
                    root.iconphoto(True, self._icon_photo)
            except Exception:
                pass  # Icon is cosmetic — fail silently

        # Status bar (pack first so it stays at bottom)
        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(
            root, textvariable=self.status_var, anchor=tk.W,
            relief=tk.SUNKEN, padx=5, font=("Consolas", 9),
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame strip (above status bar, below canvas)
        self.frame_strip = tk.Frame(root, height=50)
        self._frame_strip_buttons: list[tk.Button] = []
        if self._animated:
            self.frame_strip.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
            self._rebuild_frame_strip()

        # Main layout
        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True)

        # Palette panel
        self.palette_frame = palette_frame = tk.Frame(main, padx=5, pady=5)
        palette_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(palette_frame, text="Palette", font=("Arial", 10, "bold")).pack()

        self.palette_buttons: dict[str, tk.Button] = {}

        # Swatch grid frame
        self.swatch_frame = tk.Frame(palette_frame)
        self.swatch_frame.pack(pady=2)
        self._rebuild_palette_buttons()

        # Action buttons frame (2-column grid)
        action_frame = tk.Frame(palette_frame)
        action_frame.pack(pady=(10, 0))
        action_buttons = [
            ("Save", self.save, "#90EE90"),
            ("Render", self.render, "#ADD8E6"),
            ("Open", self.open_sprite, "#B0C4DE"),
            ("Refresh", self.refresh, "#FFD700"),
            ("Clear", self.clear_grid, "#FFA07A"),
            ("New", self.new_grid, "#DDA0DD"),
            ("Import", self.import_image, "#E6E6FA"),
            ("Animate", self._add_frame, "#B0E0E6"),
        ]
        for i, (text, cmd, bg) in enumerate(action_buttons):
            tk.Button(
                action_frame, text=text, width=6, command=cmd, bg=bg,
            ).grid(row=i // 2, column=i % 2, padx=2, pady=2)

        # Canvas
        canvas_w = self.grid.width * self.cell_size
        canvas_h = self.grid.height * self.cell_size
        self.canvas = tk.Canvas(
            main, width=min(canvas_w, 800), height=min(canvas_h, 600),
            highlightthickness=0,
            scrollregion=(0, 0, canvas_w, canvas_h),
        )
        self.canvas.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Draw cells
        self.cells: list[list[int]] = []
        line_cfg = grid_line_config(self.grid_lines_visible)
        for r in range(self.grid.height):
            row_cells: list[int] = []
            for c in range(self.grid.width):
                x0 = c * self.cell_size
                y0 = r * self.cell_size
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                rect = self.canvas.create_rectangle(
                    x0, y0, x0 + self.cell_size, y0 + self.cell_size,
                    fill=color, **line_cfg,
                )
                row_cells.append(rect)
            self.cells.append(row_cells)

        # Mouse bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_release)

        # Canvas tracking
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)

        # Zoom and pan
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)

        # Keyboard bindings
        root.bind("<Control-s>", lambda e: self.save())
        root.bind("<Control-z>", lambda e: self.undo())
        root.bind("<Control-y>", lambda e: self.redo())
        root.bind("<Control-Shift-Z>", lambda e: self.redo())
        root.bind("g", lambda e: self._toggle_grid_lines())
        root.bind("i", lambda e: self._set_tool(TOOL_EYEDROPPER))
        root.bind("f", lambda e: self._set_tool(TOOL_FILL))
        root.bind("b", lambda e: self._set_tool(TOOL_BRUSH))
        root.bind("r", lambda e: self.render())
        root.bind("e", lambda e: self._export())
        root.bind("h", lambda e: self._flip_horizontal())
        root.bind("v", lambda e: self._flip_vertical())
        root.bind("<bracketleft>", lambda e: self._zoom(-1))
        root.bind("<bracketright>", lambda e: self._zoom(1))
        root.bind("<period>", lambda e: self.select_color(TRANSPARENT))
        for k in "1234567890":
            root.bind(k, lambda e, key=k: self._select_palette_by_key(key))
        root.bind("<less>", lambda e: self._prev_frame())
        root.bind("<greater>", lambda e: self._next_frame())
        root.bind("o", lambda e: self._toggle_onion_skin())
        root.bind("O", lambda e: self._cycle_onion_opacity())
        root.bind("<space>", lambda e: self._toggle_playback())
        root.bind("m", lambda e: self._toggle_side_by_side())
        root.bind("<Control-c>", lambda e: self._copy_frame())
        root.bind("<Control-v>", lambda e: self._paste_frame())

        self.select_color(TRANSPARENT)
        self._update_status()

    def select_color(self, alias: str) -> None:
        for a, btn in self.palette_buttons.items():
            if a == alias:
                btn.config(relief=tk.SOLID, borderwidth=3)
            else:
                btn.config(relief=tk.RAISED, borderwidth=1)
        self.selected = alias
        self._update_status()

    def _set_tool(self, tool: str) -> None:
        self.tool = tool
        cursors = {
            TOOL_BRUSH: "",
            TOOL_EYEDROPPER: "crosshair",
            TOOL_FILL: "plus",
        }
        self.canvas.config(cursor=cursors.get(tool, ""))
        self._update_status()

    def _select_palette_by_key(self, key: str) -> None:
        idx = palette_key_to_index(key)
        if idx is None:
            return
        aliases = sorted(self.palette.colors.keys())
        alias = palette_index_to_alias(idx, aliases)
        if alias is not None:
            self.select_color(alias)

    def _export(self) -> None:
        self.save()
        result = subprocess.run(
            [sys.executable, "-m", "gridfab", "export", str(self.work_dir)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("Exported PNGs")
        else:
            print(f"Export failed: {result.stderr.strip()}")

    def _flip_horizontal(self) -> None:
        if len(self._selected_frames) > 1:
            snap = {f: self._frame_grids[f].snapshot()
                    for f in self._selected_frames if f in self._frame_grids}
            self._multi_undo_stack.append(snap)
            if len(self._multi_undo_stack) > self.max_undo:
                self._multi_undo_stack.pop(0)
            self._multi_redo_stack.clear()
            for f in self._selected_frames:
                if f in self._frame_grids:
                    self._frame_grids[f].flip_horizontal()
                    self._frame_modified[f] = True
                    if self._side_by_side and f in self._frame_cells:
                        self._redraw_sbs_frame(f)
        else:
            self.undo_stack.append(self.grid.snapshot())
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            self.grid.flip_horizontal()
        self._redraw()
        self._set_modified()

    def _flip_vertical(self) -> None:
        if len(self._selected_frames) > 1:
            snap = {f: self._frame_grids[f].snapshot()
                    for f in self._selected_frames if f in self._frame_grids}
            self._multi_undo_stack.append(snap)
            if len(self._multi_undo_stack) > self.max_undo:
                self._multi_undo_stack.pop(0)
            self._multi_redo_stack.clear()
            for f in self._selected_frames:
                if f in self._frame_grids:
                    self._frame_grids[f].flip_vertical()
                    self._frame_modified[f] = True
                    if self._side_by_side and f in self._frame_cells:
                        self._redraw_sbs_frame(f)
        else:
            self.undo_stack.append(self.grid.snapshot())
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            self.grid.flip_vertical()
        self._redraw()
        self._set_modified()

    def _on_motion(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        if r is not None:
            self.cursor_pos = (r, c)
        else:
            self.cursor_pos = None
        self._draw_preview(r, c)
        self._update_status()

    def _on_leave(self, event: tk.Event) -> None:
        self.cursor_pos = None
        self._clear_preview()
        self._update_status()

    def _draw_preview(self, r: int | None, c: int | None) -> None:
        self._clear_preview()
        if r is None or c is None:
            return
        cs = self.cell_size
        x_off = 0
        y_off = 0
        if self._side_by_side and self._active_frame in self._frame_offsets:
            fx, fy = self._frame_offsets[self._active_frame]
            x_off = fx
            y_off = fy + 16  # add label height per row
        x0 = x_off + c * cs
        y0 = y_off + r * cs
        color = cursor_preview_color(self.selected, self.palette)
        self._preview_rect = self.canvas.create_rectangle(
            x0 + 1, y0 + 1, x0 + cs - 1, y0 + cs - 1,
            outline=color, width=2, fill="",
        )

    def _clear_preview(self) -> None:
        if self._preview_rect is not None:
            self.canvas.delete(self._preview_rect)
            self._preview_rect = None

    def _set_modified(self, value: bool = True) -> None:
        if self.modified != value:
            self.modified = value
            self._update_title()

    def _update_title(self) -> None:
        name = self.work_dir.resolve().name
        prefix = "*" if self.modified else ""
        self.root.title(f"{prefix}GridFab — {name}")

    def _update_status(self) -> None:
        selected_hex = None
        if self.selected != TRANSPARENT:
            if self.selected in self.palette.entries and self.palette.entries[self.selected]:
                selected_hex = self.palette.entries[self.selected]
            elif self.selected.startswith("#"):
                selected_hex = self.selected
        zoom_pct = round(self.cell_size / DEFAULT_CELL_SIZE * 100)
        text = format_status_text(
            cursor_pos=self.cursor_pos,
            selected=self.selected,
            selected_hex=selected_hex,
            grid_w=self.grid.width,
            grid_h=self.grid.height,
            modified=self.modified,
            tool_name=self.tool,
            zoom_pct=zoom_pct,
            file_path=self.work_dir.resolve().name,
        )
        if self._playing:
            text += "  |  Playing"
        if self.onion_skin_enabled:
            pct = round(self.onion_skin_opacity * 100)
            text += f"  |  Onion:{pct}%"
        if self._animated and self._active_frame is not None:
            text += f"  |  Frame {self._active_frame}"
        if len(self._selected_frames) > 1:
            text += f"  |  Selected: {len(self._selected_frames)} frames"
        if self._side_by_side:
            text += "  |  SBS"
        self.status_var.set(text)

    def _toggle_grid_lines(self) -> None:
        self.grid_lines_visible = not self.grid_lines_visible
        cfg = grid_line_config(self.grid_lines_visible)
        if self._side_by_side:
            for frame_cells in self._frame_cells.values():
                for row in frame_cells:
                    for rect in row:
                        self.canvas.itemconfig(rect, **cfg)
        else:
            for row in self.cells:
                for rect in row:
                    self.canvas.itemconfig(rect, **cfg)

    def _on_mousewheel(self, event: tk.Event) -> None:
        direction = 1 if event.delta > 0 else -1
        new_size = zoom_step(self.cell_size, direction)
        if new_size != self.cell_size:
            self.cell_size = new_size
            if self._side_by_side:
                self._rebuild_canvas_sbs()
            else:
                self._rebuild_canvas()
            self._update_status()

    def _on_pan_start(self, event: tk.Event) -> None:
        self.canvas.scan_mark(event.x, event.y)

    def _on_pan_drag(self, event: tk.Event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _zoom(self, direction: int) -> None:
        new_size = zoom_step(self.cell_size, direction)
        if new_size != self.cell_size:
            self.cell_size = new_size
            if self._side_by_side:
                self._rebuild_canvas_sbs()
            else:
                self._rebuild_canvas()
            self._update_status()

    def cell_at(self, event: tk.Event) -> tuple[int | None, int | None]:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        if self._side_by_side:
            cs = self.cell_size
            frame_pw = self.grid.width * cs
            frame_ph = self.grid.height * cs
            clicked_frame = None
            r = c = None
            for f, (fx, fy) in self._frame_offsets.items():
                lx, ly = x - fx, y - fy
                if 0 <= lx < frame_pw and 0 <= ly < frame_ph:
                    clicked_frame = f
                    r = ly // cs
                    c = lx // cs
                    break
            if clicked_frame is not None:
                if clicked_frame != self._active_frame and clicked_frame in self._frame_grids:
                    if self.modified:
                        self.grid.save(self.grid_path)
                    self._active_frame = clicked_frame
                    self.grid = self._frame_grids[clicked_frame]
                    self.grid_path = frame_path(self.work_dir, clicked_frame)
                    self._frame_grids[clicked_frame] = self.grid
                return r, c
            return None, None
        return cell_at_coords(x, y, self.cell_size, self.grid.width, self.grid.height)

    def _begin_stroke(self) -> None:
        if not self._stroke_active:
            if len(self._selected_frames) > 1:
                snap = {f: self._frame_grids[f].snapshot()
                        for f in self._selected_frames if f in self._frame_grids}
                self._multi_undo_stack.append(snap)
                if len(self._multi_undo_stack) > self.max_undo:
                    self._multi_undo_stack.pop(0)
                self._multi_redo_stack.clear()
            else:
                self.undo_stack.append(self.grid.snapshot())
                if len(self.undo_stack) > self.max_undo:
                    self.undo_stack.pop(0)
                self.redo_stack.clear()
            self._stroke_active = True

    def paint(self, r: int | None, c: int | None, value: str) -> None:
        if r is None or c is None:
            return
        self._begin_stroke()
        # Always paint the active frame's canvas
        self.grid.data[r][c] = value
        color = cell_display_color(value, self.palette, r, c)
        if self._side_by_side and self._active_frame in self._frame_cells:
            self.canvas.itemconfig(self._frame_cells[self._active_frame][r][c], fill=color)
        else:
            self.canvas.itemconfig(self.cells[r][c], fill=color)
        self._set_modified()
        # Broadcast to other selected frames
        if len(self._selected_frames) > 1:
            for f in self._selected_frames:
                if f == self._active_frame:
                    continue
                if f in self._frame_grids:
                    grid = self._frame_grids[f]
                    if 0 <= r < grid.height and 0 <= c < grid.width:
                        grid.data[r][c] = value
                        self._frame_modified[f] = True
                        if self._side_by_side and f in self._frame_cells:
                            self.canvas.itemconfig(
                                self._frame_cells[f][r][c], fill=color,
                            )

    def on_click(self, event: tk.Event) -> None:
        if self._playing:
            return
        # Alt+click = eyedropper from any tool
        if event.state & 0x20000:  # Alt modifier
            self._eyedropper_at(event)
            return
        r, c = self.cell_at(event)
        if self.tool == TOOL_EYEDROPPER:
            self._eyedropper_at(event)
        elif self.tool == TOOL_FILL:
            self._fill_at(r, c)
        else:
            self.paint(r, c, self.selected)

    def on_drag(self, event: tk.Event) -> None:
        if self._playing:
            return
        if self.tool != TOOL_BRUSH:
            return
        r, c = self.cell_at(event)
        self.paint(r, c, self.selected)

    def _eyedropper_at(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        value = eyedropper_pick(self.grid, r, c)
        if value is not None:
            self.select_color(value)
            self._set_tool(TOOL_BRUSH)

    def _fill_at(self, r: int | None, c: int | None) -> None:
        if r is None or c is None:
            return
        if len(self._selected_frames) > 1:
            snap = {f: self._frame_grids[f].snapshot()
                    for f in self._selected_frames if f in self._frame_grids}
            self._multi_undo_stack.append(snap)
            if len(self._multi_undo_stack) > self.max_undo:
                self._multi_undo_stack.pop(0)
            self._multi_redo_stack.clear()
            for f in self._selected_frames:
                if f in self._frame_grids:
                    self._frame_grids[f].flood_fill(r, c, self.selected)
                    self._frame_modified[f] = True
                    if self._side_by_side and f in self._frame_cells:
                        self._redraw_sbs_frame(f)
            self._redraw()
        else:
            self.undo_stack.append(self.grid.snapshot())
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            self.grid.flood_fill(r, c, self.selected)
            self._redraw()
        self._set_modified()

    def on_right_click(self, event: tk.Event) -> None:
        if self._playing:
            return
        r, c = self.cell_at(event)
        self.paint(r, c, TRANSPARENT)

    def on_right_drag(self, event: tk.Event) -> None:
        if self._playing:
            return
        r, c = self.cell_at(event)
        self.paint(r, c, TRANSPARENT)

    def on_release(self, event: tk.Event) -> None:
        self._stroke_active = False

    def undo(self) -> None:
        if len(self._selected_frames) > 1 and self._multi_undo_stack:
            # Multi-frame atomic undo
            current = {f: self._frame_grids[f].snapshot()
                       for f in self._selected_frames if f in self._frame_grids}
            self._multi_redo_stack.append(current)
            snap = self._multi_undo_stack.pop()
            for f, data in snap.items():
                if f in self._frame_grids:
                    self._frame_grids[f].restore(data)
                    self._frame_modified[f] = True
                    if self._side_by_side and f in self._frame_cells:
                        self._redraw_sbs_frame(f)
            self._redraw()
            return
        if not self.undo_stack:
            return
        self.redo_stack.append(self.grid.snapshot())
        snapshot = self.undo_stack.pop()
        self.grid.restore(snapshot)
        self._redraw()

    def redo(self) -> None:
        if len(self._selected_frames) > 1 and self._multi_redo_stack:
            # Multi-frame atomic redo
            current = {f: self._frame_grids[f].snapshot()
                       for f in self._selected_frames if f in self._frame_grids}
            self._multi_undo_stack.append(current)
            snap = self._multi_redo_stack.pop()
            for f, data in snap.items():
                if f in self._frame_grids:
                    self._frame_grids[f].restore(data)
                    self._frame_modified[f] = True
                    if self._side_by_side and f in self._frame_cells:
                        self._redraw_sbs_frame(f)
            self._redraw()
            return
        if not self.redo_stack:
            return
        self.undo_stack.append(self.grid.snapshot())
        snapshot = self.redo_stack.pop()
        self.grid.restore(snapshot)
        self._redraw()

    def _redraw(self) -> None:
        self._clear_preview()
        if self._side_by_side:
            for f in self._frame_cells:
                self._redraw_sbs_frame(f)
            return
        for r in range(self.grid.height):
            for c in range(self.grid.width):
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                # Apply onion skin if enabled
                if (self.onion_skin_enabled and self._prev_frame_colors is not None
                        and r < len(self._prev_frame_colors)
                        and c < len(self._prev_frame_colors[r])):
                    prev_c = self._prev_frame_colors[r][c]
                    cur_c = self.palette.resolve(self.grid.data[r][c], "") if self.grid.data[r][c] != TRANSPARENT else None
                    blended = onion_skin_color(prev_c, cur_c, self.onion_skin_opacity)
                    if blended is not None:
                        color = blended
                self.canvas.itemconfig(self.cells[r][c], fill=color)

    def _redraw_sbs_frame(self, frame_num: int) -> None:
        """Redraw a single frame in side-by-side mode."""
        if frame_num not in self._frame_cells or frame_num not in self._frame_grids:
            return
        grid = self._frame_grids[frame_num]
        cells = self._frame_cells[frame_num]
        for r in range(grid.height):
            for c in range(grid.width):
                color = cell_display_color(grid.data[r][c], self.palette, r, c)
                self.canvas.itemconfig(cells[r][c], fill=color)

    # --- Side-by-side view ---

    def _toggle_side_by_side(self) -> None:
        """Toggle side-by-side view (M key). Only for animated sprites."""
        if not self._animated:
            return
        if self._playing:
            return
        if self._side_by_side:
            self._exit_side_by_side()
        else:
            self._enter_side_by_side()

    def _enter_side_by_side(self) -> None:
        """Enter side-by-side view showing all frames."""
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)

        # Disable onion skin in SBS
        self.onion_skin_enabled = False
        self._prev_frame_colors = None

        # Save current window geometry for later restore
        self._saved_geometry = self.root.geometry()

        self._side_by_side = True

        # Load all frame grids
        frames = discover_frames(self.work_dir)
        self._frame_grids.clear()
        for f in frames:
            if f == self._active_frame:
                self._frame_grids[f] = self.grid
            else:
                self._frame_grids[f] = Grid.load(frame_path(self.work_dir, f))
            self._frame_modified.setdefault(f, False)

        # Ensure active frame is in selection
        if not self._selected_frames:
            self._selected_frames = {self._active_frame} if self._active_frame else set()

        # Reset viewport tracking and bind resize handler
        self._sbs_last_viewport_w = 0
        self.canvas.bind("<Configure>", self._on_sbs_configure)

        # Auto-resize window for SBS layout
        self._resize_for_sbs(len(frames))

        self._rebuild_canvas_sbs()
        self._rebuild_frame_strip()
        self._update_status()

    def _exit_side_by_side(self) -> None:
        """Exit side-by-side view, save modified frames."""
        self.canvas.unbind("<Configure>")
        self._sbs_resize_pending = False
        self._sbs_last_viewport_w = 0
        self._flush_multi_frame_changes()
        self._side_by_side = False
        self._frame_cells.clear()
        self._frame_offsets.clear()
        # Keep _frame_grids if multi-selection is active
        if len(self._selected_frames) <= 1:
            self._frame_grids.clear()
            self._frame_modified.clear()
        self._rebuild_canvas()
        self._rebuild_frame_strip()
        self._update_status()

        # Restore saved window geometry
        if self._saved_geometry:
            self.root.geometry(self._saved_geometry)
            self._saved_geometry = None

    def _resize_for_sbs(self, num_frames: int) -> None:
        """Grow the window to fit more frames in SBS mode, capped at 85% of screen."""
        cs = self.cell_size
        gap = self._sbs_gap
        frame_pixel_w = self.grid.width * cs
        # Estimate palette sidebar width
        sidebar_w = 160
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        max_w = int(screen_w * 0.85)
        max_h = int(screen_h * 0.85)

        # Desired canvas width: fit all frames in one row if possible
        desired_canvas_w = num_frames * (frame_pixel_w + gap) - gap
        desired_w = min(desired_canvas_w + sidebar_w + 40, max_w)

        # Compute layout with that canvas width to get total height
        _, total_h, _ = side_by_side_layout(
            num_frames, self.grid.width, self.grid.height, cs, gap,
            viewport_w=desired_w - sidebar_w - 40,
        )
        label_h = 16
        frame_pixel_h = self.grid.height * cs
        row_stride = frame_pixel_h + gap
        if row_stride > 0 and total_h > 0:
            num_rows = (total_h + gap) // row_stride
        else:
            num_rows = 1
        total_h += label_h * num_rows

        # Add room for frame strip, status bar, toolbar
        chrome_h = 120
        desired_h = min(total_h + chrome_h, max_h)

        # Only grow, never shrink below current size
        cur_w = self.root.winfo_width()
        cur_h = self.root.winfo_height()
        new_w = max(desired_w, cur_w)
        new_h = max(desired_h, cur_h)
        if new_w != cur_w or new_h != cur_h:
            self.root.geometry(f"{new_w}x{new_h}")

    def _on_sbs_configure(self, event: tk.Event) -> None:
        """Re-layout SBS when canvas width changes (debounced)."""
        if not self._side_by_side or self._sbs_resize_pending or self._sbs_rebuilding:
            return
        # Only re-layout when the width actually changed
        new_w = event.width
        if new_w <= 1 or new_w == self._sbs_last_viewport_w:
            return
        self._sbs_resize_pending = True
        self.root.after(50, self._sbs_configure_idle)

    def _sbs_configure_idle(self) -> None:
        """Deferred SBS re-layout after resize."""
        self._sbs_resize_pending = False
        if self._side_by_side and not self._sbs_rebuilding:
            self._rebuild_canvas_sbs()

    def _rebuild_canvas_sbs(self) -> None:
        """Rebuild canvas in side-by-side layout with all frames."""
        if self._sbs_rebuilding:
            return
        self._sbs_rebuilding = True
        try:
            self._rebuild_canvas_sbs_inner()
        finally:
            self._sbs_rebuilding = False

    def _rebuild_canvas_sbs_inner(self) -> None:
        frames = discover_frames(self.work_dir)
        if not frames:
            return
        cs = self.cell_size
        gap = self._sbs_gap
        label_h = 16  # Height for frame labels above each frame

        # Use canvas width for wrapping; fall back to 0 (single row) if not mapped
        viewport_w = self.canvas.winfo_width()
        if viewport_w <= 1:
            viewport_w = 0
        self._sbs_last_viewport_w = viewport_w

        total_w, total_h, offsets = side_by_side_layout(
            len(frames), self.grid.width, self.grid.height, cs, gap,
            viewport_w=viewport_w,
        )

        # Account for one label_h per row of frames
        frame_pixel_h = self.grid.height * cs
        row_stride = frame_pixel_h + gap
        if row_stride > 0 and total_h > 0:
            num_rows = (total_h + gap) // row_stride
        else:
            num_rows = 1
        total_h += label_h * num_rows

        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.canvas.delete("all")
        self.cells = []
        self._frame_cells.clear()
        self._frame_offsets.clear()
        line_cfg = grid_line_config(self.grid_lines_visible)

        for idx, f in enumerate(frames):
            x_off, y_off_raw = offsets[idx]
            # Compute which visual row this frame is in for label offset
            row_idx = y_off_raw // row_stride if row_stride > 0 else 0
            y_off = y_off_raw + label_h * (row_idx + 1)
            self._frame_offsets[f] = (x_off, y_off)
            grid = self._frame_grids.get(f)
            if grid is None:
                continue

            # Frame label
            is_selected = f in self._selected_frames
            is_active = f == self._active_frame
            label_color = "#4488CC" if is_selected else "#666666"
            if is_active:
                label_color = "#CC4444"
            self.canvas.create_text(
                x_off + (self.grid.width * cs) // 2,
                y_off - label_h // 2,
                text=str(f), fill=label_color,
                font=("Consolas", 9, "bold"),
            )

            # Selection indicator bar
            if is_selected:
                bar_color = "#CC4444" if is_active else "#AADDFF"
                self.canvas.create_rectangle(
                    x_off, y_off - 3,
                    x_off + self.grid.width * cs, y_off,
                    fill=bar_color, outline="",
                )

            # Draw cells
            frame_cells: list[list[int]] = []
            for r in range(grid.height):
                row_cells: list[int] = []
                for c in range(grid.width):
                    x0 = x_off + c * cs
                    y0 = y_off + r * cs
                    color = cell_display_color(grid.data[r][c], self.palette, r, c)
                    rect = self.canvas.create_rectangle(
                        x0, y0, x0 + cs, y0 + cs,
                        fill=color, **line_cfg,
                    )
                    row_cells.append(rect)
                frame_cells.append(row_cells)
            self._frame_cells[f] = frame_cells

    # --- Onion skinning ---

    def _toggle_onion_skin(self) -> None:
        """Toggle onion skin overlay on/off."""
        if not self._animated or self._side_by_side:
            return
        self.onion_skin_enabled = not self.onion_skin_enabled
        if self.onion_skin_enabled:
            self._load_prev_frame_colors()
        else:
            self._prev_frame_colors = None
        self._redraw()
        self._update_status()

    def _cycle_onion_opacity(self) -> None:
        """Cycle through onion skin opacity levels."""
        if not self._animated:
            return
        try:
            idx = self._onion_opacities.index(self.onion_skin_opacity)
        except ValueError:
            idx = -1
        self.onion_skin_opacity = self._onion_opacities[(idx + 1) % len(self._onion_opacities)]
        if self.onion_skin_enabled:
            self._redraw()
        self._update_status()

    def _load_prev_frame_colors(self) -> None:
        """Load the previous frame's resolved colors for onion skinning."""
        if not self._animated or self._active_frame is None:
            self._prev_frame_colors = None
            return
        frames = discover_frames(self.work_dir)
        idx = frames.index(self._active_frame) if self._active_frame in frames else 0
        if idx == 0:
            self._prev_frame_colors = None
            return
        prev_num = frames[idx - 1]
        prev_grid = Grid.load(frame_path(self.work_dir, prev_num))
        self._prev_frame_colors = self.palette.resolve_grid(prev_grid.data)

    # --- Playback ---

    def _toggle_playback(self) -> None:
        """Toggle animation playback on/off."""
        if not self._animated or self._side_by_side:
            return
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start animation playback."""
        if self._playing:
            return
        # Auto-save before playback
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)

        animations = load_animations(self.work_dir)
        all_frames = discover_frames(self.work_dir)
        self._play_frame_seq = playback_frame_sequence(
            animations, self._play_anim_name, all_frames,
        )
        if not self._play_frame_seq:
            return

        # Use animation's FPS if playing a named anim
        if (self._play_anim_name and self._play_anim_name in animations):
            anim_data = animations[self._play_anim_name]
            self._play_fps = anim_data.get("fps", self._play_fps)
            self._fps_var.set(self._play_fps)

        self._playing = True
        self._play_idx = 0
        self._rebuild_frame_strip()
        self._play_tick()

    def _stop_playback(self) -> None:
        """Stop animation playback."""
        if self._play_after_id is not None:
            self.root.after_cancel(self._play_after_id)
            self._play_after_id = None
        self._playing = False
        self._rebuild_frame_strip()
        self._update_status()

    def _play_tick(self) -> None:
        """Advance to the next frame in the playback sequence."""
        if not self._playing or not self._play_frame_seq:
            return
        frame_num = self._play_frame_seq[self._play_idx]
        self._switch_frame_no_rebuild(frame_num)
        self._play_idx = (self._play_idx + 1) % len(self._play_frame_seq)
        interval = frame_interval_ms(self._play_fps)
        self._play_after_id = self.root.after(interval, self._play_tick)

    def _switch_frame_no_rebuild(self, frame_num: int) -> None:
        """Switch frame display without rebuilding the frame strip (for playback)."""
        self._active_frame = frame_num
        self.grid_path = frame_path(self.work_dir, frame_num)
        self.grid = Grid.load(self.grid_path)
        self._redraw()
        self._update_status()

    def _on_fps_change(self) -> None:
        """Handle FPS spinner change."""
        try:
            self._play_fps = self._fps_var.get()
        except (tk.TclError, ValueError):
            pass

    def _on_anim_select(self, value: str) -> None:
        """Handle animation dropdown selection."""
        if value == "(All Frames)":
            self._play_anim_name = None
        else:
            self._play_anim_name = value
        # If currently playing, restart with new sequence
        if self._playing:
            self._stop_playback()
            self._start_playback()

    # --- Frame strip and navigation ---

    def _rebuild_frame_strip(self) -> None:
        """Recreate frame strip thumbnails for all frames."""
        for btn in self._frame_strip_buttons:
            btn.destroy()
        self._frame_strip_buttons.clear()

        # Control buttons
        btn_add = tk.Button(self.frame_strip, text="+", width=3, command=self._add_frame)
        btn_add.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_add)

        btn_dup = tk.Button(self.frame_strip, text="Dup", width=3, command=self._duplicate_frame)
        btn_dup.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_dup)

        btn_del = tk.Button(self.frame_strip, text="Del", width=3, command=self._delete_frame_gui)
        btn_del.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_del)

        btn_copy = tk.Button(self.frame_strip, text="Cp", width=2, command=self._copy_frame)
        btn_copy.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_copy)

        btn_paste = tk.Button(self.frame_strip, text="Ps", width=2, command=self._paste_frame)
        btn_paste.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_paste)

        btn_left = tk.Button(self.frame_strip, text="\u25C0", width=2, command=self._move_frame_left)
        btn_left.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_left)

        btn_right = tk.Button(self.frame_strip, text="\u25B6", width=2, command=self._move_frame_right)
        btn_right.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_right)

        sep = tk.Frame(self.frame_strip, width=4)
        sep.pack(side=tk.LEFT)
        self._frame_strip_buttons.append(sep)

        # Play/Pause button
        play_text = "Stop" if self._playing else "Play"
        btn_play = tk.Button(self.frame_strip, text=play_text, width=4, command=self._toggle_playback)
        btn_play.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(btn_play)

        # FPS spinner
        fps_label = tk.Label(self.frame_strip, text="FPS:")
        fps_label.pack(side=tk.LEFT, padx=(4, 0))
        self._frame_strip_buttons.append(fps_label)

        self._fps_var = tk.IntVar(value=self._play_fps)
        fps_spin = tk.Spinbox(
            self.frame_strip, from_=1, to=60, width=3,
            textvariable=self._fps_var, command=self._on_fps_change,
        )
        fps_spin.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(fps_spin)

        # Animation selector dropdown
        animations = load_animations(self.work_dir)
        anim_names = ["(All Frames)"] + sorted(animations.keys())
        self._anim_var = tk.StringVar(value=anim_names[0])
        if self._play_anim_name and self._play_anim_name in animations:
            self._anim_var.set(self._play_anim_name)
        anim_menu = tk.OptionMenu(
            self.frame_strip, self._anim_var, *anim_names,
            command=self._on_anim_select,
        )
        anim_menu.config(width=10)
        anim_menu.pack(side=tk.LEFT, padx=2)
        self._frame_strip_buttons.append(anim_menu)

        sep2 = tk.Frame(self.frame_strip, width=4)
        sep2.pack(side=tk.LEFT)
        self._frame_strip_buttons.append(sep2)

        frames = discover_frames(self.work_dir)
        for f in frames:
            is_active = f == self._active_frame
            is_selected = f in self._selected_frames
            relief = tk.SUNKEN if is_active else tk.RAISED
            border = 3 if is_active else 1
            bg = "#AADDFF" if is_selected and not is_active else "#D0D0D0" if is_active else None
            btn = tk.Button(
                self.frame_strip, text=str(f), width=4, height=1,
                relief=relief, borderwidth=border,
                command=lambda num=f: self._switch_frame(num),
            )
            if bg:
                btn.config(bg=bg)
            btn.bind("<Control-Button-1>", lambda e, num=f: self._toggle_frame_selection(num))
            btn.bind("<Shift-Button-1>", lambda e, num=f: self._range_select_frames(num))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self._frame_strip_buttons.append(btn)

    def _switch_frame(self, frame_num: int) -> None:
        """Switch to a different frame. Clears multi-selection unless in SBS mode."""
        if frame_num == self._active_frame:
            return

        # Save all modified frames in multi-selection
        self._flush_multi_frame_changes()

        # Auto-save current frame if modified
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)

        if self._side_by_side:
            # In SBS mode, keep frame_grids alive — just switch active
            self._active_frame = frame_num
            save_state(self.work_dir, {"active_frame": frame_num})
            self.grid_path = frame_path(self.work_dir, frame_num)
            self.grid = self._frame_grids.get(frame_num) or Grid.load(self.grid_path)
            self._frame_grids[frame_num] = self.grid
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._rebuild_canvas_sbs()
            self._rebuild_frame_strip()
            self._update_title()
            self._update_status()
            return

        # Clear multi-selection (plain click = single frame)
        self._selected_frames.clear()
        self._frame_grids.clear()
        self._frame_modified.clear()
        self._multi_undo_stack.clear()
        self._multi_redo_stack.clear()

        # Update active frame
        self._active_frame = frame_num
        save_state(self.work_dir, {"active_frame": frame_num})
        self.grid_path = frame_path(self.work_dir, frame_num)

        # Load new frame
        self.grid = Grid.load(self.grid_path)

        # Clear undo/redo (simple approach)
        self.undo_stack.clear()
        self.redo_stack.clear()

        # Reload onion skin data
        if self.onion_skin_enabled:
            self._load_prev_frame_colors()

        # Rebuild
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_title()
        self._update_status()

    def _toggle_frame_selection(self, frame_num: int) -> None:
        """Ctrl+click: toggle a frame in/out of multi-selection."""
        if frame_num in self._selected_frames:
            # Don't remove the active frame from selection
            if frame_num != self._active_frame:
                self._selected_frames.discard(frame_num)
                self._frame_grids.pop(frame_num, None)
                self._frame_modified.pop(frame_num, None)
        else:
            self._selected_frames.add(frame_num)
        # Ensure active frame is always in selection when multi-selecting
        if self._selected_frames:
            self._selected_frames.add(self._active_frame)
            self._load_selected_frame_grids()
        self._rebuild_frame_strip()
        self._update_status()
        return "break"  # Prevent default button command

    def _range_select_frames(self, frame_num: int) -> None:
        """Shift+click: select contiguous range from active frame to clicked frame."""
        frames = discover_frames(self.work_dir)
        if self._active_frame not in frames or frame_num not in frames:
            return "break"
        idx_active = frames.index(self._active_frame)
        idx_target = frames.index(frame_num)
        lo, hi = min(idx_active, idx_target), max(idx_active, idx_target)
        self._selected_frames = set(frames[lo:hi + 1])
        self._load_selected_frame_grids()
        self._rebuild_frame_strip()
        self._update_status()
        return "break"  # Prevent default button command

    def _load_selected_frame_grids(self) -> None:
        """Ensure _frame_grids is populated for all selected frames."""
        for f in self._selected_frames:
            if f not in self._frame_grids:
                if f == self._active_frame:
                    self._frame_grids[f] = self.grid
                else:
                    self._frame_grids[f] = Grid.load(frame_path(self.work_dir, f))
                self._frame_modified.setdefault(f, False)

    def _flush_multi_frame_changes(self) -> None:
        """Save all modified frames in _frame_grids to disk."""
        for f, modified in self._frame_modified.items():
            if modified and f in self._frame_grids:
                if f == self._active_frame:
                    continue  # Will be saved via normal self.grid.save
                self._frame_grids[f].save(frame_path(self.work_dir, f))
        self._frame_modified = {f: False for f in self._frame_modified}

    def _prev_frame(self) -> None:
        """Switch to previous frame."""
        if not self._animated:
            return
        frames = discover_frames(self.work_dir)
        if not frames:
            return
        idx = frames.index(self._active_frame) if self._active_frame in frames else 0
        if idx > 0:
            self._switch_frame(frames[idx - 1])

    def _next_frame(self) -> None:
        """Switch to next frame."""
        if not self._animated:
            return
        frames = discover_frames(self.work_dir)
        if not frames:
            return
        idx = frames.index(self._active_frame) if self._active_frame in frames else 0
        if idx < len(frames) - 1:
            self._switch_frame(frames[idx + 1])

    def _add_frame(self) -> None:
        """Add a new frame via GUI."""
        from gridfab.commands.frame_cmd import cmd_frame_add
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        cmd_frame_add(self.work_dir)
        self._animated = True
        state = load_state(self.work_dir)
        self._active_frame = state.get("active_frame", 1)
        self.grid_path = frame_path(self.work_dir, self._active_frame)
        self.grid = Grid.load(self.grid_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        if not self.frame_strip.winfo_ismapped():
            self.frame_strip.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2,
                                  before=self.status_bar)
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_title()
        self._update_status()

    def _duplicate_frame(self) -> None:
        """Duplicate the active frame."""
        if not self._animated:
            return
        from gridfab.commands.frame_cmd import cmd_frame_add
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        cmd_frame_add(self.work_dir, from_frame=self._active_frame)
        state = load_state(self.work_dir)
        self._active_frame = state.get("active_frame", 1)
        self.grid_path = frame_path(self.work_dir, self._active_frame)
        self.grid = Grid.load(self.grid_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_title()
        self._update_status()

    def _delete_frame_gui(self) -> None:
        """Delete the active frame via GUI."""
        if not self._animated:
            return
        frames = discover_frames(self.work_dir)
        if len(frames) <= 1:
            messagebox.showwarning("Cannot Delete", "Cannot delete the only frame.")
            return
        if not messagebox.askyesno("Delete Frame", f"Delete frame {self._active_frame}?"):
            return
        from gridfab.commands.frame_cmd import cmd_frame_delete
        cmd_frame_delete(self.work_dir, self._active_frame)
        state = load_state(self.work_dir)
        self._active_frame = state.get("active_frame", 1)
        self.grid_path = frame_path(self.work_dir, self._active_frame)
        self.grid = Grid.load(self.grid_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_title()
        self._update_status()

    def _copy_frame(self) -> None:
        """Copy the active frame's data to memory."""
        if not self._animated:
            return
        self._copied_frame_data = self.grid.snapshot()

    def _paste_frame(self) -> None:
        """Paste copied frame data as a new frame."""
        if not self._animated or self._copied_frame_data is None:
            return
        from gridfab.commands.frame_cmd import cmd_frame_add
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        cmd_frame_add(self.work_dir, blank=True)
        state = load_state(self.work_dir)
        new_frame = state.get("active_frame", 1)
        self._active_frame = new_frame
        self.grid_path = frame_path(self.work_dir, new_frame)
        new_grid = Grid.load(self.grid_path)
        new_grid.restore(self._copied_frame_data)
        new_grid.save(self.grid_path)
        self.grid = new_grid
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_title()
        self._update_status()

    def _move_frame_left(self) -> None:
        """Move the active frame one position left (swap with previous)."""
        if not self._animated:
            return
        frames = discover_frames(self.work_dir)
        if self._active_frame not in frames:
            return
        idx = frames.index(self._active_frame)
        if idx == 0:
            return
        prev_num = frames[idx - 1]
        cur_num = self._active_frame
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        swap_frame_files(self.work_dir, prev_num, cur_num)
        anims = load_animations(self.work_dir)
        updated = update_animations_after_swap(anims, prev_num, cur_num)
        save_animations(self.work_dir, updated)
        # After swap, our content is now at prev_num
        self._active_frame = prev_num
        save_state(self.work_dir, {"active_frame": prev_num})
        self.grid_path = frame_path(self.work_dir, prev_num)
        self.grid = Grid.load(self.grid_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_status()

    def _move_frame_right(self) -> None:
        """Move the active frame one position right (swap with next)."""
        if not self._animated:
            return
        frames = discover_frames(self.work_dir)
        if self._active_frame not in frames:
            return
        idx = frames.index(self._active_frame)
        if idx >= len(frames) - 1:
            return
        next_num = frames[idx + 1]
        cur_num = self._active_frame
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        swap_frame_files(self.work_dir, cur_num, next_num)
        anims = load_animations(self.work_dir)
        updated = update_animations_after_swap(anims, cur_num, next_num)
        save_animations(self.work_dir, updated)
        # After swap, our content is now at next_num
        self._active_frame = next_num
        save_state(self.work_dir, {"active_frame": next_num})
        self.grid_path = frame_path(self.work_dir, next_num)
        self.grid = Grid.load(self.grid_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_status()

    def save(self) -> None:
        self.grid.save(self.grid_path)
        self._flush_multi_frame_changes()
        self._set_modified(False)
        print("Saved grid.txt")

    def refresh(self) -> None:
        self.undo_stack.append(self.grid.snapshot())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.palette = Palette.load(self.palette_path)
        if self.grid_path.exists():
            self.grid = Grid.load(self.grid_path)
        self._rebuild_palette_buttons()
        self.select_color(self.selected)
        self._redraw()
        print("Refreshed from disk")

    def clear_grid(self) -> None:
        if not messagebox.askyesno("Clear Grid", "Reset all pixels to transparent?"):
            return
        self.undo_stack.append(self.grid.snapshot())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        for r in range(self.grid.height):
            for c in range(self.grid.width):
                self.grid.data[r][c] = TRANSPARENT
        self._redraw()
        self.save()
        print("Grid cleared")

    def new_grid(self) -> None:
        has_sprite = self.grid_path.exists()

        if has_sprite:
            choice = messagebox.askquestion(
                "New",
                "Create a new grid in the current folder?\n\n"
                "Yes = Resize current grid here\n"
                "No = Create a new sprite in another folder",
            )
            if choice == "yes":
                self._new_grid_here()
                return
            else:
                self._new_sprite()
                return
        else:
            self._new_sprite()

    def _new_grid_here(self) -> None:
        size_str = simpledialog.askstring(
            "New Grid", "Enter size as WxH (e.g. 16x16, 32x32):",
            parent=self.root,
        )
        if not size_str:
            return
        parts = size_str.lower().split("x")
        if len(parts) != 2:
            messagebox.showerror("Invalid Size", "Size must be WxH (e.g. 32x32)")
            return
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            messagebox.showerror("Invalid Size", "Width and height must be integers")
            return
        if w < 1 or h < 1:
            messagebox.showerror("Invalid Size", "Width and height must be positive")
            return
        if not messagebox.askyesno(
            "New Grid",
            f"Create new {w}x{h} grid? This will replace the current grid.",
        ):
            return
        self.undo_stack.append(self.grid.snapshot())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.grid = Grid.blank(w, h)
        self._rebuild_canvas(resize_viewport=True)
        self.save()
        print(f"New {w}x{h} grid created")

    def _new_sprite(self) -> None:
        parent = filedialog.askdirectory(
            title="Choose parent folder for new sprite",
            parent=self.root,
        )
        if not parent:
            return

        name = simpledialog.askstring(
            "Sprite Name", "Enter sprite name (becomes folder name):",
            parent=self.root,
        )
        if not name:
            return

        size_str = simpledialog.askstring(
            "Grid Size", "Enter size as WxH (e.g. 16x16, 32x32):",
            parent=self.root,
        )
        if not size_str:
            return
        parts = size_str.lower().split("x")
        if len(parts) != 2:
            messagebox.showerror("Invalid Size", "Size must be WxH (e.g. 32x32)")
            return
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            messagebox.showerror("Invalid Size", "Width and height must be integers")
            return
        if w < 1 or h < 1:
            messagebox.showerror("Invalid Size", "Width and height must be positive")
            return

        new_dir = Path(parent) / name
        try:
            from gridfab.commands.init import cmd_init
            cmd_init(new_dir, w, h)
        except FileExistsError as e:
            messagebox.showerror("Error", str(e))
            return

        self._switch_to_dir(new_dir)
        print(f"Created new sprite: {new_dir}")

    def open_sprite(self) -> None:
        folder = filedialog.askdirectory(
            title="Open sprite folder",
            parent=self.root,
        )
        if not folder:
            return

        folder_path = Path(folder)
        if not (folder_path / "grid.txt").exists() and not is_animated(folder_path):
            messagebox.showerror(
                "Not a Sprite",
                f"No grid.txt or frame files found in {folder_path.name}\n\n"
                "Select a folder containing grid.txt and palette.txt.",
            )
            return

        self._switch_to_dir(folder_path)
        print(f"Opened sprite: {folder_path}")

    def import_image(self) -> None:
        image_path = filedialog.askopenfilename(
            title="Select image to import",
            filetypes=[
                ("Image files",
                 "*.png *.bmp *.dib *.gif *.tiff *.tif *.webp *.jpg *.jpeg *.jpe "
                 "*.jp2 *.jpx *.j2k *.ico *.icns *.tga *.pcx *.ppm *.pbm *.pgm *.pnm "
                 "*.sgi *.xbm *.dds *.eps *.qoi *.psd *.cur *.fli *.flc *.xpm "
                 "*.wmf *.emf *.fits *.msp *.blp *.avif"),
                ("All files", "*.*"),
            ],
            parent=self.root,
        )
        if not image_path:
            return

        name = simpledialog.askstring(
            "Sprite Name", "Enter sprite name (becomes folder name):",
            parent=self.root,
        )
        if not name:
            return

        tile_str = simpledialog.askstring(
            "Tilesheet?",
            "If this is a tilesheet, enter tile size as WxH.\n"
            "Leave blank for single image import.",
            parent=self.root,
        )

        new_dir = self.work_dir / name
        try:
            from gridfab.commands.import_cmd import cmd_import
            from gridfab.cli import parse_size

            if tile_str and tile_str.strip():
                tile_size = parse_size(tile_str.strip())
                tile_coord = simpledialog.askstring(
                    "Tile Position",
                    "Enter tile coordinate as COL,ROW (0-indexed):",
                    parent=self.root,
                )
                if not tile_coord:
                    return
                parts = tile_coord.split(",")
                if len(parts) != 2:
                    messagebox.showerror("Invalid", "Must be COL,ROW (e.g. 3,2)")
                    return
                try:
                    tile_pos = (int(parts[0]), int(parts[1]))
                except ValueError:
                    messagebox.showerror("Invalid", "Coordinates must be integers")
                    return
                cmd_import(
                    Path(image_path), new_dir,
                    tile_size=tile_size, tile_pos=tile_pos,
                )
            else:
                cmd_import(Path(image_path), new_dir)

            self._switch_to_dir(new_dir)
            messagebox.showinfo("Import Complete", f"Imported to {new_dir.name}")
        except (ValueError, FileExistsError, FileNotFoundError) as e:
            messagebox.showerror("Import Error", str(e))

    def _switch_to_dir(self, new_dir: Path) -> None:
        """Switch the editor to a different sprite directory."""
        self.work_dir = new_dir
        self.palette_path = new_dir / "palette.txt"

        # Check animation state
        self._animated = is_animated(new_dir)
        if self._animated:
            state = load_state(new_dir)
            frames = discover_frames(new_dir)
            self._active_frame = state.get("active_frame", frames[0] if frames else 1)
            self.grid_path = frame_path(new_dir, self._active_frame)
        else:
            self._active_frame = None
            self.grid_path = new_dir / "grid.txt"

        # Reload palette and grid
        self.palette = Palette.load(self.palette_path)
        if self.grid_path.exists():
            self.grid = Grid.load(self.grid_path)
        else:
            w, h = get_grid_dimensions(self.work_dir)
            self.grid = Grid.blank(w, h)

        # Reset undo/redo and modified state
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.modified = False

        # Rebuild palette buttons
        self._rebuild_palette_buttons()

        # Frame strip
        if self._animated:
            if not self.frame_strip.winfo_ismapped():
                self.frame_strip.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2,
                                      before=self.status_bar)
            self._rebuild_frame_strip()
        else:
            self.frame_strip.pack_forget()

        # Rebuild canvas
        self._rebuild_canvas(resize_viewport=True)

        # Update title and status
        self._update_title()
        self.select_color(TRANSPARENT)

    def _rebuild_palette_buttons(self) -> None:
        """Remove old swatch buttons and create new ones in a grid layout."""
        for widget in self.swatch_frame.winfo_children():
            widget.destroy()
        self.palette_buttons.clear()

        # Build items: transparent first, then sorted palette colors
        items: list[tuple[str, str]] = [(TRANSPARENT, "#FFFFFF")]
        for alias, color in sorted(self.palette.colors.items()):
            items.append((alias, color if color else "#FFFFFF"))

        for i, (alias, color) in enumerate(items):
            fg = _contrast_color(color)
            text = "." if alias == TRANSPARENT else alias
            btn = tk.Button(
                self.swatch_frame, text=text, width=4, height=2,
                bg=color, fg=fg, borderwidth=1,
                command=lambda a=alias: self.select_color(a),
            )
            btn.grid(row=i // SWATCH_COLS, column=i % SWATCH_COLS, padx=1, pady=1)
            if alias != TRANSPARENT:
                btn.bind("<Double-Button-1>", lambda e, a=alias: self._edit_color(a))
            btn.bind("<Button-3>", lambda e, a=alias: self._swatch_context_menu(e, a))
            self.palette_buttons[alias] = btn

        # "+" add-color button at the end
        add_pos = len(items)
        add_btn = tk.Button(
            self.swatch_frame, text="+", width=4, height=2,
            command=self._add_color,
        )
        add_btn.grid(
            row=add_pos // SWATCH_COLS, column=add_pos % SWATCH_COLS,
            padx=1, pady=1,
        )

    def _add_color(self) -> None:
        """Open color picker and add a new color to the palette."""
        result = colorchooser.askcolor(parent=self.root, title="Choose a color")
        if result[1] is None:
            return
        hex_color = result[1].upper()

        alias = simpledialog.askstring(
            "Alias", "Enter alias (1-2 characters):", parent=self.root,
        )
        if not alias:
            return

        try:
            Palette._validate_alias(alias)
        except ValueError as e:
            messagebox.showerror("Invalid Alias", str(e))
            return

        # Check case-insensitive duplicates
        for existing in self.palette.entries:
            if existing == TRANSPARENT:
                continue
            if existing.lower() == alias.lower():
                messagebox.showerror(
                    "Duplicate Alias",
                    f"Alias '{alias}' conflicts with existing alias '{existing}' "
                    f"(case-insensitive duplicates not allowed)",
                )
                return

        self.palette.entries[alias] = hex_color
        self.palette.save(self.palette_path)
        self._rebuild_palette_buttons()
        self.select_color(alias)

    def _edit_color(self, alias: str) -> None:
        """Open color picker to change an existing palette color."""
        if alias == TRANSPARENT:
            return
        current = self.palette.entries.get(alias, "#FFFFFF")
        result = colorchooser.askcolor(
            initialcolor=current, parent=self.root, title=f"Edit color: {alias}",
        )
        if result[1] is None:
            return
        self.palette.entries[alias] = result[1].upper()
        self.palette.save(self.palette_path)
        self._rebuild_palette_buttons()
        self.select_color(alias)
        self._redraw()

    def _swatch_context_menu(self, event: tk.Event, alias: str) -> None:
        """Show right-click context menu for a swatch button."""
        menu = tk.Menu(self.root, tearoff=0)
        if alias == TRANSPARENT:
            menu.add_command(label="Transparent (no actions)", state=tk.DISABLED)
        else:
            hex_color = self.palette.entries.get(alias, "")
            menu.add_command(
                label=f"Copy Hex ({hex_color})",
                command=lambda: self._copy_to_clipboard(hex_color),
            )
            menu.add_command(
                label="Edit Color...",
                command=lambda: self._edit_color(alias),
            )
            menu.add_separator()
            menu.add_command(
                label="Remove Color",
                command=lambda: self._remove_color(alias),
            )
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _remove_color(self, alias: str) -> None:
        """Remove a color from the palette after confirmation."""
        if not messagebox.askyesno(
            "Remove Color",
            f"Remove '{alias}' from the palette?\n\n"
            f"Cells using this color will show as magenta (unknown).",
        ):
            return
        del self.palette.entries[alias]
        self.palette.save(self.palette_path)
        if self.selected == alias:
            self.selected = TRANSPARENT
        self._rebuild_palette_buttons()
        self.select_color(self.selected)
        self._redraw()

    def _rebuild_canvas(self, resize_viewport: bool = False) -> None:
        """Rebuild the canvas for a new grid size."""
        cs = self.cell_size
        canvas_w = self.grid.width * cs
        canvas_h = self.grid.height * cs
        if resize_viewport:
            self.canvas.config(width=min(canvas_w, 800), height=min(canvas_h, 600))
        self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))
        self.canvas.delete("all")
        self.cells = []
        line_cfg = grid_line_config(self.grid_lines_visible)
        for r in range(self.grid.height):
            row_cells: list[int] = []
            for c in range(self.grid.width):
                x0 = c * cs
                y0 = r * cs
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                rect = self.canvas.create_rectangle(
                    x0, y0, x0 + cs, y0 + cs,
                    fill=color, **line_cfg,
                )
                row_cells.append(rect)
            self.cells.append(row_cells)

    def render(self) -> None:
        self.save()
        result = subprocess.run(
            [sys.executable, "-m", "gridfab", "render", str(self.work_dir)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("Rendered preview.png")
        else:
            print(f"Render failed: {result.stderr.strip()}")


def main() -> None:
    work_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    root = tk.Tk()
    PixelEditor(root, Path(work_dir))
    root.mainloop()


if __name__ == "__main__":
    main()
