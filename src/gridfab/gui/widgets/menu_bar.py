"""Menu bar factory for GridFab GUI."""

import tkinter as tk

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
    file_menu.add_command(label="Save", accelerator="Ctrl+S",
                          command=callbacks.get("save"))
    file_menu.add_command(label="Open...", accelerator="Ctrl+O",
                          command=callbacks.get("open"))
    file_menu.add_command(label="Refresh",
                          command=callbacks.get("refresh"))
    file_menu.add_separator()
    file_menu.add_command(label="Render", accelerator="R",
                          command=callbacks.get("render"))
    file_menu.add_command(label="Export", accelerator="E",
                          command=callbacks.get("export"))
    file_menu.add_separator()
    file_menu.add_command(label="Import...",
                          command=callbacks.get("import_image"))
    file_menu.add_command(label="New Sprite...",
                          command=callbacks.get("new"))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=callbacks.get("exit"))
    menubar.add_cascade(label="File", menu=file_menu)

    # ── Edit ─────────────────────────────────────────────────────────
    edit_menu = _styled_menu(menubar)
    edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                          command=callbacks.get("undo"))
    edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                          command=callbacks.get("redo"))
    edit_menu.add_separator()
    edit_menu.add_command(label="Clear Grid",
                          command=callbacks.get("clear"))
    edit_menu.add_separator()
    edit_menu.add_command(label="Flip Horizontal", accelerator="H",
                          command=callbacks.get("flip_h"))
    edit_menu.add_command(label="Flip Vertical", accelerator="V",
                          command=callbacks.get("flip_v"))
    menubar.add_cascade(label="Edit", menu=edit_menu)

    # ── View ─────────────────────────────────────────────────────────
    view_menu = _styled_menu(menubar)
    view_menu.add_command(label="Grid Lines", accelerator="G",
                          command=callbacks.get("toggle_grid"))
    view_menu.add_command(label="Zoom In", accelerator="]",
                          command=callbacks.get("zoom_in"))
    view_menu.add_command(label="Zoom Out", accelerator="[",
                          command=callbacks.get("zoom_out"))
    view_menu.add_separator()
    view_menu.add_command(label="Side-by-Side", accelerator="M",
                          command=callbacks.get("side_by_side"))
    view_menu.add_command(label="Onion Skin", accelerator="O",
                          command=callbacks.get("onion_skin"))
    menubar.add_cascade(label="View", menu=view_menu)

    # ── Animation ────────────────────────────────────────────────────
    anim_menu = _styled_menu(menubar)
    anim_menu.add_command(label="Add Frame",
                          command=callbacks.get("add_frame"))
    anim_menu.add_command(label="Duplicate",
                          command=callbacks.get("duplicate_frame"))
    anim_menu.add_command(label="Delete",
                          command=callbacks.get("delete_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label="Copy", accelerator="Ctrl+C",
                          command=callbacks.get("copy_frame"))
    anim_menu.add_command(label="Paste", accelerator="Ctrl+V",
                          command=callbacks.get("paste_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label="Play / Stop", accelerator="Space",
                          command=callbacks.get("play_stop"))
    anim_menu.add_command(label="Previous Frame", accelerator="<",
                          command=callbacks.get("prev_frame"))
    anim_menu.add_command(label="Next Frame", accelerator=">",
                          command=callbacks.get("next_frame"))
    anim_menu.add_separator()
    anim_menu.add_command(label="New Animation...",
                          command=callbacks.get("new_anim"))
    menubar.add_cascade(label="Animation", menu=anim_menu)

    # ── Help ─────────────────────────────────────────────────────────
    help_menu = _styled_menu(menubar)
    help_menu.add_command(label="Keyboard Shortcuts",
                          command=callbacks.get("show_shortcuts"))
    help_menu.add_command(label="About GridFab",
                          command=callbacks.get("about"))
    menubar.add_cascade(label="Help", menu=help_menu)

    root.config(menu=menubar)
    return menubar
