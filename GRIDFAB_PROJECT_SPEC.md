# GridFab — Human-AI Collaborative Pixel Art Editor

## Project Specification for Claude Code

---

## What This Project Is

GridFab is an open-source pixel art editor built around a radical idea: **the artwork is stored as plain text files that both humans and LLMs can read and edit directly**. It has two interfaces operating on the same files simultaneously:

1. **A GUI editor** (tkinter) for humans to paint, preview, and refine pixel art visually
2. **A CLI tool** for LLMs (via Claude Code, agentic coding tools, or scripts) to read the grid as text, reason about spatial layout, and make structured edits

The text-based format (`grid.txt` + `palette.txt`) is the canonical representation of the artwork. This is what makes it novel — no other pixel art tool gives AI agents direct read/write access to a human-readable art format while a human simultaneously edits the same files in a GUI.

The target audience is **hobby and indie game developers** who use engines like Godot, Unity, and GameMaker. The tool should feel lightweight, fast, and zero-friction — closer to a sharp utility knife than a Swiss Army knife.

## What Already Exists

Two working Python files form the foundation. **Do not rewrite these from scratch** — evolve them. The existing code is clean and functional. Extend it.

### `gridfab.py` — CLI tool
- Commands: `init`, `render`, `row`, `rows`, `fill`, `rect`, `export`, `palette`
- 32×32 grid, 1–2 character palette aliases, `#RRGGBB` inline colors
- Renders preview with checkerboard transparency background
- Exports at 1×, 4×, 8×, 16× with true transparency
- Uses Pillow for image rendering

### `gridfab_gui.py` — GUI editor
- tkinter canvas with 16px cells
- Left-click paint, right-click erase
- Palette sidebar with color buttons
- Save, Render, Refresh buttons
- Reads/writes the same `grid.txt` and `palette.txt` files

### File Format (preserve exactly)

**`grid.txt`** — 32 lines, each with 32 space-separated values. Values are either `.` (transparent), a 1–2 character palette alias, or a `#RRGGBB` hex color.

```
. . . . . . . . . . . . . . R R R R . . . . . . . . . . . . . .
. . . . . . . . . . . . . R R SK SK R R . . . . . . . . . . . .
```

**`palette.txt`** — One alias per line, `ALIAS=#RRGGBB`. Comments with `#`. Aliases are 1–2 extended ASCII characters. `.` and `..` are reserved for transparent.

**Alias rules:**
- 1 or 2 characters long (e.g. `R`, `SK`, `DG`, `h2`)
- Case sensitive: `R` and `r` are different aliases
- No case-insensitive duplicates: you cannot define both `SK` and `sk` (or `Sk` or `sK`) in the same palette — this prevents confusing near-collisions
- Extended ASCII only (printable characters, no Unicode beyond codepoint 255)
- Cannot start with `#` (conflicts with hex colors and comments)
- `.` is reserved for transparent

```
# Character colors
R=#CC3333
SK=#FFCCAA
HR=#663311
DG=#444444
LB=#6699CC
```

This format is sacred. It is the core innovation. Every feature must preserve the property that `grid.txt` is a readable, diffable, grep-able, sed-able text file. The space-separated format means 1-char and 2-char aliases coexist naturally.

---

## Architecture Principles

1. **Text-as-truth.** `grid.txt` IS the artwork. The GUI and CLI are views/editors of this truth. No binary formats, no databases, no hidden state.

2. **File-system sync.** The GUI and CLI coordinate through the filesystem. The GUI has a Refresh button and should also support auto-refresh (file watching). No sockets, no IPC, no shared memory.

3. **Project = directory.** A sprite is a directory containing `grid.txt`, `palette.txt`, and generated outputs. A game project is a parent directory containing sprite subdirectories. No project files, no config databases.

4. **Minimal dependencies.** Core: Python 3.10+ stdlib + Pillow. GUI: tkinter (stdlib). No frameworks, no electron, no web stack. Must package cleanly with PyInstaller.

5. **CLI-first features.** Every editing operation must be available via CLI before (or simultaneously with) GUI. The CLI is the API for LLMs. If an LLM can't do it via CLI, it's a gap.

6. **Fail loudly.** Invalid palette aliases, out-of-range coordinates, malformed grid files — all should produce clear error messages with line numbers and context. LLMs need good error messages to self-correct.

---

## Feature Roadmap

