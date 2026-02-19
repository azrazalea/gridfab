"""The 'export' command: export PNGs, display palette, and rename aliases."""

import json
from pathlib import Path

from gridfab.core.grid import Grid, load_config, _pad_cell
from gridfab.core.palette import Palette
from gridfab.core.animation import resolve_grid_path, discover_frames, frame_path
from gridfab.render.export import render_export


def cmd_export(directory: Path, frame: int | None = None) -> None:
    """Export final PNGs at configured scales with true transparency."""
    grid_path = resolve_grid_path(directory, frame)
    palette_path = directory / "palette.txt"
    grid = Grid.load(grid_path, palette_path=palette_path)
    palette = Palette.load(palette_path)
    colors = palette.resolve_grid(grid.data)

    config = load_config(directory)
    scales = config.get("export", {}).get("scales", [1, 4, 8, 16])

    for scale in scales:
        img = render_export(colors, grid.width, grid.height, scale)
        if scale == 1:
            name = "output.png"
        else:
            name = f"output_{scale}x.png"
        output = directory / name
        img.save(str(output))
        w = grid.width * scale
        h = grid.height * scale
        print(f"Exported {output} ({w}x{h})")


def cmd_palette(directory: Path) -> None:
    """Display the current palette."""
    palette_path = directory / "palette.txt"
    if not palette_path.exists():
        raise FileNotFoundError(
            f"No palette.txt found in {directory} — run 'gridfab init' first"
        )

    palette = Palette.load(palette_path)
    entries = palette.colors

    if not entries:
        print("Palette is empty. Add entries to palette.txt: ALIAS=#RRGGBB")
        return

    print("Current palette:")
    for alias, color in sorted(entries.items()):
        print(f"  {alias} = {color if color else 'transparent'}")


def cmd_palette_rename(directory: Path, old_alias: str, new_alias: str) -> None:
    """Rename a palette alias across palette.txt and all grid files."""
    palette_path = directory / "palette.txt"
    if not palette_path.exists():
        raise FileNotFoundError(
            f"No palette.txt found in {directory} — run 'gridfab init' first"
        )

    if old_alias == new_alias:
        raise ValueError(f"new alias '{new_alias}' is same as old")

    # Validate new alias
    Palette._validate_alias(new_alias)

    palette = Palette.load(palette_path)

    if old_alias not in palette.entries:
        raise ValueError(
            f"alias '{old_alias}' not found in palette"
        )

    # Check case-insensitive collision with other existing aliases
    for existing in palette.entries:
        if existing == old_alias or existing == ".":
            continue
        if existing.lower() == new_alias.lower():
            raise ValueError(
                f"alias '{new_alias}' conflicts with existing alias '{existing}' "
                f"(case-insensitive duplicates not allowed)"
            )

    # Rename in palette
    color = palette.entries.pop(old_alias)
    palette.entries[new_alias] = color
    palette.save(palette_path)

    # Collect all grid files to update
    grid_files: list[Path] = []
    grid_txt = directory / "grid.txt"
    if grid_txt.exists():
        grid_files.append(grid_txt)
    frames = discover_frames(directory)
    for f in frames:
        grid_files.append(frame_path(directory, f))

    # Replace old alias with new alias in all grid files
    updated_count = 0
    for gf in grid_files:
        content = gf.read_text()
        lines = content.rstrip("\n").split("\n")
        changed = False
        new_lines = []
        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue
            cells = line.split()
            new_cells = []
            for cell in cells:
                # Unpad, check, re-pad
                from gridfab.core.grid import _unpad_cell
                raw = _unpad_cell(cell)
                if raw == old_alias:
                    raw = new_alias
                    changed = True
                new_cells.append(_pad_cell(raw))
            new_lines.append(" ".join(new_cells))
        if changed:
            with open(gf, "w", newline="\n") as f:
                f.write("\n".join(new_lines) + "\n")
            updated_count += 1

    print(f"Renamed '{old_alias}' → '{new_alias}' in palette + {updated_count} grid file(s).")
