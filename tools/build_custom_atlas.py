#!/usr/bin/env python3
"""Build a tile atlas from a directory of PNG sprites.

Finds all .png files in subdirectories and packs them into:
  - <output_dir>/atlas.png (NxN tile grid, no separation/margin)
  - <output_dir>/atlas_index.json (name -> {row, col, x, y})

Usage:
    python tools/build_custom_atlas.py [--input-dir DIR] [--tile-size N] [--output-dir DIR]
"""

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image


def find_assets(input_dir: Path) -> list[tuple[str, Path]]:
    """Find all PNGs in subdirectories of the input directory."""
    assets = []
    for subdir in sorted(input_dir.iterdir()):
        if not subdir.is_dir():
            continue
        for png in sorted(subdir.glob("*.png")):
            assets.append((subdir.name, png))
    return assets


def build_atlas(
    input_dir: Path,
    output_dir: Path,
    tile_size: int = 32,
) -> None:
    """Build an atlas PNG and JSON index from a directory of tile PNGs."""
    assets = find_assets(input_dir)
    if not assets:
        print(f"No assets found in {input_dir}/*/")
        sys.exit(1)

    print(f"Found {len(assets)} asset(s):")
    for name, path in assets:
        print(f"  {name}: {path.name}")

    # Calculate grid size (roughly square)
    cols = math.ceil(math.sqrt(len(assets)))
    rows = math.ceil(len(assets) / cols)

    atlas = Image.new(
        "RGBA", (cols * tile_size, rows * tile_size), (0, 0, 0, 0)
    )
    index = {}

    for i, (name, path) in enumerate(assets):
        r = i // cols
        c = i % cols
        tile = Image.open(path)
        if tile.size != (tile_size, tile_size):
            print(
                f"  WARNING: {path} is {tile.size}, expected "
                f"{tile_size}x{tile_size}"
            )
        atlas.paste(tile, (c * tile_size, r * tile_size))
        index[name] = {
            "row": r,
            "col": c,
            "x": c * tile_size,
            "y": r * tile_size,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    atlas_path = output_dir / "atlas.png"
    index_path = output_dir / "atlas_index.json"

    atlas.save(str(atlas_path))
    print(
        f"\nAtlas: {atlas_path} "
        f"({cols * tile_size}x{rows * tile_size}, {cols}x{rows} tiles)"
    )

    with open(index_path, "w", newline="\n") as f:
        json.dump(index, f, indent=2)
        f.write("\n")
    print(f"Index: {index_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a tile atlas from a directory of PNG sprites",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("assets/custom"),
        help="Directory containing subdirectories with PNGs (default: assets/custom)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for atlas.png and atlas_index.json (default: same as input-dir)",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=32,
        help="Tile size in pixels (default: 32)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or args.input_dir
    build_atlas(args.input_dir, output_dir, args.tile_size)


if __name__ == "__main__":
    main()