### Phase 1: Polish the Foundation (do this first)

These make the existing tool release-worthy.

#### 1.1 Configurable grid size
Currently hardcoded to 32×32. Support arbitrary sizes specified in a project config.

**Implementation:**
- Add optional `gridfab.json` per sprite directory:
  ```json
  {
    "grid": {
      "width": 32,
      "height": 32
    },
    "export": {
      "scales": [1, 4, 8, 16]
    }
  }
  ```
- If no config exists, default to 32×32 (backward compatible)
- Grid size is set at `init` time and stored in config
- Common presets: 8×8, 16×16, 32×32, 48×48, 64×64
- CLI: `gridfab init --size 16x16` or `gridfab init --size 64x64`
- GUI cell size should auto-scale so the canvas fits reasonably on screen
- Both `gridfab.py` and `gridfab_gui.py` read grid dimensions from the config or infer from the grid.txt file itself

#### 1.2 Undo/redo in the GUI
Essential for any editor. The CLI doesn't need undo (the user can re-run commands or the LLM can fix mistakes).

**Implementation:**
- Maintain a stack of grid snapshots (deep copies of the grid list)
- Cap at ~50 undo steps to limit memory
- Ctrl+Z / Ctrl+Y keybindings
- Each paint stroke (mousedown to mouseup) is one undo unit, not each pixel

#### 1.3 Grid lines toggle
At small cell sizes, grid lines obscure the art. Let users toggle them.

**Implementation:**
- Keyboard shortcut `G` to toggle
- When off, set rectangle outline width to 0
- When on, use the existing thin gray outline
- Remember preference in a local `.gridfab_prefs` or just default to on

#### 1.4 Zoom and pan
The GUI currently has fixed 16px cells. For larger canvases (64×64) this won't fit on screen; for smaller ones (8×8) it's too tiny.

**Implementation:**
- Mouse wheel to zoom (change cell size: 4, 8, 16, 24, 32, 48)
- Middle-click drag to pan (scroll the canvas)
- Fit-to-window button/shortcut
- Status bar showing current zoom level and cursor position (row, col)

#### 1.5 Better color picker
The palette sidebar is functional but minimal. Improve it.

**Implementation:**
- Show the color swatch AND the alias text on each button
- Highlight the currently selected color more visibly (thick border, not just sunken relief)
- Keyboard shortcuts: number keys 1-9 for first 9 palette entries, 0 for transparent
- Tooltip on hover showing the hex value
- Right-click a palette button to copy its hex value

#### 1.6 Cursor preview
Show what color you're about to paint before clicking.

**Implementation:**
- On mouse hover, tint or outline the cell under cursor with the selected color
- Use a semi-transparent overlay or a colored border
- This gives immediate visual feedback of what will happen

#### 1.7 Status bar
Show useful information at the bottom of the window.

**Implementation:**
- Current cursor position: `(row, col)` or `(x, y)` — show both coordinate systems
- Current selected color alias and hex value
- Grid dimensions
- Modified indicator (unsaved changes)
- File path of current grid

#### 1.8 Keyboard shortcuts
Make the editor efficient for experienced users.

| Key | Action |
|-----|--------|
| Ctrl+S | Save |
| Ctrl+Z | Undo |
| Ctrl+Y / Ctrl+Shift+Z | Redo |
| G | Toggle grid lines |
| R | Render preview |
| E | Export |
| 1-9, 0 | Select palette color by position |
| . | Select transparent/eraser |
| F | Fill tool (click to bucket fill) |
| B | Brush tool (default) |
| I | Eyedropper (pick color from canvas) |
| H | Flip horizontal |
| V | Flip vertical |
| [ ] | Zoom in/out |

#### 1.9 Eyedropper tool
Click a pixel to select its color from the palette.

**Implementation:**
- Press `I` or hold Alt while clicking
- If the clicked pixel uses a palette alias, select that alias
- If it uses an inline hex color, show it in the status bar but note it's not in the palette

#### 1.10 Fill (bucket) tool
Flood fill a contiguous region of same-colored pixels.

