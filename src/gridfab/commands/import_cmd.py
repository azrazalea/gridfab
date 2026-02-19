"""The 'import' command: convert images into grid.txt + palette.txt."""

import json
from pathlib import Path

from PIL import Image

from gridfab.core.grid import _pad_cell


def generate_alias_sequence():
    """Yield alias strings: A-Z, 0-9, AA-ZZ (712 total).

    Uses uppercase only to avoid case-insensitive collisions.
    """
    # Single uppercase letters
    for c in range(ord("A"), ord("Z") + 1):
        yield chr(c)
    # Single digits
    for d in range(10):
        yield str(d)
    # Two-char uppercase
    for c1 in range(ord("A"), ord("Z") + 1):
        for c2 in range(ord("A"), ord("Z") + 1):
            yield chr(c1) + chr(c2)


def image_to_grid_and_palette(
    pil_image: Image.Image,
    alpha_threshold: int = 128,
    existing_colors: dict[str, str] | None = None,
) -> tuple[list[list[str]], dict[str, str]]:
    """Convert a PIL Image to grid data and palette entries.

    Args:
        pil_image: PIL Image (any mode — converted to RGBA internally).
        alpha_threshold: Pixels with alpha < this value become transparent.
        existing_colors: Optional dict mapping hex color → alias to reuse.

    Returns:
        (grid_data, palette_entries) where grid_data is list[list[str]]
        and palette_entries is dict[alias, hex_color].
    """
    # Normalize to RGBA
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    width, height = pil_image.size

    # color_to_alias: "#RRGGBB" → alias
    color_to_alias: dict[str, str] = {}
    if existing_colors:
        for hex_color, alias in existing_colors.items():
            color_to_alias[hex_color.upper()] = alias

    alias_gen = generate_alias_sequence()
    # Skip aliases already used by existing_colors
    used_aliases = set(color_to_alias.values()) if existing_colors else set()

    grid_data: list[list[str]] = []
    for y in range(height):
        row: list[str] = []
        for x in range(width):
            r, g, b, a = pil_image.getpixel((x, y))
            if a < alpha_threshold:
                row.append(".")
            else:
                hex_color = f"#{r:02X}{g:02X}{b:02X}"
                if hex_color in color_to_alias:
                    row.append(color_to_alias[hex_color])
                else:
                    # Generate next unused alias
                    alias = next(alias_gen)
                    while alias in used_aliases:
                        alias = next(alias_gen)
                    used_aliases.add(alias)
                    color_to_alias[hex_color] = alias
                    row.append(alias)
        grid_data.append(row)

    # Build palette_entries: alias → hex_color
    palette_entries: dict[str, str] = {}
    for hex_color, alias in color_to_alias.items():
        palette_entries[alias] = hex_color

    return grid_data, palette_entries


def save_sprite(
    grid_data: list[list[str]],
    palette_entries: dict[str, str],
    directory: Path,
    width: int,
    height: int,
    metadata: dict | None = None,
) -> None:
    """Write grid.txt, palette.txt, gridfab.json, and optional metadata.json."""
    directory.mkdir(parents=True, exist_ok=True)

    # grid.txt
    with open(directory / "grid.txt", "w", newline="\n") as f:
        for row in grid_data:
            f.write(" ".join(_pad_cell(v) for v in row) + "\n")

    # palette.txt
    with open(directory / "palette.txt", "w", newline="\n") as f:
        f.write("# Palette: ALIAS=#RRGGBB\n")
        for alias, color in sorted(palette_entries.items()):
            f.write(f"{alias}={color}\n")

    # gridfab.json
    config = {
        "grid": {"width": width, "height": height},
        "export": {"scales": [1, 4, 8, 16]},
    }
    with open(directory / "gridfab.json", "w", newline="\n") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    # metadata.json (optional)
    if metadata:
        with open(directory / "metadata.json", "w", newline="\n") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")


