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
    export [dir]                             Export PNGs at configured scales
    icon [dir]                               Export .ico file (square grids)
    palette [dir]                            Display current palette
    atlas <out> [sprites...] [options]       Pack sprites into a spritesheet
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
    p_show = sub.add_parser("show", help="Alias for render")
    p_show.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # pixel
    p_pixel = sub.add_parser("pixel", help="Set a single pixel by coordinate")
    p_pixel.add_argument("row", type=int, help="Row number (0-indexed)")
    p_pixel.add_argument("col", type=int, help="Column number (0-indexed)")
    p_pixel.add_argument("color", help="Color alias or #RRGGBB")
    p_pixel.add_argument("--dir", default=".", help="Sprite directory")

    # pixels
    p_pixels = sub.add_parser("pixels", help="Set multiple pixels: row,col,color ...")
    p_pixels.add_argument("specs", nargs="+", help="Pixel specs as row,col,color")
    p_pixels.add_argument("--dir", default=".", help="Sprite directory")

    # row
    p_row = sub.add_parser("row", help="Replace a single row")
    p_row.add_argument("row_num", type=int, help="Row number (0-indexed)")
    p_row.add_argument("values", nargs="+", help="Space-separated cell values")
    p_row.add_argument("--dir", default=".", help="Sprite directory")

    # rows
    p_rows = sub.add_parser("rows", help="Replace a range of rows")
    p_rows.add_argument("start", type=int, help="Start row (inclusive)")
    p_rows.add_argument("end", type=int, help="End row (inclusive)")
    p_rows.add_argument("values", nargs="+", help="Space-separated cell values")
    p_rows.add_argument("--dir", default=".", help="Sprite directory")

    # fill
    p_fill = sub.add_parser("fill", help="Fill a horizontal span")
    p_fill.add_argument("row", type=int, help="Row number")
    p_fill.add_argument("col_start", type=int, help="Start column (inclusive)")
    p_fill.add_argument("col_end", type=int, help="End column (inclusive)")
    p_fill.add_argument("color", help="Color alias or #RRGGBB")
    p_fill.add_argument("--dir", default=".", help="Sprite directory")

    # rect
    p_rect = sub.add_parser("rect", help="Fill a rectangle")
    p_rect.add_argument("r0", type=int, help="Start row")
    p_rect.add_argument("c0", type=int, help="Start column")
    p_rect.add_argument("r1", type=int, help="End row")
    p_rect.add_argument("c1", type=int, help="End column")
    p_rect.add_argument("color", help="Color alias or #RRGGBB")
    p_rect.add_argument("--dir", default=".", help="Sprite directory")

    # clear
    p_clear = sub.add_parser("clear", help="Reset grid to all transparent")
    p_clear.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # export
    p_export = sub.add_parser("export", help="Export PNGs at multiple scales")
    p_export.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # icon
    p_icon = sub.add_parser("icon", help="Export .ico file (requires square grid)")
    p_icon.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # palette
    p_palette = sub.add_parser("palette", help="Display current palette")
    p_palette.add_argument("directory", nargs="?", default=".", help="Sprite directory")

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
    from gridfab.commands.edit import cmd_row, cmd_rows, cmd_fill, cmd_rect, cmd_pixel, cmd_pixels, cmd_clear
    from gridfab.commands.render_cmd import cmd_render
    from gridfab.commands.export_cmd import cmd_export, cmd_palette
    from gridfab.commands.icon_cmd import cmd_icon

    cmd = args.command

    if cmd == "init":
        w, h = _parse_size(args.size)
        cmd_init(Path(args.directory), w, h)

    elif cmd in ("render", "show"):
        cmd_render(Path(args.directory))

    elif cmd == "pixel":
        cmd_pixel(Path(args.dir), args.row, args.col, args.color)

    elif cmd == "pixels":
        cmd_pixels(Path(args.dir), args.specs)

    elif cmd == "row":
        cmd_row(Path(args.dir), args.row_num, args.values)

    elif cmd == "rows":
        cmd_rows(Path(args.dir), args.start, args.end, args.values)

    elif cmd == "fill":
        cmd_fill(Path(args.dir), args.row, args.col_start, args.col_end, args.color)

    elif cmd == "rect":
        cmd_rect(Path(args.dir), args.r0, args.c0, args.r1, args.c1, args.color)

    elif cmd == "clear":
        cmd_clear(Path(args.directory))

    elif cmd == "export":
        cmd_export(Path(args.directory))

    elif cmd == "icon":
        cmd_icon(Path(args.directory))

    elif cmd == "palette":
        cmd_palette(Path(args.directory))

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
