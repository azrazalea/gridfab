"""StatusBar frame for GridFab GUI."""

import tkinter as tk

try:
    import customtkinter as ctk
    _Frame = ctk.CTkFrame
except ImportError:
    _Frame = tk.Frame

from gridfab.gui.tokens import (
    BG_ELEVATED, TEXT_SECONDARY, FONT_STATUS, STATUS_BAR_HEIGHT, PAD_SM,
)


class StatusBar(_Frame):
    """Fixed-height status bar at the bottom of the editor."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=STATUS_BAR_HEIGHT,
            fg_color=BG_ELEVATED,
            corner_radius=0,
            **kwargs,
        )
        self.grid_propagate(False)

        self._var = tk.StringVar()
        self._label = tk.Label(
            self,
            textvariable=self._var,
            anchor=tk.W,
            bg=BG_ELEVATED,
            fg=TEXT_SECONDARY,
            font=FONT_STATUS,
            padx=PAD_SM + 2,
        )
        self._label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    @property
    def var(self) -> tk.StringVar:
        return self._var

    def set(self, text: str) -> None:
        self._var.set(text)
