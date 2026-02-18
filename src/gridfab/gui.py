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
        self.grid_path = self.work_dir / "grid.txt"
        self.palette_path = self.work_dir / "palette.txt"

        self.palette = Palette.load(self.palette_path)

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
        self.canvas.pack(side=tk.LEFT, padx=5, pady=5)

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
        x0 = c * cs
        y0 = r * cs
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
        self.status_var.set(text)

    def _toggle_grid_lines(self) -> None:
        self.grid_lines_visible = not self.grid_lines_visible
        cfg = grid_line_config(self.grid_lines_visible)
        for row in self.cells:
            for rect in row:
                self.canvas.itemconfig(rect, **cfg)

    def _on_mousewheel(self, event: tk.Event) -> None:
        direction = 1 if event.delta > 0 else -1
        new_size = zoom_step(self.cell_size, direction)
        if new_size != self.cell_size:
            self.cell_size = new_size
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
            self._rebuild_canvas()
            self._update_status()

    def cell_at(self, event: tk.Event) -> tuple[int | None, int | None]:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        return cell_at_coords(x, y, self.cell_size, self.grid.width, self.grid.height)

    def _begin_stroke(self) -> None:
        if not self._stroke_active:
            self.undo_stack.append(self.grid.snapshot())
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            self._stroke_active = True

    def paint(self, r: int | None, c: int | None, value: str) -> None:
        if r is None or c is None:
            return
        self._begin_stroke()
        self.grid.data[r][c] = value
        color = cell_display_color(value, self.palette, r, c)
        self.canvas.itemconfig(self.cells[r][c], fill=color)
        self._set_modified()

    def on_click(self, event: tk.Event) -> None:
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
        self.undo_stack.append(self.grid.snapshot())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.grid.flood_fill(r, c, self.selected)
        self._redraw()
        self._set_modified()

    def on_right_click(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        self.paint(r, c, TRANSPARENT)

    def on_right_drag(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        self.paint(r, c, TRANSPARENT)

    def on_release(self, event: tk.Event) -> None:
        self._stroke_active = False

    def undo(self) -> None:
        if not self.undo_stack:
            return
        self.redo_stack.append(self.grid.snapshot())
        snapshot = self.undo_stack.pop()
        self.grid.restore(snapshot)
        self._redraw()

    def redo(self) -> None:
        if not self.redo_stack:
            return
        self.undo_stack.append(self.grid.snapshot())
        snapshot = self.redo_stack.pop()
        self.grid.restore(snapshot)
        self._redraw()

    def _redraw(self) -> None:
        self._clear_preview()
        for r in range(self.grid.height):
            for c in range(self.grid.width):
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                self.canvas.itemconfig(self.cells[r][c], fill=color)

    def save(self) -> None:
        self.grid.save(self.grid_path)
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
        self._rebuild_canvas()
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
        if not (folder_path / "grid.txt").exists():
            messagebox.showerror(
                "Not a Sprite",
                f"No grid.txt found in {folder_path.name}\n\n"
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
        self.grid_path = new_dir / "grid.txt"
        self.palette_path = new_dir / "palette.txt"

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

        # Rebuild canvas
        self._rebuild_canvas()

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

    def _rebuild_canvas(self) -> None:
        """Rebuild the canvas for a new grid size."""
        cs = self.cell_size
        canvas_w = self.grid.width * cs
        canvas_h = self.grid.height * cs
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
        subprocess.run(
            [sys.executable, "-m", "gridfab", "render", str(self.work_dir)],
        )
        print("Rendered preview.png")


def main() -> None:
    work_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    root = tk.Tk()
    PixelEditor(root, Path(work_dir))
    root.mainloop()


if __name__ == "__main__":
    main()
