"""The 'atlas' command: pack multiple sprites into a spritesheet."""

import json
import math
from pathlib import Path

from PIL import Image

from gridfab.core.grid import Grid
from gridfab.core.palette import Palette
from gridfab.core.animation import is_animated
from gridfab.render.export import render_export


def _is_valid_sprite_dir(p: Path) -> bool:
    """Check if a directory is a valid sprite dir (static or animated with sheets)."""
    if (p / "grid.txt").exists():
        return True
    if is_animated(p) and list(p.glob("*_sheet.png")):
        return True
    return False


def _validate_sprite_dir(p: Path) -> None:
    """Validate a sprite directory, raising on invalid dirs with helpful messages."""
    if (p / "grid.txt").exists():
        return
    if is_animated(p):
        if list(p.glob("*_sheet.png")):
            return
        raise ValueError(
            f"{p} has animation frames but no *_sheet.png — "
            f"run 'gridfab anim sheets' first, or provide grid.txt for a static sprite"
        )
    raise ValueError(f"No grid.txt or animation sheets in {p} — not a sprite directory")


def resolve_sprite_dirs(
    positional: list[str],
    include: list[str] | None,
    exclude: list[str] | None,
) -> list[Path]:
    """Resolve sprite directories from positional args or glob patterns.

    Positional args and --include/--exclude are mutually exclusive.
    Returns validated paths (static dirs with grid.txt, or animated dirs with sheets).
    """
    has_positional = len(positional) > 0
    has_globs = bool(include)

    if has_positional and has_globs:
        raise ValueError(
            "Cannot combine positional sprite directories with --include/--exclude"
        )

    if has_positional:
        dirs = []
        for p_str in positional:
            p = Path(p_str)
            if not p.is_dir():
                raise FileNotFoundError(f"Not a directory: {p}")
            _validate_sprite_dir(p)
            dirs.append(p)
        return dirs

    # Glob mode
    if not include:
        raise ValueError(
            "No sprite directories provided — "
            "pass directories as arguments or use --include GLOB"
        )

    matched: set[Path] = set()
    for pattern in include:
        # If the pattern is absolute, use Path.glob via parent
        pat_path = Path(pattern)
        parent = pat_path.parent
        glob_part = pat_path.name
        if parent.exists():
            for match in parent.glob(glob_part):
                if match.is_dir() and _is_valid_sprite_dir(match):
                    matched.add(match.resolve())

    # Apply excludes
    if exclude:
        excluded: set[Path] = set()
        for pattern in exclude:
            pat_path = Path(pattern)
            parent = pat_path.parent
            glob_part = pat_path.name
            if parent.exists():
                for match in parent.glob(glob_part):
                    excluded.add(match.resolve())
        matched -= excluded

    if not matched:
        raise ValueError(
            "No sprite directories provided — "
            "pass directories as arguments or use --include GLOB"
        )

    return sorted(matched, key=lambda p: p.name)


def load_existing_index(
    output_dir: Path, *, index_name: str = "index.json"
) -> dict | None:
    """Load an existing index from the output directory, or None."""
    index_path = output_dir / index_name
    if not index_path.exists():
        return None
    with open(index_path) as f:
        return json.load(f)


def compute_placement(
    sprites: list[tuple[str, int, int]],  # (name, tiles_x, tiles_y)
    existing_index: dict | None,
    columns: int,
    reorder: bool,
) -> list[tuple[str, int, int]]:  # (name, row, col)
    """Compute tile placements for sprites using an occupancy grid.

    Existing sprites (from index) keep their positions unless reorder=True.
    New sprites are placed by scanning for the first available contiguous block.
    """
    # Build occupancy grid (grows vertically as needed)
    # Start with enough rows for existing + new sprites
    max_tiles = sum(tx * ty for _, tx, ty in sprites)
    initial_rows = max(1, math.ceil(max_tiles / columns) + 4)
    occupancy = [[False] * columns for _ in range(initial_rows)]

    def ensure_rows(needed: int) -> None:
        while len(occupancy) < needed:
            occupancy.append([False] * columns)

    def fits(row: int, col: int, tx: int, ty: int) -> bool:
        ensure_rows(row + ty)
        if col + tx > columns:
            return False
        for r in range(row, row + ty):
            for c in range(col, col + tx):
                if occupancy[r][c]:
                    return False
        return True

    def mark(row: int, col: int, tx: int, ty: int) -> None:
        ensure_rows(row + ty)
        for r in range(row, row + ty):
            for c in range(col, col + tx):
                occupancy[r][c] = True

    def find_first_fit(tx: int, ty: int) -> tuple[int, int]:
        row = 0
        while True:
            ensure_rows(row + ty)
            for col in range(columns):
                if fits(row, col, tx, ty):
                    return row, col
            row += 1

    result: list[tuple[str, int, int]] = []
    new_sprites: list[tuple[str, int, int]] = []  # (name, tiles_x, tiles_y)

    # Phase 1: place existing sprites (from index)
    if existing_index and not reorder:
        existing_sprites = existing_index.get("sprites", {})
        for name, tx, ty in sprites:
            if name in existing_sprites:
                info = existing_sprites[name]
                r, c = info["row"], info["col"]
                ensure_rows(r + ty)
                mark(r, c, tx, ty)
                result.append((name, r, c))
            else:
                new_sprites.append((name, tx, ty))
    else:
        new_sprites = list(sprites)

    # Phase 2: place new sprites by scanning for first fit
    for name, tx, ty in new_sprites:
        r, c = find_first_fit(tx, ty)
        mark(r, c, tx, ty)
        result.append((name, r, c))

    return result


