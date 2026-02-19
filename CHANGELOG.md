# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0]

### Added

#### Animation System
- Full animation support: `frame_NNN.txt` files, `animation.json` metadata, `.gridfab_state` for active frame tracking
- `frame add` command: add frames (copy active, `--from N`, or `--blank`); first call converts grid.txt-only sprites to animated mode
- `frame delete` command: delete frames with automatic renumbering and animation reference updates
- `frame select` command: set the active frame
- `frame list` command: list all frames with active marker
- `frame copy-rect` command: copy a rectangular region from one frame to another
- `--frame N` flag on all edit and output commands to target specific frames
- `anim add` / `anim list` / `anim delete` commands: manage named animations with frame lists, FPS, and loop settings
- `anim sheet` command: export animation spritesheet PNG + JSON metadata (horizontal/vertical/grid layouts)
- `anim sheets` command: export spritesheets for all defined animations
- `anim gif` / `anim preview` commands: export animated GIF

#### Animation Subdirectories
- Each animation can live in its own subdirectory with independent frame numbering (e.g. `burn/frame_001.txt`), inheriting `palette.txt` and `gridfab.json` from the parent sprite
- `base:N` frame references in animation.json to reuse parent sprite frames (e.g. `"base:1"`)
- `anim create` command: create an animation subdirectory with an empty `animation.json`
- `frame add`/`frame delete` in subdirectories automatically update the subdir's `animation.json`
- `anim sheets` discovers and exports subdirectory animations alongside root-level animations
- Palette and config parent-directory fallback for all commands operating in subdirectories

#### GUI Editor Enhancements
- Status bar: cursor position, selected color, grid dimensions, zoom level, tool name, modified indicator, file path
- Grid lines toggle (`G` key)
- Zoom (mouse wheel, 6 levels: 4/8/16/24/32/48px) and pan (middle-click drag)
- Cursor preview: colored border on hovered cell
- Tool mode system: Brush (`B`), Eyedropper (`I`, or Alt+click), Fill (`F`)
- Keyboard shortcuts: `R` render, `E` export, `1-9`/`0` palette colors, `.` transparent, `H`/`V` flip, `[`/`]` zoom
- "Animate" button: convert single-frame sprites to animated mode
- `gui` CLI command: launch the GUI from the terminal

#### GUI Animation Features
- Frame strip with numbered buttons, Add/Duplicate/Delete, Copy/Paste, Move Left/Right
- Frame navigation: click buttons or `<`/`>` keys; auto-saves on switch
- Onion skinning: `O` to toggle, `Shift+O` to cycle opacity (25%/50%/75%)
- Animation playback: Play/Pause button, FPS spinner (1-60), animation selector, Space bar
- Side-by-side view (`M`): wrapping grid of all frames, auto-resize, synchronized zoom/pan
- Multi-frame editing: Ctrl+click/Shift+click selection, broadcast paint/fill/erase/flip to all selected frames
- Atomic multi-frame undo/redo
- Animation directory selector: dropdown to switch between "(Base)" and animation subdirectories
- "NewAnim" button to create animation subdirectories from the GUI
- "+Base" button to insert base frame references in subdirectories

#### CLI & Format
- Dot-padded grid columns: all values padded to 2 characters with `.` for visual alignment
- `palette rename <old> <new>`: rename aliases across palette.txt and all grid/frame files
- `palette show` subcommand (bare `palette` still works)
- Hex auto-alias: passing `#RRGGBB` to edit commands auto-generates a palette alias
- Hex migration on load: inline hex values auto-migrated to palette aliases
- `clean` command: remove generated files (preview.png, scaled outputs), recurses into animation subdirectories

#### Atlas
- Animated sprite support: `*_sheet.png` files become `{dir}/{anim}` entries with animation metadata
- Discovers spritesheets inside animation subdirectories
- Columns auto-expand to fit the widest sprite entry

#### Tagger
- "Copy grid.txt" button (Ctrl+C): copies tile's grid.txt + palette.txt text to clipboard
- AI prompt includes grid.txt + palette.txt text for reasoning about actual pixel data

### Changed
- Grid cell values no longer support inline `#RRGGBB` hex colors — all colors must have palette aliases
- Palette aliases can no longer contain `.` (reserved for transparent and grid padding)
- `palette` CLI is now a subcommand group (`palette show`, `palette rename`); bare `palette` defaults to show
- `Palette.resolve()` no longer accepts inline hex — raises error for unknown aliases

### Removed
- Inline hex color support in grid.txt files (use palette aliases instead)

### Fixed
- Tagger: preserve original sprite name before deduplication so downstream code uses the correct base name
- GUI keyboard shortcuts `[`, `]`, `.` not working on Windows (keybinding format fix)
- GUI render/export subprocess errors now reported instead of failing silently
- GUI window no longer jumps around when zooming; canvas fills available space on window resize
- Animation subdirectory functions (`is_anim_subdir`, `resolve_palette_path`, `resolve_frame_path`, `resolve_config_path`) now resolve `Path(".")` correctly so CLI commands work when run from inside a subdirectory

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
