"""Menu bar factory for GridFab GUI."""

import tkinter as tk

from gridfab.gui.i18n import _
from gridfab.gui.tokens import (
    MENU_BG, MENU_FG, MENU_ACTIVE_BG, MENU_ACTIVE_FG, MENU_DISABLED_FG,
)


def _styled_menu(parent) -> tk.Menu:
    """Create a dark-styled tearoff-free menu."""
    return tk.Menu(
        parent, tearoff=0,
        bg=MENU_BG, fg=MENU_FG,
        activebackground=MENU_ACTIVE_BG, activeforeground=MENU_ACTIVE_FG,
        disabledforeground=MENU_DISABLED_FG,
    )


def create_menu_bar(root, callbacks: dict) -> tk.Menu:
    """Build and configure the full menu bar.

    callbacks dict keys:
        save, open, refresh, render, export, import_image, new, exit,
        undo, redo, clear, flip_h, flip_v,
        toggle_grid, zoom_in, zoom_out, side_by_side, onion_skin,
        add_frame, duplicate_frame, delete_frame, copy_frame, paste_frame,
        play_stop, prev_frame, next_frame, new_anim,
        show_shortcuts, about
    """
    menubar = tk.Menu(root, bg=MENU_BG, fg=MENU_FG)

    # ── File ─────────────────────────────────────────────────────────
    file_menu = _styled_menu(menubar)
    file_menu.add_command(label=_("Save"), accelerator="Ctrl+S",
                          command=callbacks.get("save"))
    file_menu.add_command(label=_("Open..."), accelerator="Ctrl+O",
                          command=callbacks.get("open"))
    file_menu.add_command(label=_("Refresh"),
                          command=callbacks.get("refresh"))
    file_menu.add_separator()
    file_menu.add_command(label=_("Render"), accelerator="R",
                          command=callbacks.get("render"))
    file_menu.add_command(label=_("Export"), accelerator="E",
                          command=callbacks.get("export"))
    file_menu.add_separator()
    file_menu.add_command(label=_("Import..."),
                          command=callbacks.get("import_image"))
    file_menu.add_command(label=_("New Sprite..."),
                          command=callbacks.get("new"))
    file_menu.add_separator()
    file_menu.add_command(label=_("Exit"), command=callbacks.get("exit"))
    menubar.add_cascade(label=_("File"), menu=file_menu)

    # ── Edit ─────────────────────────────────────────────────────────
    edit_menu = _styled_menu(menubar)
    edit_menu.add_command(label=_("Undo"), accelerator="Ctrl+Z",
                          command=callbacks.get("undo"))
    edit_menu.add_command(label=_("Redo"), accelerator="Ctrl+Y",
                          command=callbacks.get("redo"))
    edit_menu.add_separator()
    edit_menu.add_command(label=_("Clear Grid"),
                          command=callbacks.get("clear"))
    edit_menu.add_separator()
    edit_menu.add_command(label=_("Flip Horizontal"), accelerator="H",
                          command=callbacks.get("flip_h"))
    edit_menu.add_command(label=_("Flip Vertical"), accelerator="V",
                          command=callbacks.get("flip_v"))
    menubar.add_cascade(label=_("Edit"), menu=edit_menu)

    # ── View ─────────────────────────────────────────────────────────
    view_menu = _styled_menu(menubar)
    view_menu.add_command(label=_("Grid Lines"), accelerator="G",
                          command=callbacks.get("toggle_grid"))
    view_menu.add_command(label=_("Zoom In"), accelerator="]",
                          command=callbacks.get("zoom_in"))
    view_menu.add_command(label=_("Zoom Out"), accelerator="[",
                          command=callbacks.get("zoom_out"))
    view_menu.add_separator()
    view_menu.add_command(label=_("Side-by-Side"), accelerator="M",
                          command=callbacks.get("side_by_side"))
    view_menu.add_command(label=_("Onion Skin"), accelerator="O",
                          command=callbacks.get("onion_skin"))
    menubar.add_cascade(label=_("View"), menu=view_menu)

    # ── Animation ────────────────────────────────────────────────────
    anim_menu = _styled_menu(menubar)
    anim_menu.add_command(label=_("Add Frame"),
                          command=callbacks.get("add_frame"))
    anim_menu.add_command(label=_("Duplicate"),
                          command=callbacks.get("duplicate_frame"))
    anim_menu.add_command(label=_("Delete"),
                          command=callbacks.get("delete_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label=_("Copy"), accelerator="Ctrl+C",
                          command=callbacks.get("copy_frame"))
    anim_menu.add_command(label=_("Paste"), accelerator="Ctrl+V",
                          command=callbacks.get("paste_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label=_("Play / Stop"), accelerator="Space",
                          command=callbacks.get("play_stop"))
    anim_menu.add_command(label=_("Previous Frame"), accelerator="<",
                          command=callbacks.get("prev_frame"))
    anim_menu.add_command(label=_("Next Frame"), accelerator=">",
                          command=callbacks.get("next_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label=_("New Animation..."),
                          command=callbacks.get("new_anim"))
    menubar.add_cascade(label=_("Animation"), menu=anim_menu)

    # ── Help ─────────────────────────────────────────────────────────
    help_menu = _styled_menu(menubar)
    help_menu.add_command(label=_("Keyboard Shortcuts"),
                          command=callbacks.get("show_shortcuts"))
    help_menu.add_command(label=_("About GridFab"),
                          command=callbacks.get("about"))
    menubar.add_cascade(label=_("Help"), menu=help_menu)

    root.config(menu=menubar)
    return menubar
