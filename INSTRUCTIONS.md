# GridFab Instructions

GridFab is a pixel art editor where artwork is stored as plain text files. It has two interfaces that operate on the same files simultaneously:

- **gridfab** — Command-line interface for LLMs, scripts, and terminal users
- **gridfab-gui** — Visual editor with a painting canvas and palette sidebar

> **Important:** Always use the GUI or CLI commands to edit grid.txt. Do not edit it by hand. The tools handle validation, bounds checking, and consistent formatting. If the CLI finds a malformed grid.txt, it will auto-repair it (trimming extra columns, padding short rows, replacing invalid values) and print loud warnings — but prevention is better than repair.

## Getting Started

### Windows

1. Open a terminal in the GridFab folder
2. Run `gridfab.exe init` to create a new sprite in the current directory
3. Double-click `gridfab-gui.exe` to open the visual editor

### macOS

1. You may need to make the binaries executable first:
   ```bash
   chmod +x gridfab gridfab-gui
   ```
2. Run `./gridfab init` to create a new sprite in the current directory
3. Run `./gridfab-gui` to open the visual editor
4. If Gatekeeper blocks the app, go to System Settings > Privacy & Security and click "Allow"

### Linux

1. You may need to make the binaries executable first:
   ```bash
   chmod +x gridfab gridfab-gui
   ```
2. Run `./gridfab init` to create a new sprite in the current directory
3. Run `./gridfab-gui` to open the visual editor

> **Note on command names:** This document uses `gridfab` for CLI examples. On Windows, use `gridfab.exe` instead. On macOS/Linux, use `./gridfab` if the directory is not in your PATH.

## Sprite File Format

A GridFab sprite is a directory containing these files:

### grid.txt

The artwork itself. One row per line, values separated by spaces. Each value is one of:

- `.` — Transparent pixel
- A **palette alias** — 1 or 2 characters defined in palette.txt (e.g. `R`, `SK`, `DG`)
- An **inline hex color** — `#RRGGBB` format (e.g. `#CC3333`)

Example 4x4 grid:
```
. . R R
. R SK SK
R SK SK .
R R . .
```

All rows must have the same number of values. The grid dimensions are inferred from the file contents.

### palette.txt

Maps short aliases to hex colors. One entry per line in `ALIAS=#RRGGBB` format.

```
# Character colors
R=#CC3333
B=#0000FF
SK=#FFCCAA
DG=#336633
```

