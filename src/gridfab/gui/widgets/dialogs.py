"""Dark-themed dialog replacements for tkinter simpledialog/messagebox."""

import tkinter as tk

try:
    import customtkinter as ctk
    _Toplevel = ctk.CTkToplevel
    _Label = ctk.CTkLabel
    _Button = ctk.CTkButton
    _Entry = ctk.CTkEntry
    _Frame = ctk.CTkFrame
except ImportError:
    _Toplevel = tk.Toplevel
    _Label = tk.Label
    _Button = tk.Button
    _Entry = tk.Entry
    _Frame = tk.Frame

from gridfab.gui.i18n import _
from gridfab.gui.tokens import (
    BG_ELEVATED, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT, ACCENT_HOVER,
    HOVER_BUTTON, BORDER, BG_WIDGET, FONT_BODY, FONT_SMALL,
)


class _DarkDialog(_Toplevel):
    """Base class for dark-themed modal dialogs."""

    def __init__(self, parent, title: str, width: int = 300):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._result = None
        self._parent = parent
        self._width = width

    def _finalize(self):
        """Call after subclass adds all widgets to size and show the dialog."""
        self.update_idletasks()
        w = self._width
        h = self.winfo_reqheight()
        if h < 40:
            h = 150  # fallback
        px = self._parent.winfo_rootx() + self._parent.winfo_width() // 2 - w // 2
        py = self._parent.winfo_rooty() + self._parent.winfo_height() // 3
        self.geometry(f"{w}x{h}+{px}+{py}")
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()

    def _on_cancel(self):
        self.grab_release()
        self.destroy()

    def _on_ok(self):
        self.grab_release()
        self.destroy()

    def wait(self):
        self.wait_window()
        return self._result


class DarkInputDialog(_DarkDialog):
    """Dark-themed replacement for simpledialog.askstring."""

    def __init__(self, parent, title: str, prompt: str):
        super().__init__(parent, title)

        _Label(
            self, text=prompt, font=FONT_BODY,
            text_color=TEXT_PRIMARY, wraplength=300,
            anchor="w", justify="left",
        ).pack(fill="x", padx=16, pady=(10, 4))

        self._entry = _Entry(
            self, font=FONT_BODY, width=280,
            fg_color=BG_WIDGET, text_color=TEXT_PRIMARY,
            border_color=BORDER,
        )
        self._entry.pack(fill="x", padx=16, pady=(0, 8))
        self._entry.bind("<Return>", lambda e: self._on_ok())
        self._entry.bind("<Escape>", lambda e: self._on_cancel())

        btn_frame = _Frame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 10))

        _Button(
            btn_frame, text=_("OK"), width=100, height=28, font=FONT_BODY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", command=self._on_ok,
        ).pack(side="left", expand=True, padx=(0, 4))

        _Button(
            btn_frame, text=_("Cancel"), width=100, height=28, font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, command=self._on_cancel,
        ).pack(side="left", expand=True, padx=(4, 0))

        self._finalize()
        self.after(150, lambda: self._entry.focus())

    def _on_ok(self):
        self._result = self._entry.get()
        super()._on_ok()


