"""Toolbar frame for GridFab GUI."""

import tkinter as tk

try:
    import customtkinter as ctk
    _Frame = ctk.CTkFrame
    _Button = ctk.CTkButton
except ImportError:
    _Frame = tk.Frame
    _Button = tk.Button

from gridfab.gui.i18n import _
from gridfab.gui.tokens import (
    BG_ELEVATED, BORDER, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    HOVER_BUTTON, TOOLBAR_HEIGHT, PAD_SM, PAD_MD,
    FONT_BODY, FONT_SMALL,
)
from gridfab.gui.widgets.tooltip import attach_tooltip


class ToolbarFrame(_Frame):
    """Horizontal toolbar at the top of the editor window."""

    def __init__(self, master, callbacks: dict, **kwargs):
        """Create the toolbar.

        callbacks dict keys:
            set_tool(tool_name), save, render, export,
            toggle_grid, zoom_in, zoom_out
        """
        super().__init__(
            master, height=TOOLBAR_HEIGHT, fg_color=BG_ELEVATED, corner_radius=0,
            **kwargs,
        )
        self.grid_propagate(False)
        self._callbacks = callbacks
        self._tool_buttons: dict[str, _Button] = {}
        self._active_tool = "Brush"

        # ── Tool group ───────────────────────────────────────────────
        tool_frame = tk.Frame(self, bg=BG_ELEVATED)
        tool_frame.pack(side=tk.LEFT, padx=(PAD_MD, PAD_SM))

        for tool, label, shortcut in [
            ("Brush", _("Brush"), "B"),
            ("Eyedropper", _("Eyedropper"), "I"),
            ("Fill", _("Fill"), "F"),
        ]:
            btn = _Button(
                tool_frame, text=label, width=80, height=28,
                font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, corner_radius=4,
                command=lambda t=tool: self._on_tool(t),
            )
            btn.pack(side=tk.LEFT, padx=1)
            attach_tooltip(btn, _("{tool} ({shortcut})").format(tool=label, shortcut=shortcut))
            self._tool_buttons[tool] = btn

        self._highlight_tool("Brush")

        # ── Separator ────────────────────────────────────────────────
        self._sep(self)

        # ── Action group ─────────────────────────────────────────────
        action_frame = tk.Frame(self, bg=BG_ELEVATED)
        action_frame.pack(side=tk.LEFT, padx=PAD_SM)

        for label, key, tip in [
            (_("Save"), "save", _("Save (Ctrl+S)")),
            (_("Render"), "render", _("Render (R)")),
            (_("Export"), "export", _("Export (E)")),
        ]:
            btn = _Button(
                action_frame, text=label, width=70, height=28,
                font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, corner_radius=4,
                command=callbacks.get(key, lambda: None),
            )
            btn.pack(side=tk.LEFT, padx=1)
            attach_tooltip(btn, tip)

        # ── Separator ────────────────────────────────────────────────
        self._sep(self)

        # ── Grid toggle ──────────────────────────────────────────────
        self._grid_btn = _Button(
            self, text=_("Grid"), width=60, height=28,
            font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, corner_radius=4,
            command=callbacks.get("toggle_grid", lambda: None),
        )
        self._grid_btn.pack(side=tk.LEFT, padx=PAD_SM)
        attach_tooltip(self._grid_btn, _("Grid Lines (G)"))

        # ── Separator ────────────────────────────────────────────────
        self._sep(self)

        # ── Zoom controls ────────────────────────────────────────────
        zoom_frame = tk.Frame(self, bg=BG_ELEVATED)
        zoom_frame.pack(side=tk.LEFT, padx=PAD_SM)

        btn_zout = _Button(
            zoom_frame, text="-", width=28, height=28,
            font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, corner_radius=4,
            command=callbacks.get("zoom_out", lambda: None),
        )
        btn_zout.pack(side=tk.LEFT)
        attach_tooltip(btn_zout, _("Zoom Out ([)"))

        self._zoom_label = tk.Label(
            zoom_frame, text="100%", width=5,
            bg=BG_ELEVATED, fg=TEXT_SECONDARY, font=FONT_SMALL,
        )
        self._zoom_label.pack(side=tk.LEFT, padx=2)

        btn_zin = _Button(
            zoom_frame, text="+", width=28, height=28,
            font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, corner_radius=4,
            command=callbacks.get("zoom_in", lambda: None),
        )
        btn_zin.pack(side=tk.LEFT)
        attach_tooltip(btn_zin, _("Zoom In (])"))

    def _sep(self, parent) -> None:
        """Add a 1px vertical separator."""
        sep = tk.Frame(parent, width=1, bg=BORDER)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=PAD_SM, pady=6)

    def _on_tool(self, tool: str) -> None:
        self._active_tool = tool
        self._highlight_tool(tool)
        cb = self._callbacks.get("set_tool")
        if cb:
            cb(tool)

    def _highlight_tool(self, active: str) -> None:
        for name, btn in self._tool_buttons.items():
            if name == active:
                btn.configure(fg_color=ACCENT)
            else:
                btn.configure(fg_color="transparent")

    def set_active_tool(self, tool: str) -> None:
        """Called from PixelEditor when tool changes via keyboard."""
        self._active_tool = tool
        self._highlight_tool(tool)

    def update_zoom(self, pct: int) -> None:
        """Update the zoom percentage label."""
        self._zoom_label.config(text=f"{pct}%")