**Implementation:**
- Standard 4-connected flood fill algorithm
- Press `F` to activate, click to fill
- Should work on both palette aliases AND the resolved colors (so filling a region of "R" that's adjacent to "#CC3333" — if they resolve to the same color — should fill both)
- Actually, keep it simple: fill based on matching the raw grid value (alias), not the resolved color. This is more predictable and LLM-friendly.

#### 1.11 Coordinate-based pixel command

The `row`/`rows` commands require specifying every value in a row, which causes frequent miscounting on large grids. Add a coordinate-based command for placing individual pixels or batches.

**Implementation:**
- `gridfab pixel <row> <col> <color> [--dir DIR]` — Place a single pixel
- `gridfab pixels <row>,<col>,<color> <row>,<col>,<color> ... [--dir DIR]` — Place multiple pixels in one call
- These commands do not require padding with `.` values, eliminating the most common LLM error source
- Validates coordinates are in bounds, color is a valid alias or `#RRGGBB`

#### 1.12 Graceful malformed-file handling

Currently, all CLI commands validate the entire grid.txt before operating. If one row has the wrong number of values, every command fails — including the `row` command that could fix it. This creates a trap where the only escape is editing grid.txt directly.

**Implementation:**
- `gridfab row` should be able to replace a row in a malformed file (validate only the target row's new values, not the whole file)
- Other commands can continue to validate fully
- Show a warning about the malformed state but still execute

#### 1.13 GUI Init/New button

Allow creating new sprites from the GUI without needing the CLI.

**Implementation:**
- File > New or a "New" button that opens a dialog
- Dialog prompts for: directory path, grid size (WxH dropdown or freeform), optional starter palette
- Calls the same init logic as `gridfab init`
- After creation, opens the new sprite in the editor

#### 1.14 Atlas builder integration

The standalone `tools/build_custom_atlas.py` script should be promoted to a proper CLI command and optionally accessible from the GUI.

**Implementation:**
- `gridfab atlas <output> <sprite_dirs...> [--tile-size WxH] [--columns N]` — Pack multiple sprites into a single spritesheet/atlas
- Reads grid.txt + palette.txt from each sprite directory
- Outputs a single PNG atlas and optionally a JSON metadata file with tile positions
- GUI: Tools > Build Atlas menu item that opens a directory picker

---

### Phase 2: Animation Support

This is the single most important feature for game developers. Without animation, the tool is limited to static tiles and icons.

#### 2.1 Frame-based animation model

**Concept:** An animated sprite is a directory containing multiple numbered grid files.

```
player_walk/
  palette.txt          # shared palette for all frames
  gridfab.json         # project config
  frame_001.txt
  frame_002.txt
  frame_003.txt
  frame_004.txt
  animation.json       # animation metadata
```

**`animation.json`:**
```json
{
  "animations": {
    "walk": {
      "frames": [1, 2, 3, 4],
      "fps": 8,
      "loop": true
    },
    "idle": {
      "frames": [1],
      "fps": 1,
      "loop": true
    },
    "attack": {
      "frames": [5, 6, 7, 8],
      "fps": 12,
      "loop": false
    }
  }
}
```

**Alternative (simpler, might be better to start with):** Keep a single `grid.txt` but add a `frames.txt` that lists frame files:

```
player_walk/
  palette.txt
  gridfab.json
  frame_001.txt        # frame 1
  frame_002.txt
  frame_003.txt
  frame_004.txt
  animation.json
```

The `frame_001.txt` numbered approach is the correct format because:
- `grid.txt` being special creates confusion
- Numbered files sort naturally in file explorers
- LLMs can easily iterate: "read frame_001.txt through frame_004.txt"

#### 2.2 GUI animation features

- **Frame strip/timeline** at the bottom of the canvas showing thumbnail previews of all frames
- Click a frame to edit it
- Buttons: Add Frame (duplicate current), Delete Frame, Move Frame Left/Right
- **Onion skinning**: Show previous frame as a translucent overlay while editing current frame. Toggle with `O` key. Adjustable opacity.
- **Play/pause animation preview**: Small preview window or inline playback with adjustable FPS
- **Copy frame / paste frame**: For building animation sequences efficiently

#### 2.3 CLI animation commands

```bash
# Create a new frame (copies current frame as starting point)
gridfab frame add                    # adds next sequential frame
gridfab frame add --from 3           # copies frame 3 as new frame
gridfab frame add --blank            # adds empty frame

# Delete a frame
gridfab frame delete 3

# Edit a specific frame (all existing edit commands work on the active frame)
gridfab frame select 2               # writes active frame to .gridfab_state
gridfab row 5 R R R R ...            # edits frame 2 (from state file)

# Or explicitly target a frame (argument always beats state file)
gridfab row 5 R R R R ... --frame 2

# Animation management
gridfab anim add walk --frames 1,2,3,4 --fps 8 --loop
gridfab anim list
gridfab anim preview walk            # renders animated GIF
gridfab anim delete walk
```

#### 2.4 Spritesheet export

This is what game engines actually consume.

```bash
# Export spritesheet for a specific animation
gridfab export sheet walk

# Export all animations as spritesheets
gridfab export sheets
```

**Output:** A PNG spritesheet (horizontal strip by default) + a JSON metadata file.

**Spritesheet JSON format** (compatible with common engine importers):
```json
{
  "sprite": "player_walk",
  "frame_size": {"w": 32, "h": 32},
  "animations": {
    "walk": {
      "frames": [
        {"x": 0, "y": 0, "w": 32, "h": 32, "duration": 125},
        {"x": 32, "y": 0, "w": 32, "h": 32, "duration": 125},
        {"x": 64, "y": 0, "w": 32, "h": 32, "duration": 125},
        {"x": 96, "y": 0, "w": 32, "h": 32, "duration": 125}
      ],
      "loop": true
    }
  },
  "scale": 1
}
```

**Layout options:**
- `--layout horizontal` (default) — all frames in one row
- `--layout vertical` — all frames in one column  
- `--layout grid --columns 4` — wrap into grid
- `--scale 1,4,8` — export at multiple scales

**Animated GIF export:**
```bash
gridfab export gif walk --scale 4    # animated GIF for previews/sharing
```

---

### Phase 3: Project Management & Workflow

#### 3.1 Multi-sprite projects

A game has dozens to hundreds of sprites. Support browsing and managing them.

**Project structure:**
```
my_game_sprites/
  gridfab_project.json        # project-level config
  characters/
    player/
      palette.txt
      frame_001.txt
      ...
    enemy_slime/
      palette.txt
      frame_001.txt
      ...
  tiles/
    grass/
      grid.txt
      palette.txt
    water/
      grid.txt
      palette.txt
  ui/
    heart_full/
      grid.txt
    heart_empty/
      grid.txt
```

**`gridfab_project.json`:**
```json
{
  "project": {
    "name": "My RPG Sprites",
    "default_size": "32x32",
    "shared_palette": "palette.txt"
  },
  "export": {
    "default_scales": [1, 4],
    "output_dir": "exported"
  }
}
```

**CLI project commands:**
```bash
# Initialize a project
gridfab project init "My RPG Sprites"

# Create a new sprite within the project
gridfab new characters/goblin --size 32x32
gridfab new tiles/lava --size 16x16

# List all sprites in project
gridfab project list

# Batch export everything
gridfab project export

# Batch recolor: swap palette across all sprites using a shared palette
gridfab project recolor --from old_palette.txt --to new_palette.txt
```

**GUI project browser:**
- Left sidebar with directory tree showing all sprites
- Click a sprite to open it in the editor
- Thumbnail previews in the sidebar
- This is a later enhancement — start with single-sprite editing

#### 3.2 Shared palettes

Many game projects need consistent colors across all sprites.

**Implementation:**
- `gridfab_project.json` can specify a `shared_palette` path
- Individual sprites can override with their own `palette.txt`
- Resolution order: sprite's `palette.txt` → project's shared palette → error
- CLI: `gridfab palette merge a.txt b.txt --output combined.txt`
- CLI: `gridfab palette sort` — sort alphabetically or by hue
- CLI: `gridfab palette unused` — list aliases not used in any grid file

#### 3.3 Layers

Layers add significant complexity. Implement as a later phase, and keep the model simple.

**Concept:** Each layer is a separate grid file. Layers composite top-to-bottom.

```
player/
  palette.txt
  layer_outline.txt     # top layer
  layer_color.txt       # middle layer  
  layer_shadow.txt      # bottom layer
  layers.json           # layer order and visibility
```

**`layers.json`:**
```json
{
  "layers": [
    {"name": "outline", "file": "layer_outline.txt", "visible": true},
    {"name": "color", "file": "layer_color.txt", "visible": true},
    {"name": "shadow", "file": "layer_shadow.txt", "visible": true}
  ]
}
```

The render command composites all visible layers. The GUI shows a layer panel. Each layer is independently editable. This is powerful for the AI workflow — an LLM can edit the outline layer without touching the color fill.

**Important: don't implement layers in Phase 1 or 2. The single-grid model is simpler and perfectly functional. Mention layers in the README as a planned feature.**

#### 3.4 Tiling preview

For tile-based games, you need to see how tiles repeat.

**Implementation:**
- GUI toggle: `T` key to show the current sprite tiled 3×3 around itself
- Helps identify seam issues
- CLI: `gridfab render --tiled` generates a 3×3 tiled preview
- Read-only — editing only affects the center tile

---

### Phase 4: AI-Specific Features

These features specifically leverage the text format for LLM workflows.

#### 4.1 Describe command

Let an LLM understand what's in the grid without seeing the image.

```bash
gridfab describe
```

Output:
```
Grid: 32×32, 847/1024 pixels filled (82.7%)
Palette: 8 colors used (R=red, SK=skin, HR=hair, B=black, W=white, G=gray, DR=dark-red, LG=light-gray)
Color distribution: R=234 (22.9%), SK=187 (18.3%), HR=45 (4.4%), ...
Bounding box: rows 2-29, cols 8-24 (content is roughly centered)
Symmetry: approximate vertical symmetry detected (87% match)
```

This gives an LLM spatial context without needing vision capabilities.

#### 4.2 Diff command

Show what changed between two grid files.

```bash
gridfab diff grid_old.txt grid_new.txt
```

Output:
```
Changed pixels: 23
  Row 5: cols 12-15 changed from . to R (filled with red)
  Row 6: cols 11-16 changed from . to R (extended red region)
  Row 10: col 14 changed from R to SK (single pixel color change)
```

This helps LLMs understand the effect of their edits and communicate changes to the human.

#### 4.3 Mirror/flip commands

Common operations for generating directional sprites.

```bash
gridfab flip horizontal              # flip the grid left-right
gridfab flip vertical                # flip the grid top-bottom
gridfab rotate 90                    # rotate 90° clockwise
gridfab rotate 180
gridfab rotate 270
```

For game sprites, you often need east-facing and west-facing versions. The flip command makes this a one-liner.

#### 4.4 Copy/paste regions

Move or duplicate parts of a sprite.

```bash
# Copy a region to a buffer file
gridfab copy 0 0 15 15 --to head.txt

# Paste from buffer at a position  
gridfab paste head.txt --at 0 16

# Shift all non-transparent pixels
gridfab shift right 2
gridfab shift down 1
```

#### 4.5 Outline command

Auto-generate a 1-pixel outline around all non-transparent pixels.

```bash
gridfab outline B                    # add black outline
gridfab outline --remove             # remove outline pixels
```

This is a common pixel art technique and maps perfectly to text-grid operations — check each pixel's 4 neighbors, if any neighbor is transparent and the pixel is not, mark the transparent neighbor for outline.

#### 4.6 Pattern commands

Fill regions with patterns.

```bash
# Checkerboard fill
gridfab pattern checker 0 0 15 15 R SK

# Dithering pattern (50% mix of two colors)
gridfab pattern dither 0 0 15 15 R SK

# Gradient (horizontal, approximate with available palette colors)
gridfab pattern gradient horizontal 0 0 31 31 R DR B
```

#### 4.7 Import from image

Convert an existing PNG/image into the text grid format.

```bash
gridfab import sprite.png --palette palette.txt
```

This maps each pixel to the nearest palette color and writes `grid.txt`. Essential for bringing existing art into the tool.

#### 4.8 Symmetry mode

Edit with automatic mirroring — useful for faces, shields, etc.

```bash
# In CLI, mirror operations automatically
gridfab symmetry on horizontal

# Now every row/fill/rect command is automatically mirrored
gridfab fill 5 0 5 10 R
# Also fills row 5, cols 21-31 with R (mirrored)
```

In the GUI: toggle symmetry mode with `S` key, show a guide line down the center.

---

### Phase 5: Engine Integration & Export

#### 5.1 Godot export

```bash
gridfab export godot --output-dir ./exported/
```

Generates:
- PNG spritesheets at appropriate scales
- `.tres` SpriteFrames resource file (or compatible JSON) with animation data
- Import hints file (`.import`) with `filter=false`, `compress/mode=lossless`

The user drops the exported folder into their Godot project's `res://` and the sprites just work.

#### 5.2 Unity export

```bash
gridfab export unity --output-dir ./exported/
```

Generates:
- PNG spritesheets
- `.meta` file with correct import settings: `filterMode: 0` (Point), `spritePixelsPerUnit: 32`, `spriteMode: 2` (Multiple), and slice data for each frame

#### 5.3 Generic export

```bash
# Individual frames as PNGs
gridfab export frames --scale 4

# Spritesheet with JSON metadata
gridfab export sheet --layout horizontal --scale 1,4

# Animated GIF
gridfab export gif --scale 4 --fps 8

# Animated APNG (better quality than GIF)
gridfab export apng --scale 4 --fps 8
```

---

## Implementation Guidelines

### Code Organization

Restructure into a proper Python package:

```
gridfab/
  __init__.py
  __main__.py           # entry point: python -m gridfab
  cli.py                # CLI argument parsing and command dispatch
  gui.py                # tkinter GUI application
  core/
    __init__.py
    grid.py             # Grid class: load, save, manipulate
    palette.py           # Palette class: load, save, resolve
    project.py           # Project class: multi-sprite management
    animation.py         # Animation: frames, sequences, metadata
  render/
    __init__.py
    preview.py           # Preview rendering (checkerboard bg)
    export.py            # Export rendering (transparent bg)
    spritesheet.py       # Spritesheet assembly
    gif.py               # Animated GIF/APNG export
  commands/
    __init__.py
    init.py
    edit.py              # row, rows, fill, rect, flip, etc.
    render_cmd.py
    export_cmd.py
    project_cmd.py
    animation_cmd.py
    describe.py
    diff.py
  utils.py               # Color conversion, validation helpers

pyproject.toml
README.md
LICENSE                  # MIT
```

### The Grid class

The central data structure. Everything flows through this.

```python
class Grid:
    def __init__(self, width: int, height: int, data: list[list[str]]):
        self.width = width
        self.height = height
        self.data = data  # list of rows, each row is list of string values
    
    @classmethod
    def load(cls, path: Path) -> "Grid": ...
    
    @classmethod
    def blank(cls, width: int, height: int) -> "Grid": ...
    
    def save(self, path: Path) -> None: ...
    
    def get(self, row: int, col: int) -> str: ...
    def set(self, row: int, col: int, value: str) -> None: ...
    
    def fill_rect(self, r0: int, c0: int, r1: int, c1: int, value: str) -> None: ...
    def fill_row(self, row: int, col_start: int, col_end: int, value: str) -> None: ...
    def flood_fill(self, row: int, col: int, value: str) -> None: ...
    
    def flip_horizontal(self) -> None: ...
    def flip_vertical(self) -> None: ...
    def rotate_90(self) -> None: ...  # Note: changes dimensions if not square
    
    def copy_region(self, r0: int, c0: int, r1: int, c1: int) -> "Grid": ...
    def paste(self, other: "Grid", at_row: int, at_col: int) -> None: ...
    
    def shift(self, direction: str, amount: int) -> None: ...
    
    def add_outline(self, color: str) -> None: ...
    
    def describe(self, palette: "Palette") -> dict: ...
    def diff(self, other: "Grid") -> list[Change]: ...
    
    def snapshot(self) -> list[list[str]]: ...  # deep copy for undo
    def restore(self, snapshot: list[list[str]]) -> None: ...
```

### The Palette class

```python
class Palette:
    TRANSPARENT = "."
    
    def __init__(self, entries: dict[str, str | None]):
        # entries maps alias -> hex color or None (transparent)
        self.entries = entries
    
    @classmethod
    def load(cls, path: Path) -> "Palette":
        # Must validate: no case-insensitive duplicates
        # e.g. if "SK" exists, reject "sk", "Sk", "sK"
        ...
    
    def save(self, path: Path) -> None: ...
    
    def resolve(self, value: str) -> str | None: ...  # alias -> hex or None
    
    def validate_alias(self, alias: str) -> None:
        """Validate alias rules. Raise on violation.
        - 1-2 chars long
        - Extended ASCII only (ord <= 255, printable)
        - Cannot start with '#'
        - Cannot be '.' or '..'
        - No case-insensitive collision with existing aliases
        """
        ...
    
    def validate_value(self, value: str) -> bool: ...
    
    def unused_aliases(self, grid: "Grid") -> list[str]: ...
    
    def color_distribution(self, grid: "Grid") -> dict[str, int]: ...
    
    def nearest_color(self, hex_color: str) -> str: ...  # for import
```

### Error handling

All errors should produce messages that help an LLM self-correct:

```
ERROR: grid.txt row 5 col 12: unknown palette alias 'XY' — define it in palette.txt or use #RRGGBB
ERROR: row number must be 0-31, got 32 (grid is 32 rows, 0-indexed)
ERROR: fill expects 4 arguments (row col_start col_end color), got 3
ERROR: palette.txt line 7: duplicate alias 'R' (first defined on line 3)
ERROR: palette.txt line 9: alias 'sk' conflicts with existing alias 'SK' (case-insensitive duplicates not allowed)
ERROR: palette.txt line 4: alias 'ABC' too long — aliases must be 1-2 characters, got 3
```

Include the valid range, the expected format, and what to do about it.

### Testing

Write tests for:
- Grid load/save round-trip (load a file, save it, load again — should be identical)
- Every CLI command with valid inputs
- Every CLI command with invalid inputs (check error messages)
- Palette resolution (alias → color, inline hex, transparent, unknown alias)
- Palette alias validation: 1-char works, 2-char works, 3-char rejected, case-insensitive duplicate rejected, `#`-prefixed rejected, non-ASCII-extended rejected
- Palette with mixed 1-char and 2-char aliases in same grid
- Flood fill (basic case, edge cases: filling the entire grid, filling a single pixel, filling when already the target color)
- Flip/rotate operations
- Spritesheet assembly
- Grid dimensions from config

Use `pytest`. Keep tests in a `tests/` directory with fixture grid/palette files in `tests/fixtures/`.

### Dependencies

**Required:**
- Python 3.10+
- Pillow (for image rendering/export)

**Standard library (no install needed):**
- tkinter (GUI)
- pathlib, argparse, json, copy, sys, os

**Optional/dev:**
- pytest (testing)
- pyinstaller (packaging)

**Do NOT add:**
- numpy (Pillow's pixel operations are sufficient for this scale)
- any web framework
- any database
- any GUI framework other than tkinter

### Packaging for Distribution

The tool must be distributable as:

1. **pip package** (`pip install gridfab`) with entry points:
   ```toml
   [project.scripts]
   gridfab = "gridfab.cli:main"
   
   [project.gui-scripts]  
   gridfab-gui = "gridfab.gui:main"
   ```

2. **Standalone binaries** via PyInstaller + GitHub Actions:
   - Windows: `.exe`
   - macOS: `.app` in `.dmg`
   - Linux: AppImage or standalone binary
   - CI workflow triggered on version tags

**`pyproject.toml` skeleton:**
```toml
[project]
name = "gridfab"
version = "0.1.0"
description = "Human-AI collaborative pixel art editor"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = ["Pillow>=10.0"]

[project.optional-dependencies]
dev = ["pytest", "pyinstaller"]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

---

## README Structure

The README is the first thing people see. It needs to be compelling.

### Must include:

1. **Hero image/GIF** — A side-by-side showing the text grid on the left and the rendered sprite on the right. Or even better: a GIF of the human painting in the GUI while text appears in a terminal beside it.

2. **One-line pitch**: "Pixel art editor where AI and humans edit the same sprite in real time — because the art is plain text."

3. **Why this exists** — Brief personal story. "I'm a hobby game dev making games in Godot. I wanted an LLM to help me create sprites, but no art tool speaks text. So I built one."

4. **Quick start** — From zero to first sprite in 4 commands:
   ```bash
   pip install gridfab
   gridfab init --size 32x32
   gridfab-gui .
   # Start painting! Or ask your AI to edit grid.txt
   ```

5. **The "aha" demo** — Show the workflow:
   - Human: "Hey Claude, I need a red potion bottle sprite"
   - Claude edits grid.txt via CLI commands
   - Human hits Refresh in GUI, sees the sprite, tweaks a few pixels
   - Human: "Make the liquid darker and add a cork"
   - Claude edits grid.txt again
   - Final sprite in under 2 minutes

6. **Feature list** with status (✅ done, 🚧 in progress, 📋 planned)

7. **For game devs** — Export formats, engine support, spritesheet generation

8. **For AI/LLM users** — How to use with Claude Code, Claude chat, or any coding agent

9. **Installation** — pip, standalone downloads, from source

10. **File format reference** — Document grid.txt and palette.txt

11. **CLI reference** — All commands with examples

12. **Contributing** — How to help

13. **License** — MIT

---

## Priority Order for Implementation

If you're working through this with Claude Code, here's the order that maximizes "impressive demo" potential at each stage:

### Sprint 1: Package restructure + polish (3-4 hours)
- Restructure into the `gridfab/` package layout
- Set up `pyproject.toml` with entry points
- Configurable grid size
- Undo/redo in GUI
- Zoom and grid toggle
- Status bar
- Keyboard shortcuts
- Eyedropper and fill tools
- Write initial tests

### Sprint 2: Animation foundation (3-4 hours)
- Multi-frame file format (`frame_001.txt`)
- CLI commands: frame add/delete/select
- GUI frame strip and navigation
- Onion skinning
- Play/pause preview
- Spritesheet export with JSON metadata
- Animated GIF export

### Sprint 3: AI workflow features (2-3 hours)
- `describe` command
- `diff` command
- `flip` / `rotate` / `mirror` commands
- `outline` command
- `copy` / `paste` / `shift` commands
- `import` from PNG command
- `pattern` commands
- Symmetry mode

### Sprint 4: Project management (2-3 hours)
- Multi-sprite project structure
- Project init/list/export commands
- Shared palettes
- GUI project browser sidebar
- Tiling preview mode

### Sprint 5: Engine integration (2-3 hours)
- Godot export with SpriteFrames
- Unity export with .meta
- Generic spritesheet export options
- APNG export

### Sprint 6: Distribution (2-3 hours)
- GitHub Actions CI/CD for multi-platform builds
- PyPI publishing workflow
- README with GIFs and demos
- itch.io page setup

---

## What NOT to Build

Equally important — things to avoid:

- **Don't build a web version.** tkinter is fine. The web would add enormous complexity and break the file-system sync model.
- **Don't add a built-in LLM client.** The tool doesn't call AI APIs. The AI uses the CLI. Keep the boundary clean.
- **Don't support PSD/ASE import.** These are complex binary formats. Support PNG import only.
- **Don't build layer support in Phase 1 or 2.** Mentioned as future work.
- **Don't add drawing shapes (circles, lines, beziers).** This is a pixel art tool, not a vector editor. Freehand painting + rect fill + flood fill is sufficient.
- **Don't over-engineer the GUI.** It should look simple and functional. Fancy UI is not the selling point — the dual-interface workflow is.
- **Don't add collaborative real-time editing (multiple simultaneous users).** The file-system model handles human+AI but not multiple humans editing simultaneously. That's fine.
- **Don't break backward compatibility with the existing grid.txt format.** Ever. New features should be additive (new files, new config options), never changing how grid.txt works.

---

## Technical Decisions (Already Made)

These have been decided:

1. **Frame file naming**: `frame_001.txt`, `frame_002.txt`, etc. Zero-padded three digits.

2. **Config format**: JSON. It's stdlib, universally understood, and every LLM can read/write it perfectly.

3. **Active frame**: Both a state file (`.gridfab_state`) AND `--frame N` argument are supported. The `--frame` argument always wins over the state file. `gridfab frame select 2` writes to the state file for interactive LLM sessions. The state file is a simple JSON: `{"active_frame": 2}`.

## Technical Decisions (Open — decide during implementation)

4. **GUI framework future**: tkinter works for now but has limitations (no GPU acceleration, limited widget set). If the project grows, CustomTkinter or Dear PyGui could be considered, but don't switch prematurely.

5. **CLI framework**: argparse (stdlib) is fine for now. click or typer would be nicer but add dependencies. Your call.

---

## Success Criteria

The tool is "done enough to release" when:

1. A user can `pip install gridfab`, create a sprite, paint it in the GUI, and export a PNG — in under 2 minutes
2. An LLM (via Claude Code or similar) can read grid.txt, understand the sprite, and make meaningful edits via CLI commands
3. The human can see the LLM's changes by hitting Refresh (or auto-refresh)
4. Animation: create a 4-frame walk cycle and export as spritesheet + GIF
5. The README has a compelling GIF showing the human-AI workflow
6. Pre-built binaries exist for Windows, macOS, and Linux on GitHub Releases
7. `gridfab export godot` produces files that import cleanly into Godot 4

---

*This spec is a living document. Update it as decisions are made and features are implemented.*