**Alias rules:**
- Must be 1 or 2 characters long (e.g. `R`, `SK`, `DG`)
- Case-sensitive: `R` and `r` are different aliases
- No case-insensitive duplicates: you cannot have both `SK` and `sk`
- Must be printable ASCII characters
- Cannot start with `#` (that's for comments and hex colors)
- `.` is reserved for transparent and cannot be redefined
- Lines starting with `#` are comments

### gridfab.json

Optional configuration file. Created automatically by `gridfab init`.

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

**Configuration options:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `grid.width` | integer | 32 | Grid width in pixels (used when creating new grids) |
| `grid.height` | integer | 32 | Grid height in pixels (used when creating new grids) |
| `export.scales` | list of integers | [1, 4, 8, 16] | Scale factors for PNG export |

## GUI Editor

Launch with `gridfab-gui [directory]` (defaults to current directory). On Windows, double-click `gridfab-gui.exe`.

### Painting

- **Left-click** — Paint with the selected color
- **Left-click + drag** — Paint continuously
- **Right-click** — Erase (set to transparent)
- **Right-click + drag** — Erase continuously

### Palette Sidebar

The left panel shows all colors defined in palette.txt. Click a color button to select it. The `.` button selects transparent (eraser). The currently selected color has a sunken border.

### Action Buttons

- **Save** — Write the current grid to grid.txt (Ctrl+S)
- **Render** — Save and generate preview.png with a checkerboard background
- **Refresh** — Reload grid.txt and palette.txt from disk. **Click this after an LLM or script makes changes** to see their edits in the GUI.
- **Clear** — Reset all pixels to transparent (with confirmation). Undoable.
- **New** — Create a new blank grid with a custom size. Prompts for WxH dimensions. Undoable.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save grid.txt |
| Ctrl+Z | Undo (up to 512 steps) |
| Ctrl+Y | Redo |
| Ctrl+Shift+Z | Redo (alternative) |

### Undo/Redo

The GUI tracks up to 512 undo steps. Each continuous paint stroke (click through release) is one undo step. Refreshing from disk is also an undoable action — if you don't like what an LLM changed, hit Ctrl+Z to revert to your previous state.

## CLI Reference

All commands operate on a sprite directory (defaults to `.` — the current directory). All coordinates are 0-indexed.

### gridfab init

Create a new sprite directory with blank grid.txt, starter palette.txt, and gridfab.json.

```
gridfab init [--size WxH] [directory]
```

- `--size` — Grid dimensions as WxH (default: 32x32). Examples: `8x8`, `16x16`, `32x32`, `64x64`
- `directory` — Target directory (default: current directory)

Will not overwrite an existing grid.txt. Preserves an existing palette.txt.

### gridfab render

Generate `preview.png` with a checkerboard background behind transparent pixels. Useful for quick visual checks.

```
gridfab render [directory]
```

### gridfab export

Export final PNGs at multiple scales with true RGBA transparency. Scale factors are configured in gridfab.json.

```
gridfab export [directory]
```

Output files:
- `output.png` — 1x scale (actual pixel dimensions)
- `output_4x.png` — 4x scale
- `output_8x.png` — 8x scale
- `output_16x.png` — 16x scale

Each pixel in the grid becomes an NxN block at scale N.

### gridfab palette

Display all colors defined in palette.txt.

```
gridfab palette [directory]
```

### gridfab pixel

Set a single pixel by coordinate. The simplest and most reliable way to place individual pixels.

```
gridfab pixel <row> <col> <color> [--dir directory]
```

Example:
```
gridfab pixel 5 13 DK
```

### gridfab pixels

Set multiple pixels in one call. Each pixel is specified as a comma-separated triplet: `row,col,color`. All pixels are validated before any are written (atomic operation).

```
gridfab pixels <row,col,color> [row,col,color ...] [--dir directory]
```

Example:
```
gridfab pixels 5,13,DK 5,14,WB 6,12,DK 6,15,WB
```

### gridfab row

Replace a single row in the grid. You must provide exactly as many values as the grid is wide.

```
gridfab row <row_number> <value0> <value1> ... [--dir directory]
```

Example (replace row 5 of a 4-wide grid):
```
gridfab row 5 R R SK .
```

### gridfab rows

Replace a range of rows (inclusive). Provide all values for all rows in sequence, left to right, top to bottom.

```
gridfab rows <start_row> <end_row> <values...> [--dir directory]
```

Example (replace rows 2-3 of a 4-wide grid):
```
gridfab rows 2 3 R R SK . . SK R R
```

### gridfab fill

Fill a horizontal span within a single row with one color.

```
gridfab fill <row> <col_start> <col_end> <color> [--dir directory]
```

Example (fill row 5, columns 2 through 10 with red):
```
gridfab fill 5 2 10 R
```

### gridfab rect

Fill a rectangular region with one color.

```
gridfab rect <row_start> <col_start> <row_end> <col_end> <color> [--dir directory]
```

Example (fill a rectangle from row 5, col 5 to row 15, col 15 with blue):
```
gridfab rect 5 5 15 15 B
```

Both `fill` and `rect` accept palette aliases or inline `#RRGGBB` hex colors.

### gridfab icon

Export `icon.ico` (Windows) and `icon.icns` (macOS) files containing multiple sizes (16, 32, 48, 256). The grid must be square (e.g. 32x32).

```
gridfab icon [directory]
```

Output: `icon.ico` and `icon.icns` in the sprite directory.

### gridfab clear

Reset all pixels in the grid to transparent, preserving grid dimensions.

```
gridfab clear [directory]
```

### gridfab tag

Interactive tileset tagger for labeling tiles in existing spritesheet PNGs. Includes AI-assisted name and description generation via Claude Code CLI.

```
gridfab tag <tileset.png> [--tile-size N] [--output FILE] [--model haiku|sonnet|opus]
                          [--bg-color RRGGBB] [--import-index FILE]
```

**Arguments:**
- `tileset.png` — Path to the tileset/atlas PNG image

**Options:**
- `--tile-size N` — Tile size in pixels (default: 32)
- `--output FILE` / `-o FILE` — Output index.json path (default: `<tileset>_index.json`)
- `--model MODEL` — Claude model for AI naming: `haiku` (default), `sonnet`, or `opus`
- `--bg-color RRGGBB` — Background color to treat as empty tiles (hex, e.g. `ffffff` for white)
- `--import-index FILE` — Import an existing index for review/enrichment

**Keyboard reference (tag mode — main window focused):**

| Key | Action |
|-----|--------|
| Letter/number keys | Toggle tags on the current tile |
| Tab | Generate AI name & description from active tags |
| Enter | Save sprite & advance to next tile |
| Space | Skip tile without saving |
| Backspace | Go back to previous tile |
| Delete | Mark tile as empty & skip |
| Arrow keys | Resize multi-tile selection |
| + or = | Add a new tag shortcut |
| F1 | Show help |
| Escape | Save index & quit |

**Edit mode (name/type/description field focused):**

| Key | Action |
|-----|--------|
| Tab | Move to next field |
| Enter | Save & advance (from description) or next field (from name/type) |
| Escape | Return to tag mode |

**Workflow:**
1. Press tag keys to describe the current tile (e.g. `w` for wall, `2` for stone)
2. Press Tab to generate an AI name and description (requires Claude Code CLI)
3. Review and edit the Name, Type, and Description fields
4. Press Enter from the Description field to save and advance

**AI assists, not replaces:** You can type a partial name or description, press Escape to return to tag mode, then press Tab to generate — the AI will refine what you wrote rather than starting from scratch. For example, type "dark" in the Name field, Escape, then Tab — the AI sees your draft and incorporates it. This works for both the Name and Description fields.

**Workshopping with the agent:** You can leave feedback directly in the Name or Description fields. For example, if the agent suggests a name you don't like, edit it to something like `"@Agent: this looks more like a chest than a crate"` and re-generate (Escape, Tab). The agent reads whatever is in the fields as context, so it will try to incorporate your feedback. This is useful for iterating on tricky tiles or when you're unsure what something is.

**Type field:** Auto-populated from active tags. One alphabetic tag fills in that tag name; two or more alphabetic tags fill in "multi". Numeric material tags (1-5) don't affect the type. You can always edit the type manually.

**Resume:** The tagger auto-saves to the output index.json after every sprite. Re-run with the same arguments to resume where you left off. Incomplete sprites (missing description, tags, or type) are automatically queued for review.

**Also available as:** `gridfab-tagger` standalone entry point (same functionality, independent binary in release builds).

### gridfab atlas

Pack multiple sprites into a single spritesheet (atlas.png) with a JSON index (index.json). Useful for game engine workflows where you need a packed spritesheet.

```
gridfab atlas <output_dir> [sprites...] [--include GLOB] [--exclude GLOB]
              [--tile-size WxH] [--columns N] [--reorder]
              [--atlas-name FILE] [--index-name FILE]
```

**Arguments:**
- `output_dir` — Where atlas.png and index.json are written (created if needed)
- `sprites...` — Sprite directories to include (positional)

**Options:**
- `--include GLOB` — Glob pattern to find sprite directories (repeatable, mutually exclusive with positional args)
- `--exclude GLOB` — Glob pattern to exclude sprite directories (repeatable, use with --include)
- `--tile-size WxH` — Base tile dimensions in pixels (default: auto-detect from first sprite)
- `--columns N` — Number of columns in the atlas grid (default: ceil(sqrt(total_tiles)))
- `--reorder` — Ignore existing index.json and place all sprites from scratch
- `--atlas-name FILE` — Output atlas filename (default: `atlas.png`)
- `--index-name FILE` — Output index filename (default: `index.json`)

**Multi-tile sprites:** Sprite grids must be exact multiples of the base tile size. A 64x64 sprite on a 32x32 tile grid spans 2x2 tiles. Non-multiple sprites are skipped with a warning.

**Stable ordering:** When an existing index.json is present, existing sprites keep their positions and new sprites fill available gaps. Use `--reorder` to reset all positions.

**Output files:**

- `atlas.png` — The spritesheet image (RGBA, transparent background). Each sprite is rendered at 1x scale (one pixel per grid cell) and placed on a tile grid.
- `index.json` — Sprite positions and layout metadata:

  ```json
  {
    "tile_size": [32, 32],
    "columns": 4,
    "sprites": {
      "grass": {
        "row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1,
        "description": "green grass tile",
        "tags": ["terrain", "grass", "nature"],
        "tile_type": "terrain"
      },
      "dragon": {
        "row": 0, "col": 1, "tiles_x": 2, "tiles_y": 2,
        "description": "",
        "tags": [],
        "tile_type": ""
      }
    }
  }
  ```

**Index fields:**

| Field | Description |
|-------|-------------|
| `tile_size` | `[width, height]` — Base tile dimensions in pixels. All sprites are placed on a grid of these tiles. |
| `columns` | Number of tile columns in the packing grid. Used internally by GridFab to reproduce the same layout on rebuilds. Game engines can ignore this. |
| `sprites` | Map of sprite name (directory name) to placement and semantic info. |
| `sprites.*.row` | Tile row where this sprite starts (0-indexed). Pixel Y = `row * tile_size[1]`. |
| `sprites.*.col` | Tile column where this sprite starts (0-indexed). Pixel X = `col * tile_size[0]`. |
| `sprites.*.tiles_x` | Width of this sprite in tiles. Pixel width = `tiles_x * tile_size[0]`. |
| `sprites.*.tiles_y` | Height of this sprite in tiles. Pixel height = `tiles_y * tile_size[1]`. |
| `sprites.*.description` | Human-readable description of the sprite (default: empty). Edit the index to fill this in. |
| `sprites.*.tags` | List of searchable tags for the sprite (default: empty). Edit the index to fill this in. |
| `sprites.*.tile_type` | Category/type of the sprite, e.g. "terrain", "prop", "character" (default: empty). Edit the index to fill this in. |

**Semantic fields:** New sprites are created with empty `description`, `tags`, and `tile_type`. These fields are preserved when rebuilding, reordering, or adding sprites — so you can safely fill them in by editing index.json and they won't be lost on the next atlas rebuild. These fields help LLMs and game engines find sprites by meaning rather than just by name.

**Reading sprites from the atlas in a game engine:** To extract a sprite's region from atlas.png, compute pixel coordinates from the index:
```
x = col * tile_size[0]
y = row * tile_size[1]
w = tiles_x * tile_size[0]
h = tiles_y * tile_size[1]
```
The `columns` field is not needed for extraction — it only controls how GridFab packs sprites during atlas generation.

Examples:
```bash
gridfab atlas output/ sprites/grass sprites/stone sprites/tree
gridfab atlas output/ --include "sprites/*" --exclude "sprites/wip_*"
gridfab atlas output/ sprites/* --tile-size 32x32 --columns 8
gridfab atlas output/ sprites/* --reorder
```

## Using GridFab with an LLM

GridFab is designed for human-AI collaborative pixel art. An LLM can read grid.txt as plain text, reason about spatial layout, and make structured edits via the CLI — all while a human paints in the GUI simultaneously.

### Claude Code Skill

If you use [Claude Code](https://claude.ai/claude-code), GridFab includes a skill that gives Claude built-in knowledge of how to create and edit sprites. Install it by copying the skill directory to your user-level skills:

```bash
cp -r skills/gridfab-create ~/.claude/skills/gridfab-create
```

On Windows:
```
xcopy /E /I skills\gridfab-create %USERPROFILE%\.claude\skills\gridfab-create
```

Once installed, Claude will automatically use GridFab's CLI when you ask it to create or edit pixel art. No prompt needed — just ask.

### Suggested LLM Prompt

For LLMs without the skill installed, copy and paste this prompt (or adapt it). You can also point the LLM at this file directly: "Read INSTRUCTIONS.md for how to use GridFab."

---

You are helping create pixel art using GridFab. The artwork is stored as plain text files that you can read and edit.

**Files:**
- `grid.txt` — The artwork. One row per line, space-separated. `.` = transparent. 1-2 char aliases (defined in palette.txt) or `#RRGGBB` for colors.
- `palette.txt` — Color definitions. Format: `ALIAS=#RRGGBB`. Aliases must be 1-2 characters, printable ASCII, case-sensitive (no case-insensitive duplicates). `.` is reserved for transparent. Lines starting with `#` are comments.
- `gridfab.json` — Config with grid dimensions and export scales.

**IMPORTANT: Always use the CLI commands to edit the grid. Do not edit grid.txt directly unless there is no CLI command that can accomplish the task.** The CLI handles validation, bounds checking, and consistent formatting. Direct file edits risk malformed files and data loss. palette.txt can be edited directly to add or modify color definitions.

**Binary name:** The CLI binary is `gridfab` on macOS/Linux or `gridfab.exe` on Windows. Check what platform you are running on and use the correct name. If running from source via pip, use `gridfab` on all platforms.

**Creating a new sprite:**
1. Run `gridfab init --size WxH <directory>` to create a new sprite (e.g. `gridfab init --size 16x16 my_sprite`)
2. Add colors to palette.txt: one per line as `ALIAS=#RRGGBB` (e.g. `R=#CC3333`)
3. Build the image using CLI edit commands

**Editing commands (preferred order):**
- `gridfab pixel <row> <col> <color>` — Set a single pixel by coordinate (simplest, no counting)
- `gridfab pixels <r,c,color> [...]` — Set multiple pixels in one call (validated atomically)
- `gridfab rect <r0> <c0> <r1> <c1> <color>` — Fill rectangle with one color
- `gridfab fill <row> <col_start> <col_end> <color>` — Fill horizontal span with one color
- `gridfab row <n> <values...>` — Replace one row (must provide all values for the full width)
- `gridfab rows <start> <end> <values...>` — Replace range of rows (all values, left-to-right, top-to-bottom)
- `gridfab clear [dir]` — Reset all pixels to transparent

**Other commands:**
- `gridfab render` — Generate preview.png
- `gridfab export` — Export PNGs at configured scales
- `gridfab icon` — Export icon.ico (requires square grid)
- `gridfab palette` — Show current palette colors
- `gridfab tag <tileset.png>` — Interactive tileset tagger with AI-assisted naming
- `gridfab atlas <output_dir> [sprites...]` — Pack sprites into a spritesheet (atlas.png + index.json)

All coordinates are 0-indexed. All rows must have the same width. After making changes, tell the user to click Refresh in the GUI to see your edits.

**Malformed file handling:** If grid.txt has structural issues (wrong column counts, invalid values, blank lines), the CLI auto-repairs the file and prints loud warnings to stderr. Check stderr output after every command to catch any repairs.

---

## More Information

- Source code and full documentation: https://github.com/azrazalea/gridfab
- License: GNU Affero General Public License v3.0 (see LICENSE.md)
