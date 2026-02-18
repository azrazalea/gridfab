# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Animation system core data model: frame discovery (`frame_NNN.txt`), animation metadata (`animation.json`), active frame state (`.gridfab_state`), grid path resolution for frame-aware commands
- `frame add` command: add animation frames (copy active, `--from N`, or `--blank`); first call on grid.txt-only dir converts to animated mode
- `frame delete` command: delete frames with automatic renumbering and animation.json reference updates
- `frame select` command: set active frame via `.gridfab_state`
- `frame list` command: list all frames with active marker
- `--frame N` flag on all edit commands (`pixel`, `pixels`, `row`, `rows`, `fill`, `rect`, `clear`, `render`, `export`) to target specific animation frames
- `anim add` command: define named animations with frame lists, FPS, and loop settings stored in `animation.json`
- `anim list` command: display all defined animations
- `anim delete` command: remove animations by name
- `anim sheet` command: export animation spritesheet PNG + JSON metadata (horizontal/vertical/grid layouts)
- `anim sheets` command: export spritesheets for all defined animations
- `anim gif` command: export animated GIF for a named animation
- `anim preview` command: alias for `anim gif`
- GUI status bar showing cursor position, selected color, grid dimensions, zoom level, tool name, modified indicator, and file path
- GUI grid lines toggle (`G` key) to show/hide pixel borders
- GUI zoom (mouse wheel) with 6 levels (4/8/16/24/32/48px) and pan (middle-click drag)
- GUI cursor preview: colored border on hovered cell showing selected color
- GUI tool mode system with Brush, Eyedropper (`I` key), and Fill tools
- GUI eyedropper tool: pick color from canvas, auto-returns to brush; Alt+click from any tool
- GUI fill tool (`F` key): flood-fill contiguous region with selected color, undoable
- GUI keyboard shortcuts: `B` brush, `R` render, `E` export, `1-9`/`0` select palette color, `.` transparent, `H` flip horizontal, `V` flip vertical, `[`/`]` zoom out/in

### Fixed
- Tagger: preserve original sprite name before deduplication so downstream code uses the correct base name
- GUI keyboard shortcuts `[`, `]`, `.` not working on Windows (keybinding format fix)
- GUI render/export subprocess errors now reported instead of failing silently
- GUI window no longer jumps around when zooming; canvas fills available space on window resize

## [0.3.0]

### Added
- `import` command: convert images (any format Pillow can read: PNG, BMP, GIF, TIFF, WebP, JPEG, PSD, and more) into grid.txt + palette.txt format. Three modes: single image, single tile from tilesheet, and whole tilesheet split into individual sprites. Supports atlas index.json for named sprite extraction with metadata.
- `tag` command: interactive tileset tagger for labeling tiles in existing spritesheet PNGs (`gridfab tag <tileset.png>`). Keyboard-driven workflow with AI-assisted name/description generation via Claude Code CLI.
- `gridfab-tagger` standalone entry point (same as `gridfab tag`, available as independent binary in release builds)
- Tagger `tile_type` field: auto-fills from active tags (single tag = tag name, multiple = "multi")
- Tagger empty tile persistence: user-marked and auto-detected empty tiles saved as merged rectangles across sessions
- Tagger duplicate name detection with status bar notification
- `atlas` command: pack multiple sprites into a spritesheet with multi-tile support, stable ordering via index.json, glob-based sprite discovery, and configurable tile size/columns
- `atlas --atlas-name` and `--index-name` flags for custom output filenames
- Atlas index semantic fields: `description`, `tags`, and `tile_type` per sprite for LLM/game engine discoverability
- GUI palette editing: add colors via color picker, edit by double-clicking, remove via right-click menu, copy hex to clipboard
- GUI multi-column swatch grid with contrast-aware text labels
- GUI "Open" button to browse and open existing sprite folders
- GUI "Import" button to import images into new sprite folders
- GUI enhanced "New" button with choice between resize and new sprite
- GUI action buttons in 2-column grid layout

### Changed
- Reworked tagger default tags to broader categories (prop, equipment, terrain, hazard, path, etc.)
- Tagger AI feedback mode: `@:` prefix triggers fresh AI-generated results

### Fixed
- GUI Refresh button now rebuilds palette sidebar, so external palette changes appear after refresh

## [0.2.0]

### Added
- `pixel` command: set a single pixel by coordinate (`gridfab pixel <row> <col> <color>`)
- `pixels` command: batch pixel placement (`gridfab pixels <row,col,color> ...`) with atomic validation
- `clear` command: reset grid to all transparent without re-initializing (`gridfab clear [dir]`)
- `icon` command: export `.ico` and `.icns` icon files from square grids (`gridfab icon [dir]`)
- GUI "New" button: create a new grid with custom dimensions
- GUI "Clear" button: reset all pixels to transparent with confirmation dialog
- Project logo and application window icon (GUI title bar and Nuitka builds)
- Logo in README and social preview image for GitHub
- Auto-repair for malformed grid.txt files: trims extra columns, pads short rows, replaces invalid cell values with transparent, skips blank lines — with loud warnings to stderr
- Claude Code skills: gridfab-contribute (repo contributors), gridfab-release (release process), gridfab-create (end-user pixel art creation)
- Claude Code skill installation instructions in README and INSTRUCTIONS.md
- Veil of Ages credit in README "Why This Exists" section
- Examples and skills directories included in release archives
- Comprehensive test suite: 165 tests across 6 files (test_grid, test_palette, test_commands, test_render, test_cli, test_gui)

## [0.1.0]

### Added
- Core data structures: Grid and Palette with load/save, validation, manipulation
- CLI with subcommands: init, render, export, show, palette, row, rows, fill, rect
- tkinter GUI editor with undo/redo, palette sidebar, canvas painting
- Preview rendering with checkerboard background for transparent pixels
- Export rendering with true RGBA transparency at configurable scales
- Configurable grid sizes via `gridfab.json`
- 1-2 character palette aliases with case-insensitive collision detection
- GitHub Actions CI: tests + Nuitka builds for Windows, macOS, Linux
- GitHub Releases with platform archives on tagged pushes
- Atlas builder tool for packing sprite tiles
- Example quern (hand mill) sprite
- AGPLv3 license
- 28 tests covering Grid and Palette modules
- INSTRUCTIONS.md with full user manual, GUI guide, CLI reference, config docs, and suggested LLM prompt
- CHANGELOG.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
- README.md, LICENSE.md, source code, and tests included in build artifacts

### Fixed
- GUI: Refresh pushes an undo snapshot, so LLM edits can be reverted with Ctrl+Z
- Build artifacts no longer include __pycache__ or .egg-info directories

### Changed
- GUI: undo history increased from 50 to 512 steps
