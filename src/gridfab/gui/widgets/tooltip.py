"""Tooltip widget for GridFab GUI — hover delay, dark themed."""

import tkinter as tk
from gridfab.gui.tokens import TOOLTIP_BG, TOOLTIP_FG, TOOLTIP_BORDER, FONT_TOOLTIP


class Tooltip:
    """A tooltip that appears after hovering over a widget for 500ms."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id: str | None = None
        self._toplevel: tk.Toplevel | None = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event: tk.Event) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event: tk.Event) -> None:
        self._cancel()
        self._hide()

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._toplevel is not None:
            return
        x = self.widget.winfo_rootx() + 4
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self._toplevel = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)
        frame = tk.Frame(
            tw, bg=TOOLTIP_BORDER, padx=1, pady=1,
        )
        frame.pack()
        label = tk.Label(
            frame, text=self.text,
            bg=TOOLTIP_BG, fg=TOOLTIP_FG,
            font=FONT_TOOLTIP, padx=6, pady=3,
            justify=tk.LEFT,
        )
        label.pack()

    def _hide(self) -> None:
        if self._toplevel is not None:
            self._toplevel.destroy()
            self._toplevel = None

    def update_text(self, text: str) -> None:
        """Change the tooltip text."""
        self.text = text


def attach_tooltip(widget: tk.Widget, text: str, delay: int = 500) -> Tooltip:
    """Convenience function to add a tooltip to a widget."""
    return Tooltip(widget, text, delay)
