---
name: gridfab-create
description: Create and edit pixel art sprites using GridFab's CLI. Use when the user asks to create a sprite, draw pixel art, edit a grid.txt, work with GridFab, or make game art assets. Triggers on requests like "make me a sword sprite", "create a 16x16 character", "edit this sprite", "add a new color to the palette", or any pixel art task involving GridFab files.
---

# Creating Pixel Art with GridFab

GridFab stores artwork as plain text. Read and edit sprites through CLI commands while the user sees changes in the GUI by clicking Refresh.

## Design Process

Work like a pixel artist, not a code generator. Pixel art is iterative — do not try to produce a finished sprite in one pass.

### 1. Gather References

Before drawing anything, ask the user for:
- **Reference art or photos** of what they want (the more the better)
- Art style preferences (e.g. NES-style, modern pixel art, isometric)
- Size constraints and context (where will this sprite be used?)

If the user provides images, study them carefully for shape, color palette, proportions, and shading patterns.

### 2. Plan the Palette

Define colors in palette.txt before drawing. Study references to pick colors:
- Start with 4-8 colors — pixel art uses constrained palettes
- Include a base color, a highlight, and a shadow for each major element
- Use short, meaningful aliases (e.g. `SK` for skin, `DG` for dark green, `HL` for highlight)

### 3. Plan Composition

Before placing any pixels, decide:
- **Negative space** — How much empty space around the subject? Where does it go? A sprite crammed to the edges reads very differently from one with breathing room. Decide intentionally.
- **Positioning** — Where does the subject sit on the tile? Centered, grounded to the bottom, offset? Consider how this sprite will be used in-game.
- **Proportions** — How much of the tile does the subject fill? A 32x32 character might only occupy the center 20x28 pixels.
- **Light source** — Pick a consistent direction (e.g. top-left). This determines where highlights and shadows go in every later step.

### 4. Block Out the Shape

Start with a rough silhouette using `rect` and `fill`:
- Fill the outline/base color to establish the overall shape within the composition you planned
- Don't worry about detail yet — get the proportions and positioning right first

### 5. Iterate and Refine

This is where the real work happens. Work in passes:
1. **Silhouette** — Block out the overall shape with a single color
2. **Color regions** — Fill in major areas (skin, clothing, metal, etc.)
3. **Shading** — Add highlights and shadows consistent with the light source
4. **Details** — Eyes, edges, small features
5. **Cleanup** — Fix stray pixels, check symmetry if needed, verify negative space

### 6. Self-Check

After each pass, read grid.txt back and review your work:
- Does the silhouette read clearly?
- Are proportions correct for the grid size?
- Run `gridfab render` and check the preview image visually

### 7. Check In With the User

Show the user your progress at natural milestones (after blocking out the shape, after adding color, after detail work). Ask for feedback and adjust. The user may also tell you to work autonomously — in that case, keep iterating on your own but still self-check between passes.

**Do not dump a "finished" sprite on the user without checkpoints.** Iterating is faster than starting over.

## Quick Start — New Sprite

```bash
gridfab init --size 16x16 my_sprite
```

Then add colors to `my_sprite/palette.txt`:
```
# My palette
R=#CC3333
B=#3333CC
SK=#FFCCAA
```

Build the image using CLI edit commands, iterating through the design process above.

## Binary Name

- **Windows**: `gridfab.exe`
- **macOS/Linux**: `./gridfab` (or `gridfab` if in PATH)
- **From source via pip**: `gridfab` on all platforms

Check your platform and use the correct name.

## Files

- **grid.txt** — The artwork. One row per line, space-separated. `.` = transparent, 1-2 char palette aliases, or `#RRGGBB` inline hex.
- **palette.txt** — Color definitions: `ALIAS=#RRGGBB` per line. `#` lines are comments. Edit this file directly to add/modify colors.
- **gridfab.json** — Optional config with `grid.width`, `grid.height`, `export.scales`.

## Editing Commands

**Prefer CLI commands for editing the grid.** The CLI handles validation, bounds checking, and formatting. Editing grid.txt directly is a last resort — only do it if the CLI truly cannot accomplish what you need. palette.txt can always be edited directly.

All coordinates are 0-indexed. All rows must have the same width. Use `--dir <path>` if the sprite is not in the current directory.

| Command | Description |
|---------|-------------|
| `gridfab pixel <row> <col> <color>` | Set a single pixel by coordinate — simplest, no counting |
| `gridfab pixels <r,c,color> [...]` | Batch pixel placement — validated atomically |
| `gridfab rect <r0> <c0> <r1> <c1> <color>` | Fill a rectangle with one color |
| `gridfab fill <row> <col_start> <col_end> <color>` | Fill a horizontal span with one color |
| `gridfab rows <start> <end> <values...>` | Replace a range of rows in one call |
| `gridfab row <n> <values...>` | Replace a single row (provide all values for full width) |
| `gridfab clear [dir]` | Reset all pixels to transparent |

