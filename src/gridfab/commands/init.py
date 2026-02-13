"""The 'init' command: create a new sprite directory."""

import json
from pathlib import Path

from gridfab.core.grid import Grid, DEFAULT_WIDTH, DEFAULT_HEIGHT


def cmd_init(directory: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
    """Create a blank grid.txt, starter palette.txt, and gridfab.json in directory."""
    directory.mkdir(parents=True, exist_ok=True)

    grid_path = directory / "grid.txt"
    palette_path = directory / "palette.txt"
    config_path = directory / "gridfab.json"

    if grid_path.exists():
        raise FileExistsError(
            f"{grid_path} already exists — delete it first to reinitialize"
        )

    # Create blank grid
    grid = Grid.blank(width, height)
    grid.save(grid_path)
    print(f"Created {grid_path} ({width}x{height}, all transparent)")

    # Create palette if missing
    if not palette_path.exists():
        with open(palette_path, "w", newline="\n") as f:
            f.write("# Palette: ALIAS=#RRGGBB\n")
            f.write("# 1-2 character aliases. '.' is reserved for transparent.\n")
        print(f"Created {palette_path} (empty starter)")
    else:
        print(f"{palette_path} already exists, keeping it")

    # Create config
    config = {
        "grid": {"width": width, "height": height},
        "export": {"scales": [1, 4, 8, 16]},
    }
    with open(config_path, "w", newline="\n") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"Created {config_path}")
