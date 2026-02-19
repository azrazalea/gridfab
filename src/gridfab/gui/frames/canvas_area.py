"""Canvas area frame for GridFab GUI — wraps tk.Canvas in a dark container."""

import tkinter as tk

try:
    import customtkinter as ctk
    _Frame = ctk.CTkFrame
except ImportError:
    _Frame = tk.Frame

from gridfab.gui.tokens import BG_BASE


class CanvasArea(_Frame):
    """Container for the pixel art canvas with dark background."""

    def __init__(self, master, canvas_w: int, canvas_h: int, **kwargs):
        super().__init__(master, fg_color=BG_BASE, corner_radius=0, **kwargs)

        self.canvas = tk.Canvas(
            self,
            width=min(canvas_w, 800),
            height=min(canvas_h, 600),
            highlightthickness=0,
            bg=BG_BASE,
            scrollregion=(0, 0, canvas_w, canvas_h),
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
