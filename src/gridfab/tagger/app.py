"""Main GUI application for the tileset tagger."""

import json
import sys
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw

from gridfab.tagger.tags import TagManager
from gridfab.tagger.navigator import TilesetNavigator
from gridfab.tagger.ai import AIAssistant


class TaggerApp:
    """Interactive tileset tagger with keyboard-driven workflow."""

    ZOOM = 8  # Zoom factor for current tile display
    CONTEXT_ZOOM = 2  # Zoom factor for context view
    CONTEXT_RADIUS = 3  # Tiles of context around selection

    def __init__(self, tileset_path: str, tile_size: int = 32,
                 output_path: str | None = None, model: str = "haiku",
                 bg_color: tuple | None = None, import_path: str | None = None):
        self.tileset_path = Path(tileset_path).resolve()
        self.tile_size = tile_size

        # Output path: default to <tileset_stem>_index.json next to tileset
        if output_path:
            self.output_path = Path(output_path).resolve()
        else:
            self.output_path = self.tileset_path.parent / f"{self.tileset_path.stem}_index.json"

        # Tag config lives next to the output
        tag_config_path = self.output_path.parent / "tagger_tags.json"
        self.tag_mgr = TagManager(tag_config_path)

        # Load tileset
        self.nav = TilesetNavigator(self.tileset_path, tile_size, bg_color=bg_color)
        # Merge persisted empty tiles from previous sessions
        persisted_empties = self.tag_mgr.load_empty_tiles()
        if persisted_empties:
            self.nav.empty_tiles |= persisted_empties

        print(f"Loaded: {self.nav.cols}x{self.nav.rows} tiles, "
              f"{self.nav.non_empty_count()} non-empty, "
              f"{len(self.nav.empty_tiles)} empty"
              f"{f' ({len(persisted_empties)} from config)' if persisted_empties else ''}")

        # AI assistant
        self.ai = AIAssistant(model)
        if self.ai.available:
            print(f"AI: Claude Code available (model: {model})")
        else:
            print("AI: Claude Code not found — AI features disabled (tagging still works)")
            print("    Install: https://docs.anthropic.com/en/docs/claude-code")
            print("    Authenticate: run 'claude' and follow prompts, or set ANTHROPIC_API_KEY")
            print("    Check status: claude /status")

        # Session state
        self.sprites: dict[str, dict] = {}  # name -> sprite data
        self.covered_tiles: set[tuple[int, int]] = set()  # tiles already in a sprite
        self.active_tags: set[str] = set()  # currently toggled tag keys
        self.sel_tiles_x = 1  # multi-tile selection width
        self.sel_tiles_y = 1  # multi-tile selection height
        self.current_name = ""
        self.current_desc = ""
        self.ai_generating = False  # True while AI call is in flight
        self._type_auto_filled = False  # Track whether type field was auto-filled

        # Import mode: tiles to review with pre-populated names
        # Maps (row, col) -> {"name": ..., "tiles_x": ..., "tiles_y": ..., ...}
        self.import_data: dict[tuple[int, int], dict] = {}
        self.import_names: set[str] = set()  # track import names for dedup on save

        # Rolling context: last N saved sprites for AI prompt context
        self.recent_saves: list[dict] = []
        self.RECENT_SAVES_MAX = 8

        # Build ordered list of tiles to visit (skip empty)
        self.tile_order = [
            (r, c)
            for r in range(self.nav.rows)
            for c in range(self.nav.cols)
            if (r, c) not in self.nav.empty_tiles
        ]
        self.current_idx = 0

        # Load existing output index for resume (marks tiles as done)
        self._load_existing_index()

        # Import external index for review (marks tiles as needing review)
        if import_path:
            self._import_index(Path(import_path).resolve())

        # Skip to first unvisited tile
        self._advance_to_next_unvisited(from_current=True)

        # Build GUI
        self._build_gui()

    # ── Index Persistence ──────────────────────────────────────────────────

    def _is_sprite_complete(self, sprite: dict) -> bool:
        """Check if a sprite has all required fields filled in."""
        return (bool(sprite.get("description"))
                and bool(sprite.get("tags"))
                and bool(sprite.get("tile_type")))

    def _load_existing_index(self):
        """Resume from existing index.json if present.

        Complete sprites (with description + tags + tile_type) are marked done.
        Incomplete sprites are kept in self.sprites (so they persist on save)
        but also queued into import_data for review, and NOT marked as covered
        so the navigator will visit them.
        """
        if not self.output_path.exists():
            return
        try:
            data = json.loads(self.output_path.read_text())
            complete = 0
            incomplete = 0
            for name, sprite in data.get("sprites", {}).items():
                self.sprites[name] = sprite  # Always keep in sprites for persistence
                if self._is_sprite_complete(sprite):
                    # Fully done — mark as covered (skip during navigation)
                    for dr in range(sprite.get("tiles_y", 1)):
                        for dc in range(sprite.get("tiles_x", 1)):
                            self.covered_tiles.add((sprite["row"] + dr, sprite["col"] + dc))
                    complete += 1
                else:
                    # Incomplete — queue for review (don't mark covered)
                    pos = (sprite["row"], sprite["col"])
                    self.import_data[pos] = {
                        "name": name,
                        "tiles_x": sprite.get("tiles_x", 1),
                        "tiles_y": sprite.get("tiles_y", 1),
                        "description": sprite.get("description", ""),
                        "tile_type": sprite.get("tile_type", ""),
                        "tags": sprite.get("tags", []),
                    }
                    self.import_names.add(name)
                    incomplete += 1
            if complete or incomplete:
                print(f"Resumed: {complete} complete, {incomplete} need review "
                      f"(from {self.output_path.name})")
                # Seed recent context for AI from last completed sprites
                # Sort by position so the context is spatially coherent
                completed = [
                    (name, s) for name, s in self.sprites.items()
                    if self._is_sprite_complete(s)
                ]
                completed.sort(key=lambda x: (x[1]["row"], x[1]["col"]))
                for name, s in completed[-self.RECENT_SAVES_MAX:]:
                    self.recent_saves.append({
                        "name": name,
                        "row": s["row"],
                        "col": s["col"],
                        "tags": s.get("tags", []),
                        "description": s.get("description", ""),
                    })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load existing index: {e}")

    def _import_index(self, import_path: Path):
        """Import an existing index for review/enrichment.

        Complete sprites already in the output index are skipped.
        Complete sprites NOT in the output are added directly as done.
        Incomplete sprites are queued for review with pre-populated data.
        """
        if not import_path.exists():
            print(f"Warning: Import file not found: {import_path}")
            return
        try:
            data = json.loads(import_path.read_text())
            added = 0
            queued = 0
            skipped = 0
            for name, sprite in data.get("sprites", {}).items():
                pos = (sprite["row"], sprite["col"])
                # Skip tiles already fully done in the output index
                if pos in self.covered_tiles:
                    skipped += 1
                    continue
                # Already queued for review from output index load
                if pos in self.import_data:
                    # Merge: prefer whichever has more data
                    existing = self.import_data[pos]
                    if not existing.get("description") and sprite.get("description"):
                        existing["description"] = sprite["description"]
                    if not existing.get("tile_type") and sprite.get("tile_type"):
                        existing["tile_type"] = sprite["tile_type"]
                    if not existing.get("tags") and sprite.get("tags"):
                        existing["tags"] = sprite["tags"]
                    continue
                if self._is_sprite_complete(sprite):
                    # Complete import — add directly as done
                    self.sprites[name] = sprite
                    for dr in range(sprite.get("tiles_y", 1)):
                        for dc in range(sprite.get("tiles_x", 1)):
                            self.covered_tiles.add((sprite["row"] + dr, sprite["col"] + dc))
                    added += 1
                else:
                    # Incomplete — keep in sprites for persistence, queue for review
                    self.sprites[name] = sprite
                    self.import_data[pos] = {
                        "name": name,
                        "tiles_x": sprite.get("tiles_x", 1),
                        "tiles_y": sprite.get("tiles_y", 1),
                        "description": sprite.get("description", ""),
                        "tile_type": sprite.get("tile_type", ""),
                        "tags": sprite.get("tags", []),
                    }
                    self.import_names.add(name)
                    queued += 1
            print(f"Imported: {added} complete, {queued} for review, "
                  f"{skipped} already done (from {import_path.name})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not import index: {e}")

    def _save_index(self):
        """Write current state to index.json in GridFab atlas format."""
        index = {
            "tile_size": [self.tile_size, self.tile_size],
            "columns": self.nav.cols,
            "sprites": self.sprites,
        }
        self.output_path.write_text(json.dumps(index, indent=2))

    # ── Navigation ─────────────────────────────────────────────────────────

    def _current_tile(self) -> tuple[int, int] | None:
        if 0 <= self.current_idx < len(self.tile_order):
            return self.tile_order[self.current_idx]
        return None

    def _advance_to_next_unvisited(self, from_current=False):
        """Move current_idx to the next tile not in covered_tiles."""
        start = self.current_idx if from_current else self.current_idx + 1
        for i in range(start, len(self.tile_order)):
            if self.tile_order[i] not in self.covered_tiles:
                self.current_idx = i
                return True
        # Wrapped or done
        self.current_idx = len(self.tile_order)
        return False

    def _go_previous(self):
        """Move back to the previous tile (including completed ones)."""
        for i in range(self.current_idx - 1, -1, -1):
            self.current_idx = i
            return True
        return False

    def _sprite_at(self, row: int, col: int) -> tuple[str, dict] | None:
        """Find the sprite covering a given tile position."""
        for name, sprite in self.sprites.items():
            sr, sc = sprite["row"], sprite["col"]
            tx, ty = sprite.get("tiles_x", 1), sprite.get("tiles_y", 1)
            if sr <= row < sr + ty and sc <= col < sc + tx:
                return name, sprite
        return None

    def _count_remaining(self) -> int:
        return sum(1 for r, c in self.tile_order[self.current_idx:]
                   if (r, c) not in self.covered_tiles)

    def _count_done(self) -> int:
        return len(self.sprites)

    # ── GUI Construction ───────────────────────────────────────────────────

    def _build_gui(self):
        self.root = tk.Tk()
        self.root.title(f"Tileset Tagger — {self.tileset_path.name}")
        self.root.configure(bg="#2b2b2b")
        self.root.resizable(True, True)

        # Prevent Tk from processing Tab for widget traversal
        self.root.unbind_all("<<NextWindow>>")
        self.root.unbind_all("<<PrevWindow>>")

        # ── Top: tile displays ──
        top_frame = tk.Frame(self.root, bg="#2b2b2b")
        top_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        # Current tile (zoomed)
        tile_frame = tk.LabelFrame(top_frame, text="Current Tile", fg="#aaa",
                                   bg="#2b2b2b", font=("monospace", 10))
        tile_frame.pack(side=tk.LEFT, padx=(0, 8))
        self.tile_canvas = tk.Canvas(tile_frame, width=256, height=256,
                                     bg="#1a1a1a", highlightthickness=0)
        self.tile_canvas.pack(padx=4, pady=4)

        # Context view
        ctx_frame = tk.LabelFrame(top_frame, text="Context", fg="#aaa",
                                  bg="#2b2b2b", font=("monospace", 10))
        ctx_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ctx_canvas = tk.Canvas(ctx_frame, width=320, height=320,
                                    bg="#1a1a1a", highlightthickness=0)
        self.ctx_canvas.pack(padx=4, pady=4)

        # ── Info bar ──
        self.info_var = tk.StringVar(value="")
        info_label = tk.Label(self.root, textvariable=self.info_var, fg="#ccc",
                              bg="#333", font=("monospace", 10), anchor="w", padx=8)
        info_label.pack(fill=tk.X, padx=8, pady=2)

        # ── Tags panel ──
        tag_outer = tk.LabelFrame(self.root, text="Tags (press key to toggle)",
                                  fg="#aaa", bg="#2b2b2b", font=("monospace", 10))
        tag_outer.pack(fill=tk.X, padx=8, pady=2)

        self.tag_frame = tk.Frame(tag_outer, bg="#2b2b2b")
        self.tag_frame.pack(fill=tk.X, padx=4, pady=4)
        self.tag_labels: dict[str, tk.Label] = {}
        self._rebuild_tag_display()

        # Active tags display
        self.active_var = tk.StringVar(value="Active: (none)")
        active_label = tk.Label(tag_outer, textvariable=self.active_var, fg="#4fc3f7",
                                bg="#2b2b2b", font=("monospace", 10, "bold"),
                                anchor="w", padx=4)
        active_label.pack(fill=tk.X, padx=4, pady=(0, 4))

        # ── Name, Type & Description fields ──
        fields_frame = tk.Frame(self.root, bg="#2b2b2b")
        fields_frame.pack(fill=tk.X, padx=8, pady=2)

        entry_style = dict(font=("monospace", 11), bg="#1a1a1a", fg="#fff",
                           insertbackground="#fff", relief="flat", highlightthickness=1,
                           highlightcolor="#4fc3f7", highlightbackground="#555")

        tk.Label(fields_frame, text="Name:", fg="#aaa", bg="#2b2b2b",
                 font=("monospace", 10)).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.name_entry = tk.Entry(fields_frame, **entry_style)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        tk.Label(fields_frame, text="Type:", fg="#aaa", bg="#2b2b2b",
                 font=("monospace", 10)).grid(row=1, column=0, sticky="w", padx=(0, 4))
        self.type_entry = tk.Entry(fields_frame, **entry_style)
        self.type_entry.grid(row=1, column=1, sticky="ew", pady=2)

        tk.Label(fields_frame, text="Desc:", fg="#aaa", bg="#2b2b2b",
                 font=("monospace", 10)).grid(row=2, column=0, sticky="w", padx=(0, 4))
        self.desc_entry = tk.Entry(fields_frame, **entry_style)
        self.desc_entry.grid(row=2, column=1, sticky="ew", pady=2)

        fields_frame.columnconfigure(1, weight=1)

        # ── Status / help bar ──
        self.status_var = tk.StringVar(value="")
        status_bar = tk.Label(self.root, textvariable=self.status_var, fg="#888",
                              bg="#222", font=("monospace", 9), anchor="w", padx=8, pady=4)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # ── Key bindings ──
        self.root.bind("<Key>", self._on_key)
        self.name_entry.bind("<Return>", self._on_name_enter)
        self.name_entry.bind("<Escape>", self._on_field_escape)
        self.name_entry.bind("<Tab>", self._on_name_tab)
        self.name_entry.bind("<FocusIn>", self._on_field_focus_in)
        self.type_entry.bind("<Return>", self._on_type_enter)
        self.type_entry.bind("<Escape>", self._on_field_escape)
        self.type_entry.bind("<Tab>", self._on_type_tab)
        self.type_entry.bind("<FocusIn>", self._on_field_focus_in)
        self.desc_entry.bind("<Return>", self._on_desc_enter)
        self.desc_entry.bind("<Escape>", self._on_field_escape)
        self.desc_entry.bind("<Tab>", self._on_desc_tab)
        self.desc_entry.bind("<FocusIn>", self._on_field_focus_in)

        # Click on canvases to return to tag mode
        self.tile_canvas.bind("<Button-1>", lambda e: self._return_to_tag_mode())
        self.ctx_canvas.bind("<Button-1>", lambda e: self._return_to_tag_mode())

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

        # Initial display
        self._refresh_display()
        self._show_tag_mode_status()

        # Focus main window (not entry fields)
        self.root.focus_set()

    def _rebuild_tag_display(self):
        """Rebuild the tag shortcut grid."""
        for w in self.tag_frame.winfo_children():
            w.destroy()
        self.tag_labels.clear()

        tags = self.tag_mgr.get_sorted()
        cols_per_row = 6
        for i, (key, name) in enumerate(tags):
            r, c = divmod(i, cols_per_row)
            lbl = tk.Label(
                self.tag_frame,
                text=f"[{key}] {name}",
                font=("monospace", 9),
                fg="#888", bg="#2b2b2b",
                padx=4, pady=1, anchor="w", width=16,
            )
            lbl.grid(row=r, column=c, sticky="w", padx=2, pady=1)
            self.tag_labels[key] = lbl

    def _update_tag_highlights(self):
        """Update tag label colors based on active tags."""
        for key, lbl in self.tag_labels.items():
            if key in self.active_tags:
                lbl.configure(fg="#1a1a1a", bg="#4fc3f7", font=("monospace", 9, "bold"))
            else:
                lbl.configure(fg="#888", bg="#2b2b2b", font=("monospace", 9))

        active_names = [self.tag_mgr.tags[k] for k in sorted(self.active_tags) if k in self.tag_mgr.tags]
        if active_names:
            self.active_var.set("Active: " + ", ".join(active_names))
        else:
            self.active_var.set("Active: (none)")

        # Auto-fill type field from first alphabetic tag
        self._auto_fill_type()

    def _auto_fill_type(self):
        """Auto-populate the Type field from active alphabetic-key tags.

        Only auto-fills if the field is empty or was previously auto-filled
        (don't overwrite manual edits). Uses the single tag name if one
        alphabetic tag is active, or "multi" if more than one.
        """
        current_type = self.type_entry.get().strip()
        if current_type and not self._type_auto_filled:
            return  # User manually typed something, don't overwrite

        # Collect all alphabetic-key tags (skip numeric keys 1-5 which are materials)
        type_parts = []
        for key in sorted(self.active_tags):
            if key.isalpha() and key in self.tag_mgr.tags:
                type_parts.append(self.tag_mgr.tags[key])

        self.type_entry.delete(0, tk.END)
        if len(type_parts) == 1:
            self.type_entry.insert(0, type_parts[0])
            self._type_auto_filled = True
        elif len(type_parts) > 1:
            self.type_entry.insert(0, "multi")
            self._type_auto_filled = True
        else:
            self._type_auto_filled = False

    # ── Display Refresh ────────────────────────────────────────────────────

    def _refresh_display(self):
        """Update all visual elements for the current tile."""
        pos = self._current_tile()
        if pos is None:
            self._show_completion()
            return

        row, col = pos

        # Clamp multi-tile selection to tileset bounds
        self.sel_tiles_x = min(self.sel_tiles_x, self.nav.cols - col)
        self.sel_tiles_y = min(self.sel_tiles_y, self.nav.rows - row)

        # ── Update tile view (zoomed) ──
        tile_img = self.nav.get_tile_image(row, col, self.sel_tiles_x, self.sel_tiles_y)
        # Zoom using nearest-neighbor to preserve pixel art
        zoom_w = min(256, self.sel_tiles_x * self.tile_size * self.ZOOM)
        zoom_h = min(256, self.sel_tiles_y * self.tile_size * self.ZOOM)
        # Calculate zoom to fit the canvas (256x256)
        scale = min(256 / tile_img.width, 256 / tile_img.height)
        scale = max(1, int(scale))
        zoomed = tile_img.resize((tile_img.width * scale, tile_img.height * scale),
                                 Image.NEAREST)
        # Add checkerboard background for transparency
        checker = self._make_checkerboard(zoomed.width, zoomed.height)
        checker.paste(zoomed, (0, 0), zoomed)
        self._tile_photo = ImageTk.PhotoImage(checker)
        self.tile_canvas.config(width=checker.width, height=checker.height)
        self.tile_canvas.delete("all")
        self.tile_canvas.create_image(0, 0, anchor="nw", image=self._tile_photo)

        # ── Update context view ──
        ctx_img, _ = self.nav.get_context_image(
            row, col, self.sel_tiles_x, self.sel_tiles_y, self.CONTEXT_RADIUS
        )
        ctx_scale = max(1, min(320 // ctx_img.width, 320 // ctx_img.height, self.CONTEXT_ZOOM))
        ctx_zoomed = ctx_img.resize((ctx_img.width * ctx_scale, ctx_img.height * ctx_scale),
                                    Image.NEAREST)
        ctx_checker = self._make_checkerboard(ctx_zoomed.width, ctx_zoomed.height)
        ctx_checker.paste(ctx_zoomed, (0, 0), ctx_zoomed)
        self._ctx_photo = ImageTk.PhotoImage(ctx_checker)
        self.ctx_canvas.config(width=ctx_checker.width, height=ctx_checker.height)
        self.ctx_canvas.delete("all")
        self.ctx_canvas.create_image(0, 0, anchor="nw", image=self._ctx_photo)

        # ── Info bar ──
        remaining = self._count_remaining()
        done = self._count_done()
        total = self.nav.non_empty_count()
        pct = (done / total * 100) if total else 0
        sel_str = f"{self.sel_tiles_x}x{self.sel_tiles_y}" if (self.sel_tiles_x > 1 or self.sel_tiles_y > 1) else "1x1"

        import_str = ""
        if pos in self.import_data:
            import_remaining = len(self.import_data)
            import_str = f" [review: {import_remaining} left]"
        elif pos in self.covered_tiles:
            import_str = " [editing]"

        self.info_var.set(
            f"Row {row}, Col {col} │ Selection: {sel_str}{import_str} │ "
            f"Done: {done}/{total} ({pct:.0f}%) │ Remaining: {remaining}"
        )

        # ── Pre-populate from import data ──
        if pos in self.import_data:
            imp = self.import_data[pos]
            # Set selection size from imported sprite
            self.sel_tiles_x = imp.get("tiles_x", 1)
            self.sel_tiles_y = imp.get("tiles_y", 1)
            # Pre-populate name (user can change it)
            if not self.name_entry.get():
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, imp["name"])
            # Pre-populate type if it exists
            if not self.type_entry.get() and imp.get("tile_type"):
                self.type_entry.delete(0, tk.END)
                self.type_entry.insert(0, imp["tile_type"])
                self._type_auto_filled = False  # Loaded from data, not auto-filled
            # Pre-populate description if it exists
            if not self.desc_entry.get() and imp.get("description"):
                self.desc_entry.delete(0, tk.END)
                self.desc_entry.insert(0, imp["description"])
            # Pre-activate tags that match imported tags
            if not self.active_tags and imp.get("tags"):
                reverse_tags = {v: k for k, v in self.tag_mgr.tags.items()}
                for tag_name in imp["tags"]:
                    if tag_name in reverse_tags:
                        self.active_tags.add(reverse_tags[tag_name])
                self._update_tag_highlights()

    def _show_completion(self):
        """All tiles have been processed."""
        self.tile_canvas.delete("all")
        self.tile_canvas.create_text(128, 128, text="All done!", fill="#4fc3f7",
                                     font=("monospace", 16, "bold"))
        self.ctx_canvas.delete("all")
        self.info_var.set(f"Complete! {len(self.sprites)} sprites indexed -> {self.output_path.name}")
        self.status_var.set("All tiles processed. Press Esc to quit.")

    def _make_checkerboard(self, width: int, height: int, cell: int = 8) -> Image.Image:
        """Create a checkerboard background for transparency display."""
        img = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(img)
        c1 = (40, 40, 40, 255)
        c2 = (60, 60, 60, 255)
        for y in range(0, height, cell):
            for x in range(0, width, cell):
                color = c1 if (x // cell + y // cell) % 2 == 0 else c2
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=color)
        return img

    # ── Key Event Handling ─────────────────────────────────────────────────

    def _on_key(self, event):
        """Handle key presses in tag mode (main window focused)."""
        # Don't intercept if an entry widget has focus
        if event.widget in (self.name_entry, self.type_entry, self.desc_entry):
            return

        key = event.keysym
        char = event.char

        if key == "Escape":
            self._on_quit()
        elif key == "Tab":
            self._generate_ai()
            return "break"
        elif key == "Return":
            self._save_and_next()
        elif key == "space":
            self._skip_tile()
        elif key == "BackSpace":
            self._go_back()
        elif key == "Delete":
            self._mark_empty()
        elif key in ("plus", "equal"):
            self._add_new_tag()
        elif key == "F1":
            self._show_help()
        # Arrow keys: resize multi-tile selection
        elif key == "Right":
            self.sel_tiles_x = min(self.sel_tiles_x + 1, self.nav.cols - (self._current_tile() or (0, 0))[1])
            self._refresh_display()
        elif key == "Left":
            self.sel_tiles_x = max(1, self.sel_tiles_x - 1)
            self._refresh_display()
        elif key == "Down":
            self.sel_tiles_y = min(self.sel_tiles_y + 1, self.nav.rows - (self._current_tile() or (0, 0))[0])
            self._refresh_display()
        elif key == "Up":
            self.sel_tiles_y = max(1, self.sel_tiles_y - 1)
            self._refresh_display()
        # Tag toggle
        elif char and char in self.tag_mgr.tags:
            if char in self.active_tags:
                self.active_tags.discard(char)
            else:
                self.active_tags.add(char)
            self._update_tag_highlights()

    def _on_name_enter(self, event):
        """Enter in name field -> move to type."""
        self.type_entry.focus_set()
        return "break"

    def _on_name_tab(self, event):
        """Tab in name field -> move to type."""
        self.type_entry.focus_set()
        return "break"

    def _on_type_enter(self, event):
        """Enter in type field -> move to description."""
        self.desc_entry.focus_set()
        return "break"

    def _on_type_tab(self, event):
        """Tab in type field -> move to description."""
        self.desc_entry.focus_set()
        return "break"

    def _on_desc_enter(self, event):
        """Enter in desc field -> save and advance."""
        self.current_name = self.name_entry.get().strip()
        self.current_desc = self.desc_entry.get().strip()
        self._save_and_next()
        self.root.focus_set()
        return "break"

    def _on_desc_tab(self, event):
        """Tab in desc field -> back to main (tag mode)."""
        self.root.focus_set()
        return "break"

    def _on_field_escape(self, event):
        """Escape in any field -> return to tag mode."""
        self._return_to_tag_mode()

    def _return_to_tag_mode(self):
        """Return focus to main window for tag input."""
        self.root.focus_set()
        self._show_tag_mode_status()

    def _on_field_focus_in(self, event):
        """Update status bar when an entry field gets focus."""
        # Mark type as manually edited if user focuses and changes it
        if event.widget == self.type_entry:
            self._type_auto_filled = False
        self.status_var.set(
            "Esc/Click tile: back to tags | Tab: next field | "
            "Enter: save+next (from desc) or next field (from name/type)"
        )

    def _show_tag_mode_status(self):
        """Show the default tag-mode status bar."""
        self.status_var.set(
            "Tab:AI Generate | Enter:Save+Next | Space:Skip | "
            "Backspace:Back | arrows:Resize | +:New Tag | Del:Mark Empty | Esc:Quit"
        )

    # ── Actions ────────────────────────────────────────────────────────────

    def _generate_ai(self):
        """Call Claude Code to generate name + description from tags."""
        pos = self._current_tile()
        if pos is None:
            return

        if self.ai_generating:
            return  # Already in flight

        row, col = pos
        tag_names = sorted(self.tag_mgr.tags[k] for k in self.active_tags if k in self.tag_mgr.tags)

        if not tag_names and not self.ai.available:
            self.status_var.set("Add some tags first (no AI available for image-only analysis)")
            return

        self.status_var.set("Generating name and description...")
        self.ai_generating = True

        # Get images for AI
        tile_img = self.nav.get_tile_image(row, col, self.sel_tiles_x, self.sel_tiles_y)
        context_img, _ = self.nav.get_context_image(row, col, self.sel_tiles_x, self.sel_tiles_y)

        # Existing name/description from user (if any)
        existing_name = self.name_entry.get().strip() or None
        existing_desc = self.desc_entry.get().strip() or None

        def _run():
            result = self.ai.generate(
                tag_names, tile_img, context_img,
                row, col, self.sel_tiles_x, self.sel_tiles_y,
                recent_context=self.recent_saves,
                existing_name=existing_name,
                existing_desc=existing_desc,
            )
            self.root.after(0, lambda: self._on_ai_result(result))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _on_ai_result(self, result: dict):
        """Handle AI generation result (called on main thread)."""
        self.ai_generating = False
        self.current_name = result.get("name", "")
        self.current_desc = result.get("description", "")

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_name)
        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, self.current_desc)

        # Focus name field for quick editing
        self.name_entry.focus_set()
        self.name_entry.select_range(0, tk.END)

        self.status_var.set(
            "AI generated -- edit if needed, then Enter to save | "
            "Tab: next field | Esc/Click tile: back to tags"
        )

    def _save_and_next(self):
        """Save current tile as a sprite and advance."""
        pos = self._current_tile()
        if pos is None:
            return

        row, col = pos
        name = self.name_entry.get().strip()
        desc = self.desc_entry.get().strip()
        tile_type = self.type_entry.get().strip()

        if not name:
            self.status_var.set("Name required -- press Tab to generate or type one")
            self.name_entry.focus_set()
            return

        # If this tile was imported, remove the old import entry
        if pos in self.import_data:
            old_name = self.import_data[pos]["name"]
            if old_name in self.sprites:
                del self.sprites[old_name]
            self.import_names.discard(old_name)
            del self.import_data[pos]

        # If re-editing an existing completed sprite, remove the old entry
        # (in case the name changed)
        existing_sprite = self._sprite_at(row, col)
        if existing_sprite:
            old_name, _ = existing_sprite
            if old_name != name and old_name in self.sprites:
                del self.sprites[old_name]

        # Ensure unique name (skip this name's own position)
        base_name = name
        counter = 2
        while name in self.sprites:
            existing = self.sprites[name]
            # If it's the same position, we're overwriting — that's fine
            if existing["row"] == row and existing["col"] == col:
                break
            name = f"{base_name}_{counter}"
            counter += 1

        # Collect tag names
        tag_names = sorted(self.tag_mgr.tags[k] for k in self.active_tags if k in self.tag_mgr.tags)

        # Save sprite
        self.sprites[name] = {
            "row": row,
            "col": col,
            "tiles_x": self.sel_tiles_x,
            "tiles_y": self.sel_tiles_y,
            "description": desc,
            "tile_type": tile_type,
            "tags": tag_names,
        }

        # Mark covered tiles
        for dr in range(self.sel_tiles_y):
            for dc in range(self.sel_tiles_x):
                self.covered_tiles.add((row + dr, col + dc))

        # Add to recent saves for AI context
        self.recent_saves.append({
            "name": name,
            "row": row,
            "col": col,
            "tags": tag_names,
            "description": desc,
        })
        if len(self.recent_saves) > self.RECENT_SAVES_MAX:
            self.recent_saves = self.recent_saves[-self.RECENT_SAVES_MAX:]

        # Auto-save index
        self._save_index()

        # Reset state for next tile
        self.active_tags.clear()
        self.sel_tiles_x = 1
        self.sel_tiles_y = 1
        self._type_auto_filled = False
        self.name_entry.delete(0, tk.END)
        self.type_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self._update_tag_highlights()

        # Advance
        self._advance_to_next_unvisited()
        self._refresh_display()
        self.root.focus_set()

        self.status_var.set(f"Saved '{name}'")
        self.root.after(2000, self._show_tag_mode_status)  # Revert after 2s

    def _skip_tile(self):
        """Skip current tile without saving."""
        self.active_tags.clear()
        self.sel_tiles_x = 1
        self.sel_tiles_y = 1
        self._type_auto_filled = False
        self.name_entry.delete(0, tk.END)
        self.type_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self._update_tag_highlights()
        self._advance_to_next_unvisited()
        self._refresh_display()
        self.root.focus_set()

    def _go_back(self):
        """Go back to previous tile, loading existing data if completed."""
        if self._go_previous():
            self.active_tags.clear()
            self.sel_tiles_x = 1
            self.sel_tiles_y = 1
            self._type_auto_filled = False
            self.name_entry.delete(0, tk.END)
            self.type_entry.delete(0, tk.END)
            self.desc_entry.delete(0, tk.END)

            # If this tile has an existing sprite, load it for editing
            pos = self._current_tile()
            if pos and pos in self.covered_tiles:
                result = self._sprite_at(*pos)
                if result:
                    name, sprite = result
                    self.name_entry.insert(0, name)
                    if sprite.get("tile_type"):
                        self.type_entry.insert(0, sprite["tile_type"])
                    self.desc_entry.insert(0, sprite.get("description", ""))
                    self.sel_tiles_x = sprite.get("tiles_x", 1)
                    self.sel_tiles_y = sprite.get("tiles_y", 1)
                    # Activate tags that match
                    reverse_tags = {v: k for k, v in self.tag_mgr.tags.items()}
                    for tag_name in sprite.get("tags", []):
                        if tag_name in reverse_tags:
                            self.active_tags.add(reverse_tags[tag_name])

            self._update_tag_highlights()
            self._refresh_display()
            self.root.focus_set()

    def _mark_empty(self):
        """Mark current tile as empty and skip."""
        pos = self._current_tile()
        if pos:
            self.nav.empty_tiles.add(pos)
            self._skip_tile()

    def _add_new_tag(self):
        """Prompt user to add a new tag shortcut."""
        result = simpledialog.askstring(
            "Add Tag",
            "Format: key=tagname\n\nExamples: o=obstacle, 9=armor, O=organic",
            parent=self.root,
        )
        if not result:
            return
        if "=" not in result:
            messagebox.showwarning("Invalid Format",
                                   "Use format: key=tagname\n\n"
                                   "Examples:\n  o=obstacle\n  9=armor\n  O=organic")
            self.root.focus_set()
            return

        parts = result.split("=", 1)
        key = parts[0].strip().lower()
        name = parts[1].strip().lower()

        if not key or not name:
            messagebox.showwarning("Invalid", "Both key and name are required.")
            return
        if len(key) != 1:
            messagebox.showwarning("Invalid", "Key must be a single character.")
            return

        if self.tag_mgr.add_tag(key, name):
            self._rebuild_tag_display()
            self._update_tag_highlights()
            self.status_var.set(f"Added tag: [{key}] {name}")
        else:
            messagebox.showwarning("Conflict", f"Key '{key}' is already in use or reserved.")

        self.root.focus_set()

    def _show_help(self):
        help_msg = (
            "TILESET TAGGER -- Keyboard Reference\n\n"
            "TAG MODE (main window focused):\n"
            "  Letter/number keys -- Toggle tags\n"
            "  Tab -- Generate AI name & description\n"
            "  Enter -- Save sprite & advance\n"
            "  Space -- Skip tile\n"
            "  Backspace -- Go back\n"
            "  Delete -- Mark as empty & skip\n"
            "  Arrow keys -- Resize multi-tile selection\n"
            "  + or = -- Add new tag shortcut\n"
            "  F1 -- This help\n"
            "  Escape -- Save & quit\n\n"
            "EDIT MODE (name/type/desc field focused):\n"
            "  Tab -- Next field\n"
            "  Enter -- Save & advance (from desc) or next field (from name/type)\n"
            "  Escape -- Back to tag mode\n\n"
            "WORKFLOW:\n"
            "  1. Press tag keys to describe the tile\n"
            "  2. Press Tab for AI name+description\n"
            "  3. Edit if needed, Enter to save & next\n\n"
            "TIPS:\n"
            "- Type a partial name/desc, Escape, Tab -- the AI\n"
            "  will refine your draft rather than starting fresh.\n"
            "- Append '@: feedback' to a field to workshop it,\n"
            "  e.g. 'wooden_crate @: this is a chest not crate'"
        )
        messagebox.showinfo("Help", help_msg, parent=self.root)
        self.root.focus_set()

    def _on_quit(self):
        """Save and close."""
        self._save_index()
        self.tag_mgr.save_empty_tiles(self.nav.empty_tiles)
        self.ai.cleanup()
        print(f"\nSaved {len(self.sprites)} sprites to {self.output_path}")
        print(f"Saved {len(self.nav.empty_tiles)} empty tiles to config")
        self.root.destroy()

    # ── Run ────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive tileset tagger with AI-assisted naming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s tileset.png
  %(prog)s tileset.png --tile-size 16
  %(prog)s atlas.png --output my_index.json --model sonnet
  %(prog)s kenney_indoors.png --tile-size 32 --model haiku
  %(prog)s urizen_1bit.png --bg-color ffffff  (white bg = empty)
  %(prog)s tileset.png --import-index old_index.json  (enrich existing)

