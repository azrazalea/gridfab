"""GridFab CLI — command-line interface for creating and editing pixel art.

Usage: gridfab <command> [args...]

Commands:
    init [--size WxH] [dir]                  Create blank sprite directory
    render [dir]                             Render preview.png (checkerboard bg)
    row <row> <v0 v1 ...> [dir]             Replace a single row (0-indexed)
    rows <start> <end> <v0 v1 ...> [dir]    Replace a range of rows (inclusive)
    fill <row> <col_start> <col_end> <c>    Fill horizontal span with one color
    rect <r0> <c0> <r1> <c1> <color>        Fill a rectangle with one color
    export [dir]                             Export PNGs at configured scales
    palette [dir]                            Display current palette
"""

import argparse
import sys
from pathlib import Path


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _parse_int(s: str, name: str) -> int:
    try:
        return int(s)
    except ValueError:
        _die(f"{name} must be an integer, got: '{s}'")
        return 0  # unreachable, but satisfies type checker


def _parse_size(size_str: str) -> tuple[int, int]:
    """Parse a WxH size string like '32x32' or '16x16'."""
    parts = size_str.lower().split("x")
    if len(parts) != 2:
        _die(f"Size must be WxH (e.g. 32x32), got: '{size_str}'")
    w = _parse_int(parts[0], "width")
    h = _parse_int(parts[1], "height")
    if w < 1 or h < 1:
        _die(f"Size must be positive, got: {w}x{h}")
    return w, h


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

    # export
    p_export = sub.add_parser("export", help="Export PNGs at multiple scales")
    p_export.add_argument("directory", nargs="?", default=".", help="Sprite directory")

    # palette
    p_palette = sub.add_parser("palette", help="Display current palette")
    p_palette.add_argument("directory", nargs="?", default=".", help="Sprite directory")

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
    from gridfab.commands.edit import cmd_row, cmd_rows, cmd_fill, cmd_rect
    from gridfab.commands.render_cmd import cmd_render
    from gridfab.commands.export_cmd import cmd_export, cmd_palette

    cmd = args.command

    if cmd == "init":
        w, h = _parse_size(args.size)
        cmd_init(Path(args.directory), w, h)

    elif cmd in ("render", "show"):
        cmd_render(Path(args.directory))

    elif cmd == "row":
        cmd_row(Path(args.dir), args.row_num, args.values)

    elif cmd == "rows":
        cmd_rows(Path(args.dir), args.start, args.end, args.values)

    elif cmd == "fill":
        cmd_fill(Path(args.dir), args.row, args.col_start, args.col_end, args.color)

    elif cmd == "rect":
        cmd_rect(Path(args.dir), args.r0, args.c0, args.r1, args.c1, args.color)

    elif cmd == "export":
        cmd_export(Path(args.directory))

    elif cmd == "palette":
        cmd_palette(Path(args.directory))