def import_single(
    image_path: Path,
    output_dir: Path,
    alpha_threshold: int = 128,
) -> None:
    """Import a single PNG image into a sprite directory (mode 1)."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if (output_dir / "grid.txt").exists():
        raise FileExistsError(
            f"{output_dir / 'grid.txt'} already exists — "
            f"delete it first or choose a different output directory"
        )

    img = Image.open(str(image_path))
    grid_data, palette_entries = image_to_grid_and_palette(img, alpha_threshold)
    w, h = img.size
    save_sprite(grid_data, palette_entries, output_dir, w, h)
    print(f"Imported {image_path.name} → {output_dir} ({w}x{h}, {len(palette_entries)} colors)")


def import_tilesheet(
    image_path: Path,
    tile_w: int,
    tile_h: int,
    output_dir: Path,
    index: Path | None = None,
    alpha_threshold: int = 128,
) -> None:
    """Import a tilesheet PNG, splitting into individual sprite directories (mode 3)."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = Image.open(str(image_path))
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    sheet_w, sheet_h = img.size
    if sheet_w % tile_w != 0 or sheet_h % tile_h != 0:
        raise ValueError(
            f"Image size {sheet_w}x{sheet_h} is not divisible by "
            f"tile size {tile_w}x{tile_h}"
        )

    cols = sheet_w // tile_w
    rows = sheet_h // tile_h

    # Load index if provided
    index_data = None
    if index:
        with open(index) as f:
            index_data = json.load(f)

    # Build reverse lookup from index: (col, row) → sprite info
    pos_to_sprite: dict[tuple[int, int], tuple[str, dict]] = {}
    if index_data:
        for name, info in index_data.get("sprites", {}).items():
            pos = (info["col"], info["row"])
            pos_to_sprite[pos] = (name, info)

    # First pass: collect all tile images and detect empty tiles
    tiles: list[tuple[int, int, Image.Image]] = []  # (col, row, tile_img)
    for row in range(rows):
        for col in range(cols):
            x0 = col * tile_w
            y0 = row * tile_h
            tile_img = img.crop((x0, y0, x0 + tile_w, y0 + tile_h))

            # Check if tile is fully transparent
            if _is_empty(tile_img, alpha_threshold):
                continue

            tiles.append((col, row, tile_img))

    if not tiles:
        print(f"No non-empty tiles found in {image_path.name}")
        return

    # Build shared palette across all tiles
    shared_colors: dict[str, str] = {}  # hex → alias
    alias_gen = generate_alias_sequence()
    used_aliases: set[str] = set()

    for _, _, tile_img in tiles:
        for y in range(tile_h):
            for x in range(tile_w):
                r, g, b, a = tile_img.getpixel((x, y))
                if a < alpha_threshold:
                    continue
                hex_color = f"#{r:02X}{g:02X}{b:02X}"
                if hex_color not in shared_colors:
                    alias = next(alias_gen)
                    while alias in used_aliases:
                        alias = next(alias_gen)
                    used_aliases.add(alias)
                    shared_colors[hex_color] = alias

    # Second pass: convert each tile using the shared palette
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for col, row, tile_img in tiles:
        grid_data, _ = image_to_grid_and_palette(
            tile_img, alpha_threshold, existing_colors=shared_colors,
        )

        # Build full palette_entries from shared colors
        palette_entries = {alias: hex_c for hex_c, alias in shared_colors.items()}

        # Determine sprite name and metadata
        pos = (col, row)
        metadata = None
        if pos in pos_to_sprite:
            name, info = pos_to_sprite[pos]
            meta = {}
            for field in ("description", "tags", "tile_type"):
                if field in info:
                    meta[field] = info[field]
            if any(meta.values()):
                metadata = meta
        else:
            name = f"tile_{col}_{row}"

        sprite_dir = output_dir / name
        save_sprite(grid_data, palette_entries, sprite_dir, tile_w, tile_h,
                     metadata=metadata)
        count += 1

    print(
        f"Imported {count} tile(s) from {image_path.name} → {output_dir} "
        f"({tile_w}x{tile_h} tiles, {len(shared_colors)} colors)"
    )


def _is_empty(img: Image.Image, alpha_threshold: int) -> bool:
    """Check if every pixel in the image is below the alpha threshold."""
    if img.mode != "RGBA":
        return False
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y))[3] >= alpha_threshold:
                return False
    return True


def cmd_import(
    image: Path,
    output: Path | None = None,
    tile_size: tuple[int, int] | None = None,
    tile_pos: tuple[int, int] | None = None,
    index: Path | None = None,
    alpha_threshold: int = 128,
) -> None:
    """Dispatch to the appropriate import mode.

    Mode detection:
    - No tile_size → single image (mode 1)
    - tile_size + tile_pos → single tile extraction (mode 2)
    - tile_size only → whole tilesheet (mode 3a)
    - tile_size + index → whole tilesheet with naming (mode 3b)
    """
    if not image.exists():
        raise FileNotFoundError(f"Image not found: {image}")

    # Default output: derive from image filename
    if output is None:
        output = image.parent / image.stem

    if tile_size is None:
        # Mode 1: single image
        import_single(image, output, alpha_threshold)
    elif tile_pos is not None:
        # Mode 2: extract single tile
        tile_w, tile_h = tile_size
        col, row = tile_pos

        img = Image.open(str(image))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        sheet_w, sheet_h = img.size
        max_col = sheet_w // tile_w
        max_row = sheet_h // tile_h

        if col >= max_col or row >= max_row:
            raise ValueError(
                f"Tile position ({col},{row}) is out of bounds — "
                f"sheet has {max_col}x{max_row} tiles "
                f"(image {sheet_w}x{sheet_h}, tile size {tile_w}x{tile_h})"
            )

        x0 = col * tile_w
        y0 = row * tile_h
        tile_img = img.crop((x0, y0, x0 + tile_w, y0 + tile_h))

        # Save as a temporary image and use import_single
        grid_data, palette_entries = image_to_grid_and_palette(
            tile_img, alpha_threshold,
        )

        if (output / "grid.txt").exists():
            raise FileExistsError(
                f"{output / 'grid.txt'} already exists — "
                f"delete it first or choose a different output directory"
            )

        save_sprite(grid_data, palette_entries, output, tile_w, tile_h)
        print(
            f"Imported tile ({col},{row}) from {image.name} → {output} "
            f"({tile_w}x{tile_h}, {len(palette_entries)} colors)"
        )
    else:
        # Mode 3: whole tilesheet
        tile_w, tile_h = tile_size
        import_tilesheet(image, tile_w, tile_h, output, index, alpha_threshold)
