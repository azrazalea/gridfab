"""GridFab CLI — command-line interface for creating and editing pixel art.

Usage: gridfab <command> [args...]

Commands:
    init [--size WxH] [dir]                  Create blank sprite directory
    render [dir]                             Render preview.png (checkerboard bg)
    pixel <row> <col> <color> [--dir]       Set a single pixel by coordinate
    pixels <r,c,color> [...] [--dir]        Set multiple pixels in one call
    row <row> <v0 v1 ...> [--dir]           Replace a single row (0-indexed)
    rows <start> <end> <v0 v1 ...> [--dir]  Replace a range of rows (inclusive)
    fill <row> <col_start> <col_end> <c>    Fill horizontal span with one color
    rect <r0> <c0> <r1> <c1> <color>        Fill a rectangle with one color
    clear [dir]                              Reset grid to all transparent
    clean [dir]                              Remove generated files (preview, scaled outputs)
    export [dir]                             Export PNGs at configured scales
    icon [dir]                               Export .ico file (square grids)
    palette [dir]                            Display current palette
    tag <tileset.png> [options]              Interactive tileset tagger with AI
    atlas <out> [sprites...] [options]       Pack sprites into a spritesheet
    import <image> [output] [options]         Import image to grid.txt format
    frame add [--from N|--blank] [dir]       Add a new animation frame
    frame delete <N> [dir]                   Delete a frame (renumbers remaining)
    frame select <N> [dir]                   Set active frame
    frame list [dir]                         List all frames
    anim add <name> --frames 1,2,3 [opts]   Define a named animation
    anim list [dir]                          List all animations
    anim delete <name> [dir]                 Delete a named animation
    anim sheet <name> [--scale N] [dir]      Export animation spritesheet
    anim sheets [--scale N] [dir]            Export all animation spritesheets
    anim gif <name> [--scale N] [dir]        Export animated GIF
    anim preview <name> [--scale N] [dir]    Alias for gif
"""

import argparse
import sys
from pathlib import Path


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_size(size_str: str) -> tuple[int, int]:
    """Parse a WxH size string like '32x32' or '16x16'. Raises ValueError."""
    parts = size_str.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Size must be WxH (e.g. 32x32), got: '{size_str}'")
    try:
        w = int(parts[0])
    except ValueError:
        raise ValueError(f"width must be an integer, got: '{parts[0]}'")
    try:
        h = int(parts[1])
    except ValueError:
        raise ValueError(f"height must be an integer, got: '{parts[1]}'")
    if w < 1 or h < 1:
        raise ValueError(f"Size must be positive, got: {w}x{h}")
    return w, h