def _collect_animated_entries(
    d: Path, tw: int, th: int, seen_names: dict[str, Path],
) -> list[tuple[str, int, int, Image.Image, dict]]:
    """Collect atlas entries from an animated sprite directory.

    Each *_sheet.png becomes a separate entry named '{dir_name}/{anim_name}'.
    Returns list of (name, tiles_x, tiles_y, image, anim_meta).
    """
    entries = []
    for sheet_png in sorted(d.glob("*_sheet.png")):
        anim_name = sheet_png.stem.replace("_sheet", "")
        entry_name = f"{d.name}/{anim_name}"

        if entry_name in seen_names:
            raise ValueError(
                f"Duplicate sprite name '{entry_name}': {seen_names[entry_name]} and {d}"
            )
        seen_names[entry_name] = d

        img = Image.open(str(sheet_png))
        if img.width % tw != 0 or img.height % th != 0:
            print(
                f"WARNING: Skipping '{entry_name}': sheet {img.width}x{img.height} "
                f"is not a multiple of tile size {tw}x{th}"
            )
            continue

        tiles_x = img.width // tw
        tiles_y = img.height // th

        # Load sheet metadata if available
        sheet_json = sheet_png.with_suffix("").with_name(
            sheet_png.stem + ".json"
        )
        anim_meta = {}
        if sheet_json.exists():
            with open(sheet_json) as f:
                meta = json.load(f)
            anims = meta.get("animations", {})
            if anim_name in anims:
                anim_data = anims[anim_name]
                frame_count = len(anim_data.get("frames", []))
                # Compute fps from first frame's duration
                frames_list = anim_data.get("frames", [])
                if frames_list and "duration" in frames_list[0]:
                    fps = round(1000 / frames_list[0]["duration"])
                else:
                    fps = 8
                loop = anim_data.get("loop", True)
                anim_meta = {
                    "frame_count": frame_count,
                    "fps": fps,
                    "loop": loop,
                }

        entries.append((entry_name, tiles_x, tiles_y, img, anim_meta))
    return entries


