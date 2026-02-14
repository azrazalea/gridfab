"""GridFab GUI — tkinter-based pixel art editor.

Left-click to paint with selected color, right-click to erase (transparent).

Usage: gridfab-gui [directory]
  directory: folder containing grid.txt and palette.txt (default: current dir)
"""

import sys
import subprocess
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path

from gridfab.core.grid import Grid, TRANSPARENT, get_grid_dimensions
from gridfab.core.palette import Palette

CELL_SIZE = 16
CHECKER_LIGHT = "#DCDCDC"
CHECKER_DARK = "#B4B4B4"


def checker_color(r: int, c: int) -> str:
    """Return checkerboard color for a transparent cell."""
    return CHECKER_LIGHT if (r // 2 + c // 2) % 2 == 0 else CHECKER_DARK


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

        # Undo/redo stacks
        self.undo_stack: list[list[list[str]]] = []
        self.redo_stack: list[list[list[str]]] = []
        self.max_undo = 512
        self._stroke_active = False

        root.title(f"GridFab — {self.work_dir.resolve().name}")

        # Main layout
        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True)

        # Palette panel
        palette_frame = tk.Frame(main, padx=5, pady=5)
        palette_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(palette_frame, text="Palette", font=("Arial", 10, "bold")).pack()

        self.palette_buttons: dict[str, tk.Button] = {}

        # Transparent button
        btn = tk.Button(
            palette_frame, text=".", width=3, height=1, relief=tk.SUNKEN,
            bg="#FFFFFF", command=lambda: self.select_color(TRANSPARENT),
        )
        btn.pack(pady=2)
        self.palette_buttons[TRANSPARENT] = btn

        for alias, color in sorted(self.palette.colors.items()):
            display = color if color else "#FFFFFF"
            btn = tk.Button(
                palette_frame, text=alias, width=3, height=1,
                bg=display,
                command=lambda a=alias: self.select_color(a),
            )
            btn.pack(pady=2)
            self.palette_buttons[alias] = btn

        # Action buttons
        tk.Button(
            palette_frame, text="Save", width=6, command=self.save, bg="#90EE90",
        ).pack(pady=10)
        tk.Button(
            palette_frame, text="Render", width=6, command=self.render, bg="#ADD8E6",
        ).pack(pady=2)
        tk.Button(
            palette_frame, text="Refresh", width=6, command=self.refresh, bg="#FFD700",
        ).pack(pady=2)
        tk.Button(
            palette_frame, text="Clear", width=6, command=self.clear_grid, bg="#FFA07A",
        ).pack(pady=2)
        tk.Button(
            palette_frame, text="New", width=6, command=self.new_grid, bg="#DDA0DD",
        ).pack(pady=2)

        # Canvas
        canvas_w = self.grid.width * CELL_SIZE
        canvas_h = self.grid.height * CELL_SIZE
        self.canvas = tk.Canvas(
            main, width=canvas_w, height=canvas_h, highlightthickness=0,
        )
        self.canvas.pack(side=tk.LEFT, padx=5, pady=5)

        # Draw cells
        self.cells: list[list[int]] = []
        for r in range(self.grid.height):
            row_cells: list[int] = []
            for c in range(self.grid.width):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                rect = self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill=color, outline="#333333", width=0.5,
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

        # Keyboard bindings
        root.bind("<Control-s>", lambda e: self.save())
        root.bind("<Control-z>", lambda e: self.undo())
        root.bind("<Control-y>", lambda e: self.redo())
        root.bind("<Control-Shift-Z>", lambda e: self.redo())

        self.select_color(TRANSPARENT)

    def select_color(self, alias: str) -> None:
        for a, btn in self.palette_buttons.items():
            btn.config(relief=tk.SUNKEN if a == alias else tk.RAISED)
        self.selected = alias

    def cell_at(self, event: tk.Event) -> tuple[int | None, int | None]:
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if 0 <= r < self.grid.height and 0 <= c < self.grid.width:
            return r, c
        return None, None

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

    def on_click(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        self.paint(r, c, self.selected)

    def on_drag(self, event: tk.Event) -> None:
        r, c = self.cell_at(event)
        self.paint(r, c, self.selected)

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
        for r in range(self.grid.height):
            for c in range(self.grid.width):
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                self.canvas.itemconfig(self.cells[r][c], fill=color)

    def save(self) -> None:
        self.grid.save(self.grid_path)
        print("Saved grid.txt")

    def refresh(self) -> None:
        self.undo_stack.append(self.grid.snapshot())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.palette = Palette.load(self.palette_path)
        if self.grid_path.exists():
            self.grid = Grid.load(self.grid_path)
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

    def _rebuild_canvas(self) -> None:
        """Rebuild the canvas for a new grid size."""
        canvas_w = self.grid.width * CELL_SIZE
        canvas_h = self.grid.height * CELL_SIZE
        self.canvas.config(width=canvas_w, height=canvas_h)
        self.canvas.delete("all")
        self.cells = []
        for r in range(self.grid.height):
            row_cells: list[int] = []
            for c in range(self.grid.width):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                color = cell_display_color(
                    self.grid.data[r][c], self.palette, r, c,
                )
                rect = self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill=color, outline="#333333", width=0.5,
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