def _parse_size(size_str: str) -> tuple[int, int]:
    """Parse a WxH size string, dying on error."""
    try:
        return parse_size(size_str)
    except ValueError as e:
        _die(str(e))
        return 0, 0  # unreachable


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gridfab",
        description="Human-AI collaborative pixel art editor",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Create a new sprite directory")
    p_init.add_argument("--size", default="32x32", help="Grid size as WxH (default: 32x32)")
    p_init.add_argument("directory", nargs="?", default=".", help="Target directory")

    # render / show
    p_render = sub.add_parser("render", help="Render preview.png")
    p_render.add_argument("directory", nargs="?", default=".", help="Sprite directory")
    p_render.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")
    p_show = sub.add_parser("show", help="Alias for render")
    p_show.add_argument("directory", nargs="?", default=".", help="Sprite directory")
    p_show.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # pixel
    p_pixel = sub.add_parser("pixel", help="Set a single pixel by coordinate")
    p_pixel.add_argument("row", type=int, help="Row number (0-indexed)")
    p_pixel.add_argument("col", type=int, help="Column number (0-indexed)")
    p_pixel.add_argument("color", help="Color alias or #RRGGBB")
    p_pixel.add_argument("--dir", default=".", help="Sprite directory")
    p_pixel.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # pixels
    p_pixels = sub.add_parser("pixels", help="Set multiple pixels: row,col,color ...")
    p_pixels.add_argument("specs", nargs="+", help="Pixel specs as row,col,color")
    p_pixels.add_argument("--dir", default=".", help="Sprite directory")
    p_pixels.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # row
    p_row = sub.add_parser("row", help="Replace a single row")
    p_row.add_argument("row_num", type=int, help="Row number (0-indexed)")
    p_row.add_argument("values", nargs="+", help="Space-separated cell values")
    p_row.add_argument("--dir", default=".", help="Sprite directory")
    p_row.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # rows
    p_rows = sub.add_parser("rows", help="Replace a range of rows")
    p_rows.add_argument("start", type=int, help="Start row (inclusive)")
    p_rows.add_argument("end", type=int, help="End row (inclusive)")
    p_rows.add_argument("values", nargs="+", help="Space-separated cell values")
    p_rows.add_argument("--dir", default=".", help="Sprite directory")
    p_rows.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # fill
    p_fill = sub.add_parser("fill", help="Fill a horizontal span")
    p_fill.add_argument("row", type=int, help="Row number")
    p_fill.add_argument("col_start", type=int, help="Start column (inclusive)")
    p_fill.add_argument("col_end", type=int, help="End column (inclusive)")
    p_fill.add_argument("color", help="Color alias or #RRGGBB")
    p_fill.add_argument("--dir", default=".", help="Sprite directory")
    p_fill.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # rect
    p_rect = sub.add_parser("rect", help="Fill a rectangle")
    p_rect.add_argument("r0", type=int, help="Start row")
    p_rect.add_argument("c0", type=int, help="Start column")
    p_rect.add_argument("r1", type=int, help="End row")
    p_rect.add_argument("c1", type=int, help="End column")
    p_rect.add_argument("color", help="Color alias or #RRGGBB")
    p_rect.add_argument("--dir", default=".", help="Sprite directory")
    p_rect.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # clear
    p_clear = sub.add_parser("clear", help="Reset grid to all transparent")
    p_clear.add_argument("directory", nargs="?", default=".", help="Sprite directory")
    p_clear.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # clean
    p_clean_files = sub.add_parser("clean", help="Remove generated files (preview, scaled outputs)")
    p_clean_files.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # export
    p_export = sub.add_parser("export", help="Export PNGs at multiple scales")
    p_export.add_argument("directory", nargs="?", default=".", help="Sprite directory")
    p_export.add_argument("--frame", type=int, default=None, help="Frame number (for animated sprites)")

    # icon
    p_icon = sub.add_parser("icon", help="Export .ico file (requires square grid)")
    p_icon.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # palette
    p_palette = sub.add_parser("palette", help="Display or manage palette")
    palette_sub = p_palette.add_subparsers(dest="palette_command")

    p_palette_show = palette_sub.add_parser("show", help="Display current palette")
    p_palette_show.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_palette_rename = palette_sub.add_parser("rename", help="Rename a palette alias")
    p_palette_rename.add_argument("old_alias", help="Existing alias to rename")
    p_palette_rename.add_argument("new_alias", help="New alias name")
    p_palette_rename.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # Allow bare "palette [dir]" for backward compat
    p_palette.add_argument("--dir", default=".", help="Sprite directory")

    # tag
    p_tag = sub.add_parser("tag", help="Interactive tileset tagger with AI naming")
    p_tag.add_argument("tileset", help="Path to tileset/atlas PNG image")
    p_tag.add_argument("--tile-size", type=int, default=32,
                       help="Tile size in pixels (default: 32)")
    p_tag.add_argument("--output", "-o", default=None,
                       help="Output index.json path (default: <tileset>_index.json)")
    p_tag.add_argument("--model", choices=["haiku", "sonnet", "opus"], default="haiku",
                       help="Claude model for AI naming (default: haiku)")
    p_tag.add_argument("--bg-color", default=None, metavar="RRGGBB",
                       help="Background color to treat as empty (hex, e.g. 'ffffff')")
    p_tag.add_argument("--import-index", default=None, metavar="INDEX.json",
                       help="Import existing index for review/enrichment")

    # atlas
    p_atlas = sub.add_parser("atlas", help="Pack sprites into a spritesheet")
    p_atlas.add_argument("output_dir", help="Output directory for atlas.png + index.json")
    p_atlas.add_argument("sprites", nargs="*", help="Sprite directories")
    p_atlas.add_argument("--include", action="append", help="Glob pattern to find sprite dirs (repeatable)")
    p_atlas.add_argument("--exclude", action="append", help="Glob pattern to exclude sprite dirs (repeatable)")
    p_atlas.add_argument("--tile-size", default=None, help="Base tile size as WxH (default: auto-detect)")
    p_atlas.add_argument("--columns", type=int, default=None, help="Columns in atlas grid")
    p_atlas.add_argument("--reorder", action="store_true", help="Ignore existing index, place from scratch")
    p_atlas.add_argument("--atlas-name", default="atlas.png", help="Output atlas filename (default: atlas.png)")
    p_atlas.add_argument("--index-name", default="index.json", help="Output index filename (default: index.json)")

    # import
    p_import = sub.add_parser("import", help="Import image to grid.txt format")
    p_import.add_argument("image", help="Path to image file (any format Pillow supports)")
    p_import.add_argument("output", nargs="?", default=None, help="Output directory")
    p_import.add_argument("--tile-size", default=None, help="Tile size as WxH (enables tilesheet mode)")
    p_import.add_argument("--tile", default=None, metavar="COL,ROW", help="Extract single tile at 0-indexed position")
    p_import.add_argument("--index", default=None, help="Atlas index.json for naming sprites")
    p_import.add_argument("--alpha-threshold", type=int, default=128, help="Alpha threshold (0-255, default 128)")

    # gui
    p_gui = sub.add_parser("gui", help="Launch the GUI editor")
    p_gui.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # frame
    p_frame = sub.add_parser("frame", help="Manage animation frames")
    frame_sub = p_frame.add_subparsers(dest="frame_command")

    p_frame_add = frame_sub.add_parser("add", help="Add a new frame")
    p_frame_add.add_argument("--from", type=int, default=None, dest="from_frame",
                             help="Copy from specific frame number")
    p_frame_add.add_argument("--blank", action="store_true", help="Create blank transparent frame")
    p_frame_add.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_frame_del = frame_sub.add_parser("delete", help="Delete a frame")
    p_frame_del.add_argument("frame_num", type=int, help="Frame number to delete")
    p_frame_del.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_frame_sel = frame_sub.add_parser("select", help="Set active frame")
    p_frame_sel.add_argument("frame_num", type=int, help="Frame number to activate")
    p_frame_sel.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_frame_list = frame_sub.add_parser("list", help="List all frames")
    p_frame_list.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_frame_cp = frame_sub.add_parser("copy-rect", help="Copy rectangle from one frame to another")
    p_frame_cp.add_argument("r0", type=int, help="Top-left row")
    p_frame_cp.add_argument("c0", type=int, help="Top-left column")
    p_frame_cp.add_argument("r1", type=int, help="Bottom-right row")
    p_frame_cp.add_argument("c1", type=int, help="Bottom-right column")
    p_frame_cp.add_argument("--from", type=int, required=True, dest="src_frame", help="Source frame number")
    p_frame_cp.add_argument("--to", type=int, required=True, dest="dst_frame", help="Destination frame number")
    p_frame_cp.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # anim
    p_anim = sub.add_parser("anim", help="Manage named animations")
    anim_sub = p_anim.add_subparsers(dest="anim_command")

    p_anim_add = anim_sub.add_parser("add", help="Define a named animation")
    p_anim_add.add_argument("name", help="Animation name (e.g. walk, idle, attack)")
    p_anim_add.add_argument("--frames", required=True,
                            help="Comma-separated frame numbers (e.g. 1,2,3,4)")
    p_anim_add.add_argument("--fps", type=int, default=8, help="Frames per second (default: 8)")
    p_anim_add.add_argument("--loop", action="store_true", default=True, help="Loop animation (default)")
    p_anim_add.add_argument("--no-loop", action="store_false", dest="loop", help="Don't loop")
    p_anim_add.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_list = anim_sub.add_parser("list", help="List all animations")
    p_anim_list.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_del = anim_sub.add_parser("delete", help="Delete a named animation")
    p_anim_del.add_argument("name", help="Animation name to delete")
    p_anim_del.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_sheet = anim_sub.add_parser("sheet", help="Export animation spritesheet")
    p_anim_sheet.add_argument("name", help="Animation name")
    p_anim_sheet.add_argument("--scale", type=int, default=1, help="Scale factor (default: 1)")
    p_anim_sheet.add_argument("--layout", choices=["horizontal", "vertical", "grid"],
                              default="horizontal", help="Layout (default: horizontal)")
    p_anim_sheet.add_argument("--columns", type=int, default=None, help="Columns for grid layout")
    p_anim_sheet.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_sheets = anim_sub.add_parser("sheets", help="Export all animation spritesheets")
    p_anim_sheets.add_argument("--scale", type=int, default=1, help="Scale factor (default: 1)")
    p_anim_sheets.add_argument("--layout", choices=["horizontal", "vertical", "grid"],
                               default="horizontal", help="Layout (default: horizontal)")
    p_anim_sheets.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_gif = anim_sub.add_parser("gif", help="Export animated GIF")
    p_anim_gif.add_argument("name", help="Animation name")
    p_anim_gif.add_argument("--scale", type=int, default=1, help="Scale factor (default: 1)")
    p_anim_gif.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    p_anim_preview = anim_sub.add_parser("preview", help="Export animated GIF (alias for gif)")
    p_anim_preview.add_argument("name", help="Animation name")
    p_anim_preview.add_argument("--scale", type=int, default=1, help="Scale factor (default: 1)")
    p_anim_preview.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        _dispatch(args)
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        _die(str(e))