def cmd_atlas(
    output_dir: Path,
    sprite_dirs: list[Path],
    *,
    tile_size: tuple[int, int] | None = None,
    columns: int | None = None,
    reorder: bool = False,
    atlas_name: str = "atlas.png",
    index_name: str = "index.json",
) -> None:
    """Build a sprite atlas from multiple sprite directories."""
    # Classify directories as static or animated
    static_dirs = []
    animated_dirs = []
    for d in sprite_dirs:
        if (d / "grid.txt").exists():
            static_dirs.append(d)
        else:
            animated_dirs.append(d)

    # Load static grids
    sprite_data: list[tuple[str, Path, Grid, Palette]] = []
    for d in static_dirs:
        palette_path = d / "palette.txt"
        grid = Grid.load(d / "grid.txt", palette_path=palette_path)
        palette = Palette.load(palette_path)
        sprite_data.append((d.name, d, grid, palette))

    if not sprite_data and not animated_dirs:
        raise ValueError(
            "No sprite directories provided — "
            "pass directories as arguments or use --include GLOB"
        )

    # Load existing index
    existing_index = load_existing_index(output_dir, index_name=index_name)

    # Determine tile size
    if tile_size is None:
        if existing_index and not reorder:
            ts = existing_index["tile_size"]
            tile_size = (ts[0], ts[1])
        elif sprite_data:
            # Auto-detect from first static sprite
            first_grid = sprite_data[0][2]
            tile_size = (first_grid.width, first_grid.height)
        elif animated_dirs:
            # Auto-detect from first animated sheet
            sheets = sorted(animated_dirs[0].glob("*_sheet.png"))
            if sheets:
                img = Image.open(str(sheets[0]))
                # Use image height as tile size (sheets are typically 1 tile tall)
                tile_size = (img.height, img.height)
            else:
                raise ValueError("Cannot auto-detect tile size from animated dirs")
        else:
            raise ValueError("Cannot auto-detect tile size — no sprites found")

    tw, th = tile_size

    # Validate static sprite sizes and compute tile spans
    # Unified entry list: (name, tiles_x, tiles_y, image, anim_meta_or_None)
    all_entries: list[tuple[str, int, int, Image.Image | None, dict | None]] = []
    seen_names: dict[str, Path] = {}

    for name, path, grid, palette in sprite_data:
        if name in seen_names:
            raise ValueError(
                f"Duplicate sprite name '{name}': {seen_names[name]} and {path}"
            )
        seen_names[name] = path

        if grid.width % tw != 0 or grid.height % th != 0:
            print(
                f"WARNING: Skipping '{name}': grid {grid.width}x{grid.height} "
                f"is not a multiple of tile size {tw}x{th}"
            )
            continue

        tiles_x = grid.width // tw
        tiles_y = grid.height // th
        colors = palette.resolve_grid(grid.data)
        img = render_export(colors, grid.width, grid.height, scale=1)
        all_entries.append((name, tiles_x, tiles_y, img, None))

    # Collect animated entries
    for d in animated_dirs:
        anim_entries = _collect_animated_entries(d, tw, th, seen_names)
        all_entries.extend(anim_entries)

    if not all_entries:
        raise ValueError("No valid sprites to pack after filtering")

    # Determine columns — must be at least as wide as the widest entry
    max_entry_width = max(tx for _, tx, ty, _, _ in all_entries)
    if columns is None:
        if existing_index and not reorder:
            columns = existing_index.get("columns", None)
        if columns is None:
            total_tiles = sum(tx * ty for _, tx, ty, _, _ in all_entries)
            columns = math.ceil(math.sqrt(total_tiles))
    columns = max(columns, max_entry_width)

    # Compute placement
    placement_input = [(name, tx, ty) for name, tx, ty, _, _ in all_entries]
    placements = compute_placement(
        placement_input, existing_index, columns, reorder
    )

    # Build placement lookup: name → (row, col)
    placement_map: dict[str, tuple[int, int]] = {}
    for name, row, col in placements:
        placement_map[name] = (row, col)

    # Determine atlas dimensions
    max_row = 0
    max_col = 0
    for name, tx, ty, _, _ in all_entries:
        row, col = placement_map[name]
        max_row = max(max_row, row + ty)
        max_col = max(max_col, col + tx)
    atlas_cols = max(max_col, 1)
    atlas_rows = max(max_row, 1)

    atlas_w = atlas_cols * tw
    atlas_h = atlas_rows * th
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))

    # Paste each entry
    for name, tx, ty, img, _meta in all_entries:
        row, col = placement_map[name]
        atlas.paste(img, (col * tw, row * th))

    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(str(output_dir / atlas_name))

    # Build index — preserve existing semantic fields
    existing_sprites = (
        existing_index.get("sprites", {}) if existing_index else {}
    )
    index: dict = {
        "tile_size": [tw, th],
        "columns": columns,
        "sprites": {},
    }
    new_semantic_count = 0
    for name, tx, ty, _img, anim_meta in all_entries:
        row, col = placement_map[name]
        old = existing_sprites.get(name, {})
        desc = old.get("description", "")
        tags = old.get("tags", [])
        tile_type = old.get("tile_type", "")
        if not desc and not tags and not tile_type:
            new_semantic_count += 1
        entry: dict = {
            "row": row,
            "col": col,
            "tiles_x": tx,
            "tiles_y": ty,
            "description": desc,
            "tags": tags,
            "tile_type": tile_type,
        }
        if anim_meta:
            entry["animated"] = True
            entry["frame_count"] = anim_meta.get("frame_count", 0)
            entry["fps"] = anim_meta.get("fps", 8)
            entry["loop"] = anim_meta.get("loop", True)
        index["sprites"][name] = entry

    with open(output_dir / index_name, "w", newline="\n") as f:
        json.dump(index, f, indent=2)
        f.write("\n")

    print(
        f"Atlas: {output_dir / atlas_name} "
        f"({atlas_w}x{atlas_h}, {atlas_cols}x{atlas_rows} tiles)"
    )
    print(f"Index: {output_dir / index_name} ({len(all_entries)} sprite(s))")
    if new_semantic_count:
        print(
            f"Hint: {new_semantic_count} sprite(s) have empty description/tags/tile_type — "
            f"edit {output_dir / index_name} to fill them in"
        )