### Working Efficiently

Choose the right command for the job:

1. **`pixel`/`pixels`** — Your go-to for individual pixel placement. `pixel` sets one pixel by coordinate, `pixels` sets many in one call. No counting, no padding — just coordinates and colors.
2. **`rect`** — Large solid regions: backgrounds, big color blocks. Use this first to establish the major shapes.
3. **`fill`** — Horizontal spans within one row. Also works for single pixels (`fill <row> <col> <col> <color>`).
4. **`rows`/`row`** — Full row replacement. Error-prone: every row must have exactly the right number of values. Miscounts will malform the file. **Count carefully.** Best for small grids (8x8, 16x16) where rows are short.

**For large sprites (32x32+)**, prefer `rect` + `pixel`/`pixels` over `row`/`rows`. At 32 values per row, miscounting padding dots is very easy. `pixel` avoids counting entirely.

**Render after every major structural change** (`gridfab render`). Catching a mistake early is much cheaper than discovering it 15 rows later.

**Do not chain multiple commands in one bash call or write helper scripts.** Run one command at a time.

### Examples

```bash
# pixel: set a single pixel at row 10, column 13
gridfab pixel 10 13 DK

# pixels: batch pixel placement (row,col,color triplets)
gridfab pixels 5,13,DK 5,14,WB 6,12,DK 6,15,WB

# rect: fill a solid block — great for blocking out shapes
gridfab rect 5 5 15 15 B

# fill: horizontal span within one row
gridfab fill 5 2 10 R

# clear: start over without re-initializing
gridfab clear

# rows: write rows 2-4 of an 8-wide grid (3 rows x 8 cols = 24 values)
gridfab rows 2 4 . . OL OL OL OL . . . OL SK SK SK SK OL . . OL SK HL SK SK OL .
```

### Worked Example: 32x32 Potion Bottle

See `examples/potion/` for the full result. The build process demonstrates all command types:

```bash
gridfab init --size 32x32 potion
# Write palette.txt: OL=#2A2A3A, CK=#B8864E, CL=#D4A574,
#   GL=#8EAADC, GD=#5B7FB5, LQ=#CC3333, LD=#991A1A, LL=#FF6666, HL=#FFFFFF

# 1. Block out shapes with rect
gridfab rect 14 11 27 20 OL --dir potion   # bottle body
gridfab rect 8 13 13 18 OL --dir potion    # neck
gridfab rect 6 14 8 17 OL --dir potion     # cork

# 2. Fill interiors with fill (spans and single pixels)
gridfab fill 7 15 16 CK --dir potion       # cork interior
gridfab fill 9 14 17 GL --dir potion       # neck glass (repeat for rows 10-12)
gridfab rect 15 12 26 19 LQ --dir potion   # liquid (rect for big fill)
gridfab fill 14 12 19 GL --dir potion      # glass top of body

# 3. Shading with fill (single-pixel placement)
gridfab fill 25 16 19 LD --dir potion      # dark liquid bottom-right
gridfab fill 20 19 19 LD --dir potion      # dark liquid right edge (single pixel)
gridfab fill 15 12 13 LL --dir potion      # liquid highlight top-left
gridfab fill 9 14 14 HL --dir potion       # glass highlight (single pixel)
gridfab fill 9 17 17 GD --dir potion       # glass shadow right (single pixel)

# 4. Detail with row (shoulder shaping — requires exactly 32 values)
gridfab row 13 . . . . . . . . . . . . OL GL GL GL GL GL OL . . . . . . . . . . . . . --dir potion
gridfab row 28 . . . . . . . . . . . . . OL OL OL OL OL OL OL . . . . . . . . . . . . --dir potion

gridfab render potion
gridfab export potion
```

**Note on `row`:** Counting to exactly 32 values is error-prone. Use `row` only for rows that need pixel-precise control across the full width. For everything else, prefer `rect` + `fill`.

## Other Commands

| Command | Description |
|---------|-------------|
| `gridfab init [--size WxH] [dir]` | Create new sprite |
| `gridfab render [dir]` | Generate preview.png (checkerboard bg) |
| `gridfab export [dir]` | Export PNGs at configured scales |
| `gridfab palette [dir]` | Show current palette colors |
| `gridfab show [dir]` | Display grid contents |

## Palette Alias Rules

- 1-2 characters, case-sensitive
- No case-insensitive duplicates (`SK` and `sk` cannot coexist)
- Printable ASCII only, cannot start with `#`
- `.` is reserved for transparent

## Permission Note

Each gridfab CLI call is a separate bash command that may require user approval. If working autonomously, ask the user to approve gridfab commands so you can work without interruption. Sprite creation involves many commands — a 32x32 sprite may need 30-60+ CLI calls.