def _dispatch(args: argparse.Namespace) -> None:
    from gridfab.commands.init import cmd_init
    from gridfab.commands.edit import cmd_row, cmd_rows, cmd_fill, cmd_rect, cmd_pixel, cmd_pixels, cmd_clear, cmd_clean_files
    from gridfab.commands.render_cmd import cmd_render
    from gridfab.commands.export_cmd import cmd_export, cmd_palette
    from gridfab.commands.icon_cmd import cmd_icon

    cmd = args.command

    if cmd == "init":
        w, h = _parse_size(args.size)
        cmd_init(Path(args.directory), w, h)

    elif cmd in ("render", "show"):
        cmd_render(Path(args.directory), frame=args.frame)

    elif cmd == "pixel":
        cmd_pixel(Path(args.dir), args.row, args.col, args.color, frame=args.frame)

    elif cmd == "pixels":
        cmd_pixels(Path(args.dir), args.specs, frame=args.frame)

    elif cmd == "row":
        cmd_row(Path(args.dir), args.row_num, args.values, frame=args.frame)

    elif cmd == "rows":
        cmd_rows(Path(args.dir), args.start, args.end, args.values, frame=args.frame)

    elif cmd == "fill":
        cmd_fill(Path(args.dir), args.row, args.col_start, args.col_end, args.color, frame=args.frame)

    elif cmd == "rect":
        cmd_rect(Path(args.dir), args.r0, args.c0, args.r1, args.c1, args.color, frame=args.frame)

    elif cmd == "clear":
        cmd_clear(Path(args.directory), frame=args.frame)

    elif cmd == "clean":
        cmd_clean_files(Path(args.directory))

    elif cmd == "export":
        cmd_export(Path(args.directory), frame=args.frame)

    elif cmd == "icon":
        cmd_icon(Path(args.directory))

    elif cmd == "palette":
        from gridfab.commands.export_cmd import cmd_palette_rename
        pcmd = args.palette_command
        if pcmd == "rename":
            cmd_palette_rename(Path(args.directory), args.old_alias, args.new_alias)
        elif pcmd == "show":
            cmd_palette(Path(args.directory))
        else:
            # Bare "palette" without subcommand — show palette
            cmd_palette(Path(args.dir))

    elif cmd == "tag":
        from gridfab.tagger.app import TaggerApp

        # Parse bg color
        bg_color = None
        if args.bg_color:
            h = args.bg_color.lstrip("#")
            if len(h) != 6:
                _die(f"Invalid color format '{args.bg_color}', use RRGGBB hex")
            bg_color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        tileset_path = Path(args.tileset).resolve()
        if not tileset_path.exists():
            _die(f"File not found: {args.tileset}")

        app = TaggerApp(
            tileset_path=str(tileset_path),
            tile_size=args.tile_size,
            output_path=args.output,
            model=args.model,
            bg_color=bg_color,
            import_path=args.import_index,
        )
        app.run()

    elif cmd == "atlas":
        from gridfab.commands.atlas_cmd import cmd_atlas, resolve_sprite_dirs

        tile_size = None
        if args.tile_size:
            tile_size = _parse_size(args.tile_size)

        sprite_dirs = resolve_sprite_dirs(
            args.sprites, args.include, args.exclude
        )
        cmd_atlas(
            Path(args.output_dir),
            sprite_dirs,
            tile_size=tile_size,
            columns=args.columns,
            reorder=args.reorder,
            atlas_name=args.atlas_name,
            index_name=args.index_name,
        )

    elif cmd == "frame":
        from gridfab.commands.frame_cmd import (
            cmd_frame_add, cmd_frame_delete, cmd_frame_select, cmd_frame_list,
            cmd_frame_copy_rect,
        )

        fcmd = args.frame_command
        if not fcmd:
            print("Usage: gridfab frame {add|delete|select|list}")
            sys.exit(1)

        if fcmd == "add":
            cmd_frame_add(
                Path(args.directory),
                from_frame=args.from_frame,
                blank=args.blank,
            )
        elif fcmd == "delete":
            cmd_frame_delete(Path(args.directory), args.frame_num)
        elif fcmd == "select":
            cmd_frame_select(Path(args.directory), args.frame_num)
        elif fcmd == "list":
            cmd_frame_list(Path(args.directory))
        elif fcmd == "copy-rect":
            cmd_frame_copy_rect(
                Path(args.directory),
                args.r0, args.c0, args.r1, args.c1,
                src_frame=args.src_frame,
                dst_frame=args.dst_frame,
            )

    elif cmd == "anim":
        from gridfab.commands.anim_cmd import (
            cmd_anim_add, cmd_anim_list, cmd_anim_delete,
            cmd_anim_sheet, cmd_anim_sheets, cmd_anim_gif,
        )

        acmd = args.anim_command
        if not acmd:
            print("Usage: gridfab anim {add|list|delete|sheet|sheets|gif|preview}")
            sys.exit(1)

        if acmd == "add":
            frames = [int(x) for x in args.frames.split(",")]
            cmd_anim_add(
                Path(args.directory), args.name, frames,
                fps=args.fps, loop=args.loop,
            )
        elif acmd == "list":
            cmd_anim_list(Path(args.directory))
        elif acmd == "delete":
            cmd_anim_delete(Path(args.directory), args.name)
        elif acmd == "sheet":
            cmd_anim_sheet(
                Path(args.directory), args.name,
                scale=args.scale, layout=args.layout, columns=args.columns,
            )
        elif acmd == "sheets":
            cmd_anim_sheets(
                Path(args.directory),
                scale=args.scale, layout=args.layout,
            )
        elif acmd in ("gif", "preview"):
            cmd_anim_gif(Path(args.directory), args.name, scale=args.scale)

    elif cmd == "gui":
        import tkinter as tk
        from gridfab.gui import PixelEditor
        root = tk.Tk()
        PixelEditor(root, Path(args.directory))
        root.mainloop()

    elif cmd == "import":
        from gridfab.commands.import_cmd import cmd_import

        tile_size = None
        if args.tile_size:
            tile_size = _parse_size(args.tile_size)

        tile_pos = None
        if args.tile:
            parts = args.tile.split(",")
            if len(parts) != 2:
                _die(f"--tile must be COL,ROW (e.g. 3,2), got: '{args.tile}'")
            try:
                tile_pos = (int(parts[0]), int(parts[1]))
            except ValueError:
                _die(f"--tile coordinates must be integers, got: '{args.tile}'")

        index_path = Path(args.index) if args.index else None
        output_path = Path(args.output) if args.output else None

        cmd_import(
            Path(args.image),
            output_path,
            tile_size=tile_size,
            tile_pos=tile_pos,
            index=index_path,
            alpha_threshold=args.alpha_threshold,
        )