class DarkMessageDialog(_DarkDialog):
    """Dark-themed replacement for messagebox.showinfo/showerror/showwarning."""

    def __init__(self, parent, title: str, message: str,
                 kind: str = "info", buttons: str = "ok"):
        """
        kind: "info", "warning", "error"
        buttons: "ok", "yesno", "yesnocancel", "okcancel"
        """
        super().__init__(parent, title, width=340)

        # Icon-like color indicator
        icon_colors = {"info": ACCENT, "warning": "#CCA700", "error": "#F44747"}
        icon_color = icon_colors.get(kind, ACCENT)

        header = _Frame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(10, 0))

        # Color dot as icon substitute
        dot = _Frame(header, width=8, height=8, fg_color=icon_color,
                     corner_radius=4)
        dot.pack(side="left", padx=(0, 6), pady=3)

        _Label(
            header, text=title, font=FONT_BODY,
            text_color=icon_color, anchor="w",
        ).pack(side="left")

        _Label(
            self, text=message, font=FONT_BODY,
            text_color=TEXT_PRIMARY, wraplength=340,
            anchor="w", justify="left",
        ).pack(fill="x", padx=16, pady=(4, 8))

        btn_frame = _Frame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 10))

        if buttons == "ok":
            _Button(
                btn_frame, text=_("OK"), width=100, height=28, font=FONT_BODY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="#FFFFFF", command=lambda: self._respond(True),
            ).pack(side="right")
        elif buttons == "yesno":
            _Button(
                btn_frame, text=_("No"), width=80, height=28, font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, command=lambda: self._respond(False),
            ).pack(side="right", padx=(4, 0))
            _Button(
                btn_frame, text=_("Yes"), width=80, height=28, font=FONT_BODY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="#FFFFFF", command=lambda: self._respond(True),
            ).pack(side="right")
        elif buttons == "yesnocancel":
            _Button(
                btn_frame, text=_("Cancel"), width=80, height=28, font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, command=lambda: self._respond(None),
            ).pack(side="right", padx=(4, 0))
            _Button(
                btn_frame, text=_("No"), width=80, height=28, font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, command=lambda: self._respond(False),
            ).pack(side="right", padx=(4, 0))
            _Button(
                btn_frame, text=_("Yes"), width=80, height=28, font=FONT_BODY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="#FFFFFF", command=lambda: self._respond(True),
            ).pack(side="right")
        elif buttons == "okcancel":
            _Button(
                btn_frame, text=_("Cancel"), width=80, height=28, font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, command=lambda: self._respond(False),
            ).pack(side="right", padx=(4, 0))
            _Button(
                btn_frame, text=_("OK"), width=80, height=28, font=FONT_BODY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="#FFFFFF", command=lambda: self._respond(True),
            ).pack(side="right")

        self.bind("<Return>", lambda e: self._respond(True))
        self.bind("<Escape>", lambda e: self._on_cancel())

        self._finalize()

    def _respond(self, value):
        self._result = value
        self.grab_release()
        self.destroy()


# ── Convenience functions matching tkinter messagebox/simpledialog API ──

def ask_string(parent, title: str, prompt: str) -> str | None:
    """Dark-themed replacement for simpledialog.askstring."""
    dlg = DarkInputDialog(parent, title, prompt)
    return dlg.wait()


def show_info(parent, title: str, message: str) -> None:
    """Dark-themed replacement for messagebox.showinfo."""
    DarkMessageDialog(parent, title, message, kind="info", buttons="ok").wait()


def show_warning(parent, title: str, message: str) -> None:
    """Dark-themed replacement for messagebox.showwarning."""
    DarkMessageDialog(parent, title, message, kind="warning", buttons="ok").wait()


def show_error(parent, title: str, message: str) -> None:
    """Dark-themed replacement for messagebox.showerror."""
    DarkMessageDialog(parent, title, message, kind="error", buttons="ok").wait()


def ask_yes_no(parent, title: str, message: str) -> bool:
    """Dark-themed replacement for messagebox.askyesno. Returns True/False."""
    return DarkMessageDialog(
        parent, title, message, kind="info", buttons="yesno",
    ).wait() is True


def ask_yes_no_cancel(parent, title: str, message: str) -> bool | None:
    """Dark-themed replacement for messagebox.askyesnocancel.
    Returns True (Yes), False (No), or None (Cancel)."""
    return DarkMessageDialog(
        parent, title, message, kind="warning", buttons="yesnocancel",
    ).wait()


def ask_ok_cancel(parent, title: str, message: str) -> bool:
    """Dark-themed replacement for messagebox.askokcancel. Returns True/False."""
    return DarkMessageDialog(
        parent, title, message, kind="info", buttons="okcancel",
    ).wait() is True
