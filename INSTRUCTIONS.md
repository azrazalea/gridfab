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

### gridfab clear

Reset all pixels in the grid to transparent, preserving grid dimensions.

```
gridfab clear [directory]
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
- `gridfab palette` — Show current palette colors

All coordinates are 0-indexed. All rows must have the same width. After making changes, tell the user to click Refresh in the GUI to see your edits.

**Malformed file handling:** If grid.txt has structural issues (wrong column counts, invalid values, blank lines), the CLI auto-repairs the file and prints loud warnings to stderr. Check stderr output after every command to catch any repairs.

---

## More Information

- Source code and full documentation: https://github.com/azrazalea/gridfab
- License: GNU Affero General Public License v3.0 (see LICENSE.md)
