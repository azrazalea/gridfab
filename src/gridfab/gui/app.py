"""GridFab GUI — tkinter-based pixel art editor.

Left-click to paint with selected color, right-click to erase (transparent).

Usage: gridfab-gui [directory]
  directory: folder containing grid.txt and palette.txt (default: current dir)
"""

import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, colorchooser
from gridfab.gui.i18n import _
from gridfab.gui.widgets.dialogs import (
    ask_string, show_info, show_warning, show_error,
    ask_yes_no, ask_yes_no_cancel, ask_ok_cancel,
)
from pathlib import Path

from gridfab.core.grid import Grid, TRANSPARENT, get_grid_dimensions
from gridfab.core.palette import Palette
from gridfab.core.animation import (
    discover_frames, is_animated, is_anim_subdir, frame_path,
    resolve_grid_path, resolve_palette_path,
    load_state, save_state, load_animations, save_animations,
    max_frame_number, swap_frame_files, update_animations_after_swap,
    discover_anim_dirs, load_subdir_animation, ANIM_FILE,
)
from gridfab.gui.pure import (
    ZOOM_LEVELS, DEFAULT_CELL_SIZE, CHECKER_LIGHT, CHECKER_DARK,
    TOOL_BRUSH, TOOL_EYEDROPPER, TOOL_FILL, SWATCH_COLS,
    checker_color, _contrast_color, format_status_text, grid_line_config,
    zoom_step, cell_at_coords, fit_zoom_level, cursor_preview_color,
    palette_key_to_index, palette_index_to_alias, render_frame_thumbnail,
    frame_strip_layout, blend_hex_colors, onion_skin_color,
    playback_frame_sequence, frame_interval_ms, frame_cell_at_coords,
    side_by_side_layout, anim_dir_choices, eyedropper_pick,
    cell_display_color,
)


