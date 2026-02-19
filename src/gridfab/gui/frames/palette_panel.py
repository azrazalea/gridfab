"""Palette panel for GridFab GUI — swatch grid + action buttons."""

import tkinter as tk

try:
    import customtkinter as ctk
    _Frame = ctk.CTkFrame
    _Button = ctk.CTkButton
except ImportError:
    _Frame = tk.Frame
    _Button = tk.Button

from gridfab.core.grid import TRANSPARENT
from gridfab.core.palette import Palette
from gridfab.gui.pure import _contrast_color, SWATCH_COLS
from gridfab.gui.tokens import (
    BG_SURFACE, BG_ELEVATED, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, BORDER, HOVER_BUTTON,
    PALETTE_WIDTH, PAD_SM, PAD_MD, PAD_LG,
    FONT_HEADER, FONT_BODY, FONT_SMALL,
    MENU_BG, MENU_FG, MENU_ACTIVE_BG, MENU_ACTIVE_FG, MENU_DISABLED_FG,
)
from gridfab.gui.widgets.tooltip import attach_tooltip


class PalettePanel(_Frame):
    """Left sidebar with color swatches and action buttons."""

    def __init__(self, master, callbacks: dict, **kwargs):
        """Create the palette panel.

        callbacks dict keys:
            select_color(alias), edit_color(alias), add_color,
            remove_color(alias), copy_hex(hex), context_menu(event, alias),
            open, refresh, clear, new, import_image, animate, new_anim
        """
        super().__init__(
            master, width=PALETTE_WIDTH, fg_color=BG_SURFACE, corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(True)
        self._callbacks = callbacks
        self._swatch_buttons: dict[str, _Button] = {}
        self._selected_alias: str = TRANSPARENT

        # ── PALETTE header ───────────────────────────────────────────
        header = tk.Label(
            self, text="PALETTE", font=FONT_HEADER,
            bg=BG_SURFACE, fg=TEXT_SECONDARY, anchor=tk.W,
        )
        header.pack(fill=tk.X, padx=PAD_MD, pady=(PAD_MD, PAD_SM))

        # ── Swatch grid ─────────────────────────────────────────────
        self._swatch_frame = tk.Frame(self, bg=BG_SURFACE)
        self._swatch_frame.pack(fill=tk.X, padx=PAD_MD, pady=PAD_SM)

        # ── Separator ────────────────────────────────────────────────
        sep = tk.Frame(self, height=1, bg=BORDER)
        sep.pack(fill=tk.X, padx=PAD_MD, pady=PAD_MD)

        # ── ACTIONS header ───────────────────────────────────────────
        actions_header = tk.Label(
            self, text="ACTIONS", font=FONT_HEADER,
            bg=BG_SURFACE, fg=TEXT_SECONDARY, anchor=tk.W,
        )
        actions_header.pack(fill=tk.X, padx=PAD_MD, pady=(0, PAD_SM))

        # ── Action buttons ───────────────────────────────────────────
        self._action_frame = tk.Frame(self, bg=BG_SURFACE)
        self._action_frame.pack(fill=tk.X, padx=PAD_MD)

        action_items = [
            ("Open", callbacks.get("open"), "Open sprite folder (Ctrl+O)"),
            ("Refresh", callbacks.get("refresh"), "Reload files from disk"),
            ("Clear", callbacks.get("clear"), "Reset all pixels to transparent"),
            ("New", callbacks.get("new"), "Create a new sprite"),
            ("Import", callbacks.get("import_image"), "Import an image as a sprite"),
            ("Animate", callbacks.get("animate"), "Add animation frames"),
            ("+ Anim", callbacks.get("new_anim"), "Create animation subdirectory"),
        ]
        for i, (text, cmd, tip) in enumerate(action_items):
            btn = _Button(
                self._action_frame, text=text, width=100, height=26,
                font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, corner_radius=4,
                command=cmd or (lambda: None),
            )
            btn.grid(row=i // 2, column=i % 2, padx=2, pady=2, sticky="ew")
            attach_tooltip(btn, tip)
        self._action_frame.grid_columnconfigure(0, weight=1)
        self._action_frame.grid_columnconfigure(1, weight=1)

    def rebuild(self, palette: Palette, selected: str) -> None:
        """Rebuild swatch buttons from current palette state."""
        for widget in self._swatch_frame.winfo_children():
            widget.destroy()
        self._swatch_buttons.clear()
        self._selected_alias = selected

        # Transparent first, then sorted colors
        items: list[tuple[str, str]] = [(TRANSPARENT, "#FFFFFF")]
        for alias, color in sorted(palette.colors.items()):
            items.append((alias, color if color else "#FFFFFF"))

        for i, (alias, color) in enumerate(items):
            is_sel = alias == selected
            fg = _contrast_color(color)
            text = "." if alias == TRANSPARENT else alias

            btn = _Button(
                self._swatch_frame, text=text,
                width=60, height=36,
                font=FONT_BODY,
                fg_color=color, hover_color=color,
                text_color=fg, corner_radius=4,
                border_width=SWATCH_SEL_W if is_sel else 0,
                border_color=ACCENT if is_sel else BORDER,
                command=lambda a=alias: self._on_select(a),
            )
            btn.grid(row=i // SWATCH_COLS, column=i % SWATCH_COLS, padx=2, pady=2)

            if alias != TRANSPARENT:
                btn.bind("<Double-Button-1>", lambda e, a=alias: self._on_edit(a))
            btn.bind("<Button-3>", lambda e, a=alias: self._on_context(e, a))
            self._swatch_buttons[alias] = btn

        # "+" add button
        add_pos = len(items)
        add_btn = _Button(
            self._swatch_frame, text="+",
            width=60, height=36,
            font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, corner_radius=4,
            command=self._callbacks.get("add_color", lambda: None),
        )
        add_btn.grid(
            row=add_pos // SWATCH_COLS, column=add_pos % SWATCH_COLS,
            padx=2, pady=2,
        )

    def set_selected(self, alias: str) -> None:
        """Update selection highlight without full rebuild."""
        old = self._selected_alias
        self._selected_alias = alias
        if old in self._swatch_buttons:
            self._swatch_buttons[old].configure(border_width=0, border_color=BORDER)
        if alias in self._swatch_buttons:
            self._swatch_buttons[alias].configure(border_width=SWATCH_SEL_W, border_color=ACCENT)

    def _on_select(self, alias: str) -> None:
        cb = self._callbacks.get("select_color")
        if cb:
            cb(alias)

    def _on_edit(self, alias: str) -> None:
        cb = self._callbacks.get("edit_color")
        if cb:
            cb(alias)

    def _on_context(self, event: tk.Event, alias: str) -> None:
        """Show dark-themed right-click context menu."""
        menu = tk.Menu(
            self, tearoff=0,
            bg=MENU_BG, fg=MENU_FG,
            activebackground=MENU_ACTIVE_BG, activeforeground=MENU_ACTIVE_FG,
            disabledforeground=MENU_DISABLED_FG,
        )
        if alias == TRANSPARENT:
            menu.add_command(label="Transparent (no actions)", state=tk.DISABLED)
        else:
            cb_copy = self._callbacks.get("copy_hex")
            cb_edit = self._callbacks.get("edit_color")
            cb_remove = self._callbacks.get("remove_color")
            # Get hex from button's fg_color
            btn = self._swatch_buttons.get(alias)
            hex_color = ""
            if btn:
                try:
                    hex_color = btn.cget("fg_color")
                except Exception:
                    pass
            menu.add_command(
                label=f"Copy Hex ({hex_color})",
                command=lambda: cb_copy(hex_color) if cb_copy else None,
            )
            menu.add_command(
                label="Edit Color...",
                command=lambda: cb_edit(alias) if cb_edit else None,
            )
            menu.add_separator()
            menu.add_command(
                label="Remove Color",
                command=lambda: cb_remove(alias) if cb_remove else None,
            )
        menu.tk_popup(event.x_root, event.y_root)


SWATCH_SEL_W = 2
