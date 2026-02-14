# GridFab

![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)
![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Status: Pre-Alpha](https://img.shields.io/badge/Status-Pre--Alpha-orange)
[![Build & Release](https://github.com/azrazalea/gridfab/actions/workflows/release.yml/badge.svg)](https://github.com/azrazalea/gridfab/actions/workflows/release.yml)

<p align="center">
  <img src="assets/logo/output_8x.png" alt="GridFab logo" width="256">
</p>

**Pixel art editor where AI and humans edit the same sprite in real time — because the art is plain text.**

GridFab is an open-source pixel art editor built around a radical idea: the artwork is stored as plain text files that both humans and LLMs can read and edit directly. It has two interfaces operating on the same files simultaneously:

1. **A GUI editor** (tkinter) for humans to paint, preview, and refine pixel art visually
2. **A CLI tool** for LLMs (via Claude Code, agentic coding tools, or scripts) to read the grid as text, reason about spatial layout, and make structured edits

The text-based format (`grid.txt` + `palette.txt`) is the canonical representation of the artwork. No other pixel art tool gives AI agents direct read/write access to a human-readable art format while a human simultaneously edits the same files in a GUI.

## Why This Exists

I'm a hobby game dev making [Veil of Ages](https://github.com/azrazalea/veil-of-ages) in Godot. I wanted an LLM to help me create sprites, but no art tool speaks text. So I built one.

## Quick Start

```bash
pip install gridfab
gridfab init --size 32x32
gridfab-gui .
# Start painting! Or ask your AI to edit grid.txt
```

## The "Aha" Demo

The human-AI workflow looks like this:

1. **Human:** "Hey Claude, I need a red potion bottle sprite"
2. **Claude** reads grid.txt, writes palette entries, edits rows via CLI
3. **Human** hits Refresh in the GUI — sees the sprite instantly
4. **Human:** "Make the liquid darker and add a cork"
5. **Claude** edits grid.txt again
6. Final sprite in under 2 minutes

The grid.txt is readable by both parties:

```
. . . . . . . B B B B . . . . .
. . . . . . B R R R R B . . . .
. . . . . B R R R R R R B . . .
. . . . . B R R R R R R B . . .
. . . . . . B B B B B B . . . .
```

## File Format

### grid.txt

One row per line, space-separated values. Each value is:
- `.` — transparent
- A 1-2 character palette alias (e.g. `R`, `SK`, `DG`)
- An inline `#RRGGBB` hex color

### palette.txt

One alias per line as `ALIAS=#RRGGBB`. Lines starting with `#` are comments.

```
# Character colors
R=#CC3333
SK=#FFCCAA
HR=#663311
```

### gridfab.json

Optional config per sprite directory:

```json
{
  "grid": { "width": 32, "height": 32 },
  "export": { "scales": [1, 4, 8, 16] }
}
```

## CLI Reference

```bash
gridfab init [--size WxH] [dir]              # Create new sprite
gridfab render [dir]                          # Preview with checkerboard bg
gridfab export [dir]                          # Export PNGs at multiple scales
gridfab palette [dir]                         # Show palette colors
gridfab pixel <row> <col> <color>            # Set a single pixel
gridfab pixels <r,c,color> [...]             # Batch pixel placement
gridfab row <n> <v0 v1 ...> [--dir DIR]      # Replace a row
gridfab rows <start> <end> <values...>        # Replace row range
gridfab fill <row> <c0> <c1> <color>          # Fill horizontal span
gridfab rect <r0> <c0> <r1> <c1> <color>      # Fill rectangle
gridfab clear [dir]                           # Reset grid to transparent
gridfab icon [dir]                            # Export .ico and .icns icons
gridfab atlas <output> [sprites...] [opts]    # Pack sprites into spritesheet
```

## GUI

```bash
gridfab-gui [directory]
```

- Left-click to paint, right-click to erase
- Palette sidebar with color buttons
- Ctrl+Z / Ctrl+Y for undo/redo
- Ctrl+S to save
- Save, Render, Refresh, Clear, and New buttons

## Features

- Configurable grid sizes (8x8, 16x16, 32x32, 64x64, or any WxH)
- Export at multiple scales (1x, 4x, 8x, 16x) with true transparency
- Preview rendering with checkerboard background
- Undo/redo in GUI (512-step history)
- 1-2 character palette aliases with case-insensitive collision detection
- Pixel-level editing commands (`pixel`, `pixels`, `fill`, `rect`, `row`, `rows`)
- Icon export (`.ico` and `.icns`) from square grids
- Atlas/spritesheet packing with multi-tile support, stable ordering, and JSON index
- Auto-repair for malformed grid.txt files

### Planned

- Animation support (multi-frame sprites, spritesheets, GIF export)
- AI workflow commands (describe, diff, flip, rotate, outline, patterns)
- Project management (multi-sprite projects, shared palettes)
- Game engine export (Godot SpriteFrames, Unity .meta)
- Layer support

## For AI / LLM Users

GridFab is designed for AI-assisted pixel art workflows. The CLI is the API:

```bash
# An LLM can read the grid as plain text
cat grid.txt

# Make structured edits
gridfab pixel 5 13 DK
gridfab pixels 5,13,DK 5,14,WB 6,12,DK
gridfab rect 10 10 20 20 SK
gridfab fill 5 0 31 R

# Check palette
gridfab palette
```

Every editing operation is available via CLI. The text format means LLMs can reason about spatial layout, color distribution, and composition without vision capabilities.

### Claude Code Skill

If you use [Claude Code](https://claude.ai/claude-code), install the GridFab skill to give Claude built-in knowledge of how to create and edit sprites:

```bash
# Copy the skill to your user-level skills directory
cp -r skills/gridfab-create ~/.claude/skills/gridfab-create
```

Once installed, Claude will automatically know how to use GridFab's CLI when you ask it to create or edit pixel art.

## Installation

### From PyPI

```bash
pip install gridfab
```

### From Source

```bash
git clone https://github.com/azrazalea/gridfab.git
cd gridfab
pip install -e .
```

### Requirements

- Python 3.10+
- Pillow (image rendering)
- tkinter (GUI, included with Python)

## Project Structure

```
gridfab/
  src/gridfab/          # Python package
    cli.py              # CLI entry point
    gui.py              # tkinter GUI
    core/               # Grid, Palette data structures
    render/             # Preview and export rendering
    commands/           # CLI command implementations
  tools/                # Standalone utility scripts
  examples/             # Example sprites
  tests/                # Test suite
```

## Documentation

- [INSTRUCTIONS.md](INSTRUCTIONS.md) — Full user manual: GUI guide, CLI reference, config options, suggested LLM prompt
- [CHANGELOG.md](CHANGELOG.md) — Version history
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor Covenant Code of Conduct
- [GRIDFAB_PROJECT_SPEC.md](GRIDFAB_PROJECT_SPEC.md) — Full project roadmap and specification

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and [GRIDFAB_PROJECT_SPEC.md](GRIDFAB_PROJECT_SPEC.md) for the full roadmap.

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE.md) (AGPL-3.0).