The tool auto-saves progress to the output file. Re-run with the same
arguments to resume where you left off.

Press F1 inside the GUI for keyboard shortcuts.
""",
    )
    parser.add_argument("tileset", help="Path to tileset/atlas PNG image")
    parser.add_argument("--tile-size", type=int, default=32,
                        help="Tile size in pixels (default: 32)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output index.json path (default: <tileset>_index.json)")
    parser.add_argument("--model", choices=["haiku", "sonnet", "opus"], default="haiku",
                        help="Claude model for AI naming (default: haiku)")
    parser.add_argument("--bg-color", default=None, metavar="RRGGBB",
                        help="Background color to treat as empty (hex, e.g. 'ffffff' for white)")
    parser.add_argument("--import-index", default=None, metavar="INDEX.json",
                        help="Import existing index for review/enrichment (pre-populates names)")

    args = parser.parse_args()

    tileset_path = Path(args.tileset).resolve()
    if not tileset_path.exists():
        print(f"Error: File not found: {args.tileset}", file=sys.stderr)
        sys.exit(1)

    # Parse bg color
    bg_color = None
    if args.bg_color:
        h = args.bg_color.lstrip("#")
        if len(h) == 6:
            bg_color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        else:
            print(f"Error: Invalid color format '{args.bg_color}', use RRGGBB hex", file=sys.stderr)
            sys.exit(1)

    app = TaggerApp(
        tileset_path=str(tileset_path),
        tile_size=args.tile_size,
        output_path=args.output,
        model=args.model,
        bg_color=bg_color,
        import_path=args.import_index,
    )
    app.run()


if __name__ == "__main__":
    main()
