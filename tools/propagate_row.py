#!/usr/bin/env python3
"""One-off script: propagate a tagged template row to similar rows below it.

Usage:
    python propagate_row.py <tileset.png> <index.json> --template-row ROW
           --col-start COL --col-end COL --prefix "masc_character_"
           [--bg-color RRGGBB] [--tile-size N]

For each row below the template that has non-empty tiles in matching positions,
shows a preview and asks for a new prefix. The template sprite names have the
old prefix replaced with the new one.
"""

import json
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
import argparse


def is_empty(img, tile_size, row, col, bg_color=None):
    """Check if a tile is empty (transparent or bg_color)."""
    ts = tile_size
    tile = img.crop((col * ts, row * ts, (col + 1) * ts, (row + 1) * ts))
    pixels = list(tile.getdata())
    if all(p[3] == 0 for p in pixels):
        return True
    if bg_color and all(p[:3] == bg_color[:3] for p in pixels):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Propagate template row to similar rows")
    parser.add_argument("tileset", help="Path to tileset PNG")
    parser.add_argument("index", help="Path to index.json")
    parser.add_argument("--template-row", type=int, required=True, help="Row number of the template")
    parser.add_argument("--col-start", type=int, required=True, help="First column of the template range")
    parser.add_argument("--col-end", type=int, required=True, help="Last column of the template range (inclusive)")
    parser.add_argument("--prefix", required=True, help="Prefix to replace (e.g. 'masc_character_')")
    parser.add_argument("--tile-size", type=int, default=32, help="Tile size in pixels (default: 32)")
    parser.add_argument("--bg-color", default=None, help="Background color as RRGGBB hex")
    parser.add_argument("--start-row", type=int, default=None,
                        help="First row to propagate to (default: template-row + 1)")

    args = parser.parse_args()

    tileset_path = Path(args.tileset).resolve()
    index_path = Path(args.index).resolve()

    if not tileset_path.exists():
        print(f"Error: {tileset_path} not found", file=sys.stderr)
        sys.exit(1)
    if not index_path.exists():
        print(f"Error: {index_path} not found", file=sys.stderr)
        sys.exit(1)

    bg_color = None
    if args.bg_color:
        h = args.bg_color.lstrip("#")
        bg_color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    ts = args.tile_size
    img = Image.open(tileset_path).convert("RGBA")
    total_cols = img.width // ts
    total_rows = img.height // ts

    index = json.loads(index_path.read_text())
    sprites = index.get("sprites", {})

    # Gather template sprites: names at (template_row, col) for col in range
    template_row = args.template_row
    col_start = args.col_start
    col_end = args.col_end
    old_prefix = args.prefix

    # Find template sprites by position
    template = {}  # col -> (name, sprite_data)
    for name, sp in sprites.items():
        if sp["row"] == template_row and col_start <= sp["col"] <= col_end:
            template[sp["col"]] = (name, sp)

    if not template:
        print(f"Error: No sprites found in row {template_row}, cols {col_start}-{col_end}")
        sys.exit(1)

    print(f"Template row {template_row}: {len(template)} sprites, prefix='{old_prefix}'")
    for col in sorted(template.keys()):
        name, _ = template[col]
        suffix = name[len(old_prefix):] if name.startswith(old_prefix) else f"[{name}]"
        print(f"  col {col}: {name} -> __{suffix}")

    # Find which columns have content in the template
    template_cols = sorted(template.keys())

    # Build GUI for row-by-row preview + prefix input
    start_row = args.start_row if args.start_row is not None else template_row + 1

    # Collect rows that have at least one non-empty tile in the template columns
    candidate_rows = []
    for r in range(start_row, total_rows):
        has_content = False
        for c in template_cols:
            if not is_empty(img, ts, r, c, bg_color):
                has_content = True
                break
        if has_content:
            candidate_rows.append(r)

    if not candidate_rows:
        print("No candidate rows found below the template.")
        sys.exit(0)

    print(f"\nFound {len(candidate_rows)} candidate rows to label.")

    # GUI
    root = tk.Tk()
    root.title("Propagate Row")
    root.configure(bg="#2b2b2b")

    row_idx = [0]  # mutable for closures
    added_count = [0]
    skipped_rows = []

    # Show template row for reference
    tk.Label(root, text="Template row:", fg="#aaa", bg="#2b2b2b",
             font=("monospace", 10)).pack(anchor="w", padx=8, pady=(8, 0))

    template_strip = img.crop((col_start * ts, template_row * ts,
                               (col_end + 1) * ts, (template_row + 1) * ts))
    scale = max(1, min(4, 800 // template_strip.width))
    template_zoomed = template_strip.resize(
        (template_strip.width * scale, template_strip.height * scale), Image.NEAREST)
    template_photo = ImageTk.PhotoImage(template_zoomed)
    template_label = tk.Label(root, image=template_photo, bg="#1a1a1a")
    template_label.pack(padx=8, pady=4)

    # Current row preview
    tk.Label(root, text="Current row:", fg="#aaa", bg="#2b2b2b",
             font=("monospace", 10)).pack(anchor="w", padx=8, pady=(8, 0))

    preview_label = tk.Label(root, bg="#1a1a1a")
    preview_label.pack(padx=8, pady=4)

    info_var = tk.StringVar()
    tk.Label(root, textvariable=info_var, fg="#ccc", bg="#333",
             font=("monospace", 10), anchor="w", padx=8).pack(fill=tk.X, padx=8, pady=2)

    # Prefix input
    input_frame = tk.Frame(root, bg="#2b2b2b")
    input_frame.pack(fill=tk.X, padx=8, pady=4)

    tk.Label(input_frame, text="New prefix:", fg="#aaa", bg="#2b2b2b",
             font=("monospace", 10)).pack(side=tk.LEFT, padx=(0, 4))

    prefix_entry = tk.Entry(input_frame, font=("monospace", 12), bg="#1a1a1a", fg="#fff",
                            insertbackground="#fff", relief="flat", highlightthickness=1,
                            highlightcolor="#4fc3f7", highlightbackground="#555")
    prefix_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Preview of what names will be generated
    names_var = tk.StringVar()
    names_label = tk.Label(root, textvariable=names_var, fg="#888", bg="#2b2b2b",
                           font=("monospace", 9), anchor="w", justify=tk.LEFT, padx=8)
    names_label.pack(fill=tk.X, padx=8, pady=2)

    status_var = tk.StringVar(value="Enter prefix, then press Enter to apply | Space to skip | Esc to finish")
    tk.Label(root, textvariable=status_var, fg="#888", bg="#222",
             font=("monospace", 9), anchor="w", padx=8, pady=4).pack(fill=tk.X, side=tk.BOTTOM)

    photos = []  # prevent GC

    def show_row():
        if row_idx[0] >= len(candidate_rows):
            finish()
            return

        r = candidate_rows[row_idx[0]]

        # Show row preview
        row_strip = img.crop((col_start * ts, r * ts,
                              (col_end + 1) * ts, (r + 1) * ts))
        zoomed = row_strip.resize(
            (row_strip.width * scale, row_strip.height * scale), Image.NEAREST)
        photo = ImageTk.PhotoImage(zoomed)
        photos.clear()
        photos.append(photo)
        preview_label.configure(image=photo)

        # Which template cols are non-empty in this row?
        active = []
        for c in template_cols:
            if not is_empty(img, ts, r, c, bg_color):
                name, _ = template[c]
                suffix = name[len(old_prefix):] if name.startswith(old_prefix) else name
                active.append(suffix)

        info_var.set(f"Row {r} | {len(active)}/{len(template_cols)} tiles | "
                     f"{row_idx[0] + 1}/{len(candidate_rows)} rows | "
                     f"{added_count[0]} sprites added so far")

        prefix_entry.delete(0, tk.END)
        update_preview()
        prefix_entry.focus_set()

    def update_preview(*_):
        if row_idx[0] >= len(candidate_rows):
            return
        r = candidate_rows[row_idx[0]]
        new_prefix = prefix_entry.get().strip()
        if not new_prefix:
            names_var.set("(type a prefix to see preview)")
            return

        lines = []
        for c in template_cols:
            if not is_empty(img, ts, r, c, bg_color):
                name, _ = template[c]
                suffix = name[len(old_prefix):] if name.startswith(old_prefix) else name
                lines.append(f"  col {c}: {new_prefix}{suffix}")
            else:
                lines.append(f"  col {c}: (empty, skip)")
        names_var.set("\n".join(lines))

    def apply_prefix(event=None):
        if row_idx[0] >= len(candidate_rows):
            return
        r = candidate_rows[row_idx[0]]
        new_prefix = prefix_entry.get().strip()
        if not new_prefix:
            status_var.set("Prefix required!")
            return

        count = 0
        for c in template_cols:
            if not is_empty(img, ts, r, c, bg_color):
                old_name, sp = template[c]
                suffix = old_name[len(old_prefix):] if old_name.startswith(old_prefix) else old_name
                new_name = new_prefix + suffix

                # Deduplicate
                base = new_name
                counter = 2
                while new_name in sprites:
                    if sprites[new_name]["row"] == r and sprites[new_name]["col"] == c:
                        break
                    new_name = f"{base}_{counter}"
                    counter += 1

                sprites[new_name] = {
                    "row": r,
                    "col": c,
                    "tiles_x": sp.get("tiles_x", 1),
                    "tiles_y": sp.get("tiles_y", 1),
                    "description": sp.get("description", "").replace(old_prefix.rstrip("_"), new_prefix.rstrip("_")),
                    "tile_type": sp.get("tile_type", ""),
                    "tags": sp.get("tags", []),
                }
                count += 1

        added_count[0] += count
        status_var.set(f"Added {count} sprites for row {r} with prefix '{new_prefix}'")

        # Auto-save after each row
        index_path.write_text(json.dumps(index, indent=2))

        row_idx[0] += 1
        root.after(200, show_row)

    def skip_row(event=None):
        if row_idx[0] >= len(candidate_rows):
            return
        r = candidate_rows[row_idx[0]]
        skipped_rows.append(r)
        status_var.set(f"Skipped row {r}")
        row_idx[0] += 1
        root.after(200, show_row)

    def finish(event=None):
        index_path.write_text(json.dumps(index, indent=2))
        print(f"\nDone! Added {added_count[0]} sprites total.")
        if skipped_rows:
            print(f"Skipped rows: {skipped_rows}")
        root.destroy()

    prefix_entry.bind("<Return>", apply_prefix)
    prefix_entry.bind("<KeyRelease>", update_preview)
    root.bind("<Escape>", finish)
    # Space to skip only when entry not focused... actually let's use a button
    skip_btn = tk.Button(input_frame, text="Skip (no prefix)", command=skip_row,
                         fg="#aaa", bg="#333", font=("monospace", 9), relief="flat")
    skip_btn.pack(side=tk.RIGHT, padx=(4, 0))

    show_row()
    root.mainloop()


if __name__ == "__main__":
    main()
