"""Frame strip for GridFab GUI — animation frame navigation and controls."""

import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
    _Frame = ctk.CTkFrame
    _Button = ctk.CTkButton
except ImportError:
    _Frame = tk.Frame
    _Button = tk.Button

from gridfab.gui.tokens import (
    BG_ELEVATED, BORDER, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY,
    HOVER_BUTTON, SELECTED_UNFOCUS, FRAME_STRIP_HEIGHT,
    PAD_SM, FONT_BODY, FONT_SMALL,
)


class FrameStrip(_Frame):
    """Bottom strip with animation frame controls and navigation buttons."""

    def __init__(self, master, callbacks: dict, **kwargs):
        """Create the frame strip.

        callbacks dict keys:
            add_frame, duplicate, delete, copy, paste,
            move_left, move_right, toggle_playback,
            on_fps_change(fps), on_anim_select(name),
            switch_frame(num), toggle_frame_selection(num),
            range_select_frames(num), on_anim_dir_select(name),
            add_base_ref
        """
        super().__init__(
            master, height=FRAME_STRIP_HEIGHT, fg_color=BG_ELEVATED,
            corner_radius=0, **kwargs,
        )
        self._callbacks = callbacks
        self._widgets: list[tk.Widget] = []
        self._fps_var = tk.IntVar(value=8)

    @property
    def fps_var(self) -> tk.IntVar:
        return self._fps_var

    def rebuild(
        self,
        frames: list[int],
        active_frame: int | None,
        selected_frames: set[int],
        playing: bool,
        fps: int,
        anim_dir_choices: list[str],
        current_anim_dir: str,
        is_anim_subdir: bool,
        anim_names: list[str],
        play_anim_name: str | None,
    ) -> None:
        """Rebuild the entire frame strip contents."""
        for w in self._widgets:
            w.destroy()
        self._widgets.clear()
        self._fps_var.set(fps)
        cb = self._callbacks

        # ── Control buttons ──────────────────────────────────────────
        for text, key, width in [
            ("+", "add_frame", 36),
            ("Dup", "duplicate", 50),
            ("Del", "delete", 50),
            ("Cp", "copy", 36),
            ("Ps", "paste", 36),
            ("\u25C0", "move_left", 30),
            ("\u25B6", "move_right", 30),
        ]:
            btn = _Button(
                self, text=text, width=width, height=26,
                font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, corner_radius=4,
                command=cb.get(key, lambda: None),
            )
            btn.pack(side=tk.LEFT, padx=1)
            self._widgets.append(btn)

        # Separator
        sep = tk.Frame(self, width=4, bg=BG_ELEVATED)
        sep.pack(side=tk.LEFT)
        self._widgets.append(sep)

        # ── Play/Stop ────────────────────────────────────────────────
        play_text = "Stop" if playing else "Play"
        btn_play = _Button(
            self, text=play_text, width=60, height=26,
            font=FONT_BODY,
            fg_color="transparent", hover_color=HOVER_BUTTON,
            text_color=TEXT_PRIMARY, corner_radius=4,
            command=cb.get("toggle_playback", lambda: None),
        )
        btn_play.pack(side=tk.LEFT, padx=2)
        self._widgets.append(btn_play)

        # ── FPS spinner ──────────────────────────────────────────────
        fps_label = tk.Label(self, text="FPS:", bg=BG_ELEVATED, fg=TEXT_SECONDARY, font=FONT_SMALL)
        fps_label.pack(side=tk.LEFT, padx=(4, 0))
        self._widgets.append(fps_label)

        fps_spin = ttk.Spinbox(
            self, from_=1, to=60, width=3,
            textvariable=self._fps_var,
            command=lambda: self._on_fps(),
        )
        fps_spin.pack(side=tk.LEFT, padx=2)
        self._widgets.append(fps_spin)

        # ── Animation directory selector ─────────────────────────────
        if len(anim_dir_choices) > 1:
            dir_var = tk.StringVar(value=current_anim_dir)
            dir_menu = tk.OptionMenu(
                self, dir_var, *anim_dir_choices,
                command=lambda v: self._on_dir(v),
            )
            dir_menu.config(width=10, bg=BG_ELEVATED, fg=TEXT_PRIMARY,
                            highlightthickness=0)
            dir_menu.pack(side=tk.LEFT, padx=2)
            self._widgets.append(dir_menu)

        # ── +Base ref button ─────────────────────────────────────────
        if is_anim_subdir:
            btn_base = _Button(
                self, text="+Base", width=60, height=26,
                font=FONT_BODY,
                fg_color="transparent", hover_color=HOVER_BUTTON,
                text_color="#FFE0B2", corner_radius=4,
                command=cb.get("add_base_ref", lambda: None),
            )
            btn_base.pack(side=tk.LEFT, padx=2)
            self._widgets.append(btn_base)

        # ── Playback animation selector ──────────────────────────────
        anim_var = tk.StringVar(value=play_anim_name or "(All Frames)")
        anim_menu = tk.OptionMenu(
            self, anim_var, *anim_names,
            command=lambda v: self._on_anim(v),
        )
        anim_menu.config(width=10, bg=BG_ELEVATED, fg=TEXT_PRIMARY,
                         highlightthickness=0)
        anim_menu.pack(side=tk.LEFT, padx=2)
        self._widgets.append(anim_menu)

        # Separator
        sep2 = tk.Frame(self, width=4, bg=BG_ELEVATED)
        sep2.pack(side=tk.LEFT)
        self._widgets.append(sep2)

        # ── Frame number buttons ─────────────────────────────────────
        for f in frames:
            is_active = f == active_frame
            is_selected = f in selected_frames

            if is_active:
                fg = ACCENT
            elif is_selected:
                fg = SELECTED_UNFOCUS
            else:
                fg = "transparent"

            btn = _Button(
                self, text=str(f), width=40, height=26,
                font=FONT_BODY,
                fg_color=fg, hover_color=HOVER_BUTTON,
                text_color=TEXT_PRIMARY, corner_radius=4,
                command=lambda num=f: self._on_frame(num),
            )
            btn.bind("<Control-Button-1>", lambda e, num=f: self._on_ctrl_frame(num))
            btn.bind("<Shift-Button-1>", lambda e, num=f: self._on_shift_frame(num))
            btn.pack(side=tk.LEFT, padx=1, pady=2)
            self._widgets.append(btn)

    def _on_fps(self) -> None:
        cb = self._callbacks.get("on_fps_change")
        if cb:
            try:
                cb(self._fps_var.get())
            except (tk.TclError, ValueError):
                pass

    def _on_dir(self, value: str) -> None:
        cb = self._callbacks.get("on_anim_dir_select")
        if cb:
            cb(value)

    def _on_anim(self, value: str) -> None:
        cb = self._callbacks.get("on_anim_select")
        if cb:
            cb(value)

    def _on_frame(self, num: int) -> None:
        cb = self._callbacks.get("switch_frame")
        if cb:
            cb(num)

    def _on_ctrl_frame(self, num: int) -> str:
        cb = self._callbacks.get("toggle_frame_selection")
        if cb:
            cb(num)
        return "break"

    def _on_shift_frame(self, num: int) -> str:
        cb = self._callbacks.get("range_select_frames")
        if cb:
            cb(num)
        return "break"