class PixelEditor:
    def __init__(self, root: tk.Tk, work_dir: Path):
        self.root = root
        self.work_dir = work_dir

        # Animation subdirectory state
        self._is_anim_subdir = is_anim_subdir(work_dir)
        self._sprite_root = work_dir.parent if self._is_anim_subdir else work_dir

        self.palette_path = resolve_palette_path(self.work_dir) if (self.work_dir / "palette.txt").exists() or self._is_anim_subdir else self.work_dir / "palette.txt"

        self.palette = Palette.load(self.palette_path) if self.palette_path.exists() else Palette()

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
            self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
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

        # Window close handler
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Top-level grid layout ────────────────────────────────────
        # row 0: toolbar placeholder (future)
        # row 1: main content area (expands)
        # row 2: frame strip (conditional, grid_remove when hidden)
        # row 3: status bar (fixed height)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # Toolbar (row 0)
        from gridfab.gui.frames.toolbar import ToolbarFrame
        self.toolbar = ToolbarFrame(root, callbacks={
            "set_tool": lambda t: self._set_tool(t),
            "save": self.save,
            "render": self.render,
            "export": self._export,
            "toggle_grid": self._toggle_grid_lines,
            "zoom_in": lambda: self._zoom(1),
            "zoom_out": lambda: self._zoom(-1),
        })
        self.toolbar.grid(row=0, column=0, sticky="ew")

        # Menu bar
        from gridfab.gui.widgets.menu_bar import create_menu_bar
        self._menu_bar = create_menu_bar(root, callbacks={
            "save": self.save,
            "open": self.open_sprite,
            "refresh": self.refresh,
            "render": self.render,
            "export": self._export,
            "import_image": self.import_image,
            "new": self.new_grid,
            "exit": self._on_close,
            "undo": self.undo,
            "redo": self.redo,
            "clear": self.clear_grid,
            "flip_h": self._flip_horizontal,
            "flip_v": self._flip_vertical,
            "toggle_grid": self._toggle_grid_lines,
            "zoom_in": lambda: self._zoom(1),
            "zoom_out": lambda: self._zoom(-1),
            "side_by_side": self._toggle_side_by_side,
            "onion_skin": self._toggle_onion_skin,
            "add_frame": self._add_frame,
            "duplicate_frame": self._duplicate_frame,
            "delete_frame": self._delete_frame_gui,
            "copy_frame": self._copy_frame,
            "paste_frame": self._paste_frame,
            "play_stop": self._toggle_playback,
            "prev_frame": self._prev_frame,
            "next_frame": self._next_frame,
            "new_anim": self._new_anim_gui,
            "show_shortcuts": self._show_shortcuts,
            "about": self._show_about,
        })

        # Main content area (row 1)
        main = tk.Frame(root)
        main.grid(row=1, column=0, sticky="nsew")

        # Frame strip (row 2)
        from gridfab.gui.frames.frame_strip import FrameStrip
        self.frame_strip = FrameStrip(root, callbacks={
            "add_frame": self._add_frame,
            "duplicate": self._duplicate_frame,
            "delete": self._delete_frame_gui,
            "copy": self._copy_frame,
            "paste": self._paste_frame,
            "move_left": self._move_frame_left,
            "move_right": self._move_frame_right,
            "toggle_playback": self._toggle_playback,
            "on_fps_change": lambda fps: setattr(self, "_play_fps", fps),
            "on_anim_select": self._on_anim_select,
            "switch_frame": self._switch_frame,
            "toggle_frame_selection": self._toggle_frame_selection,
            "range_select_frames": self._range_select_frames,
            "on_anim_dir_select": self._on_anim_dir_select,
            "add_base_ref": self._add_base_ref_gui,
        })
        self._frame_strip_buttons: list[tk.Button] = []  # legacy compat
        if self._animated:
            self.frame_strip.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
            self._rebuild_frame_strip()

        # Status bar (row 3)
        from gridfab.gui.frames.status_bar import StatusBar
        self._status_bar = StatusBar(root)
        self._status_bar.grid(row=3, column=0, sticky="ew")
        self.status_var = self._status_bar.var

        # Palette panel (inside main, uses pack — separate parent)
        from gridfab.gui.frames.palette_panel import PalettePanel
        self.palette_panel = PalettePanel(main, callbacks={
            "select_color": self.select_color,
            "edit_color": self._edit_color,
            "add_color": self._add_color,
            "remove_color": self._remove_color,
            "copy_hex": self._copy_to_clipboard,
            "open": self.open_sprite,
            "refresh": self.refresh,
            "clear": self.clear_grid,
            "new": self.new_grid,
            "import_image": self.import_image,
            "animate": self._add_frame,
            "new_anim": self._new_anim_gui,
        })
        self.palette_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.palette_panel.rebuild(self.palette, self.selected)

        # Legacy aliases used by internal code
        self.palette_buttons: dict[str, tk.Button] = {}
        self.swatch_frame = self.palette_panel._swatch_frame
        self.palette_frame = self.palette_panel

        # Canvas (inside main, uses pack — separate parent)
        canvas_w = self.grid.width * self.cell_size
        canvas_h = self.grid.height * self.cell_size
        from gridfab.gui.frames.canvas_area import CanvasArea
        self.canvas_area = CanvasArea(main, canvas_w, canvas_h)
        self.canvas_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = self.canvas_area.canvas  # alias for all internal code

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
        root.bind("<Control-o>", lambda e: self.open_sprite())
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
        self.selected = alias
        if hasattr(self, "palette_panel"):
            self.palette_panel.set_selected(alias)
        self._update_status()

    def _set_tool(self, tool: str) -> None:
        self.tool = tool
        cursors = {
            TOOL_BRUSH: "",
            TOOL_EYEDROPPER: "crosshair",
            TOOL_FILL: "plus",
        }
        self.canvas.config(cursor=cursors.get(tool, ""))
        if hasattr(self, "toolbar"):
            self.toolbar.set_active_tool(tool)
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
            text += "  |  " + _("Playing")
        if self.onion_skin_enabled:
            pct = round(self.onion_skin_opacity * 100)
            text += "  |  " + _("Onion:{pct}%").format(pct=pct)
        if self._animated and self._active_frame is not None:
            text += "  |  " + _("Frame {n}").format(n=self._active_frame)
        if len(self._selected_frames) > 1:
            text += "  |  " + _("Selected: {n} frames").format(n=len(self._selected_frames))
        if self._is_anim_subdir:
            text += "  |  " + _("Anim:{name}").format(name=self.work_dir.name)
        if self._side_by_side:
            text += "  |  " + _("SBS")
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
            self._sync_zoom_label()
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
            self._sync_zoom_label()
            self._update_status()

    def _sync_zoom_label(self) -> None:
        if hasattr(self, "toolbar"):
            pct = round(self.cell_size / DEFAULT_CELL_SIZE * 100)
            self.toolbar.update_zoom(pct)

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
                self._frame_grids[f] = Grid.load(frame_path(self.work_dir, f), palette_path=self.palette_path)
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
        prev_grid = Grid.load(frame_path(self.work_dir, prev_num), palette_path=self.palette_path)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
        self._redraw()
        self._update_status()

    def _on_anim_select(self, value: str) -> None:
        """Handle animation dropdown selection."""
        if value == _("(All Frames)"):
            self._play_anim_name = None
        else:
            self._play_anim_name = value
        # If currently playing, restart with new sequence
        if self._playing:
            self._stop_playback()
            self._start_playback()

    # --- Frame strip and navigation ---

    def _rebuild_frame_strip(self) -> None:
        """Recreate frame strip via the FrameStrip widget."""
        frames = discover_frames(self.work_dir)
        animations = load_animations(self.work_dir)
        anim_names = [_("(All Frames)")] + sorted(animations.keys())
        dir_choices = anim_dir_choices(self._sprite_root)
        current_dir = self.work_dir.name if self._is_anim_subdir else "(Base)"

        self.frame_strip.rebuild(
            frames=frames,
            active_frame=self._active_frame,
            selected_frames=self._selected_frames,
            playing=self._playing,
            fps=self._play_fps,
            anim_dir_choices=dir_choices,
            current_anim_dir=current_dir,
            is_anim_subdir=self._is_anim_subdir,
            anim_names=anim_names,
            play_anim_name=self._play_anim_name,
        )
        # Keep _fps_var alias for playback code
        self._fps_var = self.frame_strip.fps_var

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
            self.grid = self._frame_grids.get(frame_num) or Grid.load(self.grid_path, palette_path=self.palette_path)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)

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
                    self._frame_grids[f] = Grid.load(frame_path(self.work_dir, f), palette_path=self.palette_path)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        if not self.frame_strip.winfo_ismapped():
            self.frame_strip.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
            show_warning(self.root, _("Cannot Delete"), _("Cannot delete the only frame."))
            return
        if not ask_yes_no(self.root, _("Delete Frame"), _("Delete frame {n}?").format(n=self._active_frame)):
            return
        from gridfab.commands.frame_cmd import cmd_frame_delete
        cmd_frame_delete(self.work_dir, self._active_frame)
        state = load_state(self.work_dir)
        self._active_frame = state.get("active_frame", 1)
        self.grid_path = frame_path(self.work_dir, self._active_frame)
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
        new_grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
        self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._rebuild_frame_strip()
        self._rebuild_canvas()
        self._update_status()

    # --- Animation subdirectory management ---

    def _on_anim_dir_select(self, value: str) -> None:
        """Handle animation directory dropdown selection."""
        if value == "(Base)":
            target = self._sprite_root
        else:
            target = self._sprite_root / value
        if target == self.work_dir:
            return
        self._switch_to_anim_dir(target)

    def _switch_to_anim_dir(self, target: Path) -> None:
        """Switch the editor to an animation subdirectory or back to base."""
        # Save current work
        if self.modified:
            self.grid.save(self.grid_path)
            self._set_modified(False)
        self._flush_multi_frame_changes()

        # Exit side-by-side if active
        if self._side_by_side:
            self._exit_side_by_side()

        # Update state
        self.work_dir = target
        self._is_anim_subdir = is_anim_subdir(target)
        self._sprite_root = target.parent if self._is_anim_subdir else target
        self.palette_path = resolve_palette_path(self.work_dir)

        # Reload palette and grid
        self.palette = Palette.load(self.palette_path)
        self._animated = is_animated(self.work_dir)
        if self._animated:
            state = load_state(self.work_dir)
            frames = discover_frames(self.work_dir)
            self._active_frame = state.get("active_frame", frames[0] if frames else 1)
            self.grid_path = frame_path(self.work_dir, self._active_frame)
        else:
            self._active_frame = None
            self.grid_path = self.work_dir / "grid.txt"

        if self.grid_path.exists():
            self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
        else:
            w, h = get_grid_dimensions(self.work_dir)
            self.grid = Grid.blank(w, h)

        # Reset undo/redo
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._selected_frames.clear()
        self._frame_grids.clear()
        self._frame_modified.clear()
        self._multi_undo_stack.clear()
        self._multi_redo_stack.clear()
        self._play_anim_name = None

        # Rebuild palette and canvas
        self._rebuild_palette_buttons()
        if self._animated:
            if not self.frame_strip.winfo_ismapped():
                self.frame_strip.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
            self._rebuild_frame_strip()
        else:
            self.frame_strip.grid_remove()
        self._rebuild_canvas(resize_viewport=True)
        self._update_title()
        self.select_color(TRANSPARENT)
        print(f"Switched to: {self.work_dir}")

    def _new_anim_gui(self) -> None:
        """Create a new animation subdirectory via GUI dialog."""
        name = ask_string(self.root, _("New Animation"), _("Enter animation name (becomes folder name):"))
        if not name:
            return
        # Validate name (no special chars)
        if not name.isidentifier() and not all(c.isalnum() or c in "_-" for c in name):
            show_error(self.root, _("Invalid Name"), _("Use only letters, numbers, hyphens, underscores."))
            return

        target_root = self._sprite_root
        try:
            from gridfab.commands.anim_cmd import cmd_anim_create
            cmd_anim_create(target_root, name)
        except FileExistsError as e:
            show_error(self.root, _("Error"), str(e))
            return

        # Switch to the new animation directory
        self._switch_to_anim_dir(target_root / name)
        show_info(self.root, _("Animation Created"),
                  _("Animation '{name}' created.\nUse '+' to add frames.").format(name=name))

    def _add_base_ref_gui(self) -> None:
        """Add a base frame reference to the animation subdir's animation.json."""
        if not self._is_anim_subdir:
            return
        # Get base frames
        base_frames = discover_frames(self._sprite_root)
        if not base_frames:
            show_warning(self.root, _("No Base Frames"), _("No frames in the base sprite directory."))
            return

        # Ask which base frame to reference
        frame_str = ask_string(
            self.root, _("Add Base Frame Reference"),
            _("Available base frames: {frames}\n\nEnter frame number:").format(frames=base_frames),
        )
        if not frame_str:
            return
        try:
            frame_num = int(frame_str)
        except ValueError:
            show_error(self.root, _("Invalid"), _("Frame number must be an integer."))
            return
        if frame_num not in base_frames:
            show_error(self.root, _("Invalid"),
                       _("Frame {n} not found in base (available: {frames}).").format(n=frame_num, frames=base_frames))
            return

        # Add "base:N" to animation.json
        import json
        anim = load_subdir_animation(self.work_dir)
        anim["frames"].append(f"base:{frame_num}")
        anim_path = self.work_dir / "animation.json"
        with open(anim_path, "w", newline="\n") as f:
            json.dump(anim, f, indent=2)
            f.write("\n")
        print(f"Added base:{frame_num} reference to {self.work_dir.name}/animation.json")

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
            self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
        self._rebuild_palette_buttons()
        self.select_color(self.selected)
        self._redraw()
        print("Refreshed from disk")

    def clear_grid(self) -> None:
        if not ask_yes_no(self.root, _("Clear Grid"), _("Reset all pixels to transparent?")):
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
            choice = ask_yes_no(
                self.root, _("New"),
                _("Create a new grid in the current folder?\n\n"
                  "Yes = Resize current grid here\n"
                  "No = Create a new sprite in another folder"),
            )
            if choice:
                self._new_grid_here()
                return
            else:
                self._new_sprite()
                return
        else:
            self._new_sprite()

    def _new_grid_here(self) -> None:
        size_str = ask_string(self.root, _("New Grid"), _("Enter size as WxH (e.g. 16x16, 32x32):"))
        if not size_str:
            return
        parts = size_str.lower().split("x")
        if len(parts) != 2:
            show_error(self.root, _("Invalid Size"), _("Size must be WxH (e.g. 32x32)"))
            return
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            show_error(self.root, _("Invalid Size"), _("Width and height must be integers"))
            return
        if w < 1 or h < 1:
            show_error(self.root, _("Invalid Size"), _("Width and height must be positive"))
            return
        if not ask_yes_no(
            self.root, _("New Grid"),
            _("Create new {w}x{h} grid? This will replace the current grid.").format(w=w, h=h),
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
            title=_("Choose parent folder for new sprite"),
            parent=self.root,
        )
        if not parent:
            return

        name = ask_string(self.root, _("Sprite Name"), _("Enter sprite name (becomes folder name):"))
        if not name:
            return

        size_str = ask_string(self.root, _("Grid Size"), _("Enter size as WxH (e.g. 16x16, 32x32):"))
        if not size_str:
            return
        parts = size_str.lower().split("x")
        if len(parts) != 2:
            show_error(self.root, _("Invalid Size"), _("Size must be WxH (e.g. 32x32)"))
            return
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            show_error(self.root, _("Invalid Size"), _("Width and height must be integers"))
            return
        if w < 1 or h < 1:
            show_error(self.root, _("Invalid Size"), _("Width and height must be positive"))
            return

        new_dir = Path(parent) / name
        try:
            from gridfab.commands.init import cmd_init
            cmd_init(new_dir, w, h)
        except FileExistsError as e:
            show_error(self.root, _("Error"), str(e))
            return

        self._switch_to_dir(new_dir)
        print(f"Created new sprite: {new_dir}")

    def open_sprite(self) -> None:
        folder = filedialog.askdirectory(
            title=_("Open sprite folder"),
            parent=self.root,
        )
        if not folder:
            return

        folder_path = Path(folder)
        if not (folder_path / "grid.txt").exists() and not is_animated(folder_path):
            show_error(
                self.root, _("Not a Sprite"),
                _("No grid.txt or frame files found in {name}\n\n"
                  "Select a folder containing grid.txt and palette.txt.").format(name=folder_path.name),
            )
            return

        self._switch_to_dir(folder_path)
        print(f"Opened sprite: {folder_path}")

    def import_image(self) -> None:
        image_path = filedialog.askopenfilename(
            title=_("Select image to import"),
            filetypes=[
                (_("Image files"),
                 "*.png *.bmp *.dib *.gif *.tiff *.tif *.webp *.jpg *.jpeg *.jpe "
                 "*.jp2 *.jpx *.j2k *.ico *.icns *.tga *.pcx *.ppm *.pbm *.pgm *.pnm "
                 "*.sgi *.xbm *.dds *.eps *.qoi *.psd *.cur *.fli *.flc *.xpm "
                 "*.wmf *.emf *.fits *.msp *.blp *.avif"),
                (_("All files"), "*.*"),
            ],
            parent=self.root,
        )
        if not image_path:
            return

        name = ask_string(self.root, _("Sprite Name"), _("Enter sprite name (becomes folder name):"))
        if not name:
            return

        tile_str = ask_string(
            self.root, _("Tilesheet?"),
            _("If this is a tilesheet, enter tile size as WxH.\n"
              "Leave blank for single image import."),
        )

        new_dir = self.work_dir / name
        try:
            from gridfab.commands.import_cmd import cmd_import
            from gridfab.cli import parse_size

            if tile_str and tile_str.strip():
                tile_size = parse_size(tile_str.strip())
                tile_coord = ask_string(
                    self.root, _("Tile Position"),
                    _("Enter tile coordinate as COL,ROW (0-indexed):"),
                )
                if not tile_coord:
                    return
                parts = tile_coord.split(",")
                if len(parts) != 2:
                    show_error(self.root, _("Invalid"), _("Must be COL,ROW (e.g. 3,2)"))
                    return
                try:
                    tile_pos = (int(parts[0]), int(parts[1]))
                except ValueError:
                    show_error(self.root, _("Invalid"), _("Coordinates must be integers"))
                    return
                cmd_import(
                    Path(image_path), new_dir,
                    tile_size=tile_size, tile_pos=tile_pos,
                )
            else:
                cmd_import(Path(image_path), new_dir)

            self._switch_to_dir(new_dir)
            show_info(self.root, _("Import Complete"), _("Imported to {name}").format(name=new_dir.name))
        except (ValueError, FileExistsError, FileNotFoundError) as e:
            show_error(self.root, _("Import Error"), str(e))

    def _switch_to_dir(self, new_dir: Path) -> None:
        """Switch the editor to a different sprite directory."""
        self.work_dir = new_dir
        self._is_anim_subdir = is_anim_subdir(new_dir)
        self._sprite_root = new_dir.parent if self._is_anim_subdir else new_dir
        try:
            self.palette_path = resolve_palette_path(new_dir)
        except FileNotFoundError:
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
            self.grid = Grid.load(self.grid_path, palette_path=self.palette_path)
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
                self.frame_strip.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
            self._rebuild_frame_strip()
        else:
            self.frame_strip.grid_remove()

        # Rebuild canvas
        self._rebuild_canvas(resize_viewport=True)

        # Update title and status
        self._update_title()
        self.select_color(TRANSPARENT)

    def _rebuild_palette_buttons(self) -> None:
        """Rebuild palette panel swatches."""
        if hasattr(self, "palette_panel"):
            self.palette_panel.rebuild(self.palette, self.selected)

    def _add_color(self) -> None:
        """Open color picker and add a new color to the palette."""
        result = colorchooser.askcolor(parent=self.root, title=_("Choose a color"))
        if result[1] is None:
            return
        hex_color = result[1].upper()

        alias = ask_string(self.root, _("Alias"), _("Enter alias (1-2 characters):"))
        if not alias:
            return

        try:
            Palette._validate_alias(alias)
        except ValueError as e:
            show_error(self.root, _("Invalid Alias"), str(e))
            return

        # Check case-insensitive duplicates
        for existing in self.palette.entries:
            if existing == TRANSPARENT:
                continue
            if existing.lower() == alias.lower():
                show_error(
                    self.root, _("Duplicate Alias"),
                    _("Alias '{alias}' conflicts with existing alias '{existing}' "
                      "(case-insensitive duplicates not allowed)").format(alias=alias, existing=existing),
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
            initialcolor=current, parent=self.root, title=_("Edit color: {alias}").format(alias=alias),
        )
        if result[1] is None:
            return
        self.palette.entries[alias] = result[1].upper()
        self.palette.save(self.palette_path)
        self._rebuild_palette_buttons()
        self.select_color(alias)
        self._redraw()

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _remove_color(self, alias: str) -> None:
        """Remove a color from the palette after confirmation."""
        if not ask_yes_no(
            self.root, _("Remove Color"),
            _("Remove '{alias}' from the palette?\n\n"
              "Cells using this color will show as magenta (unknown).").format(alias=alias),
        ):
            return
        del self.palette.entries[alias]
        self.palette.save(self.palette_path)
        if self.selected == alias:
            self.selected = TRANSPARENT
        self._rebuild_palette_buttons()
        self.select_color(self.selected)
        self._redraw()

    def _on_close(self) -> None:
        """Handle window close with unsaved-changes prompt."""
        if self.modified:
            result = ask_yes_no_cancel(
                self.root, _("Unsaved Changes"),
                _("You have unsaved changes. Save before closing?"),
            )
            if result is None:  # Cancel
                return
            if result:  # Yes — save first
                self.save()
        self.root.destroy()

    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts = (
            _("B — Brush tool") + "\n"
            + _("I — Eyedropper tool") + "\n"
            + _("F — Fill tool") + "\n"
            + _("G — Toggle grid lines") + "\n"
            + _("H — Flip horizontal") + "\n"
            + _("V — Flip vertical") + "\n"
            + _("R — Render preview") + "\n"
            + _("E — Export PNGs") + "\n"
            + _("O — Toggle onion skin") + "\n"
            + _("M — Toggle side-by-side") + "\n"
            + _("[ / ] — Zoom out / in") + "\n"
            + _("< / > — Previous / next frame") + "\n"
            + _("Space — Play / stop animation") + "\n"
            + _("Ctrl+S — Save") + "\n"
            + _("Ctrl+O — Open") + "\n"
            + _("Ctrl+Z — Undo") + "\n"
            + _("Ctrl+Y — Redo") + "\n"
            + _("Ctrl+C — Copy frame") + "\n"
            + _("Ctrl+V — Paste frame") + "\n"
            + _("1-9 — Select palette color")
        )
        show_info(self.root, _("Keyboard Shortcuts"), shortcuts)

    def _show_about(self) -> None:
        """Show about dialog."""
        import gridfab
        version = getattr(gridfab, "__version__", "unknown")
        show_info(
            self.root, _("About GridFab"),
            _("GridFab v{version}\n\n"
              "A pixel art editor where artwork\n"
              "is stored as plain text.\n\n"
              "grid.txt + palette.txt = art\n\n"
              "Licensed under AGPLv3").format(version=version),
        )

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


def main(work_dir=None) -> None:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    if work_dir is None:
        work_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    work_dir = Path(work_dir)
    root = ctk.CTk()
    root.geometry("1024x768")
    root.minsize(800, 600)
    PixelEditor(root, work_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
