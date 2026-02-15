# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `tag` command: interactive tileset tagger for labeling tiles in existing spritesheet PNGs (`gridfab tag <tileset.png>`). Keyboard-driven workflow with AI-assisted name/description generation via Claude Code CLI.
- `gridfab-tagger` standalone entry point (same as `gridfab tag`, available as independent binary in release builds)
- Tagger `tile_type` field: auto-fills from active tags (single tag = tag name, multiple = "multi"). Required for sprite completeness alongside description and tags.
- Tagger empty tile persistence: user-marked and auto-detected empty tiles are saved to the tagger config file as merged rectangles, so they survive across sessions.
- `atlas` command: pack multiple sprites into a spritesheet (`gridfab atlas <output_dir> [sprites...]`). Supports multi-tile sprites, stable ordering via index.json, glob-based sprite discovery, and configurable tile size/columns.
- `atlas --atlas-name` and `--index-name` flags: customize output filenames (default: `atlas.png` and `index.json`)
- Atlas index semantic fields: each sprite in index.json now includes `description`, `tags`, and `tile_type` for LLM/game engine discoverability. New sprites get empty defaults; existing values are preserved across rebuilds, reorders, and sprite additions.

### Changed
- Reworked tagger default tags: replaced furniture-specific tags (table, bed, shelf, etc.) with broader categories (prop, equipment, terrain, hazard, path, etc.). 26 defaults with 9 keys left open for user customization.
- Tagger AI feedback mode: append `@:` to the Name or Description field to trigger feedback mode, where the AI generates a fresh result based on your instructions instead of preserving the existing text.
- Consolidated logo assets into `assets/logo/`; removed duplicate `assets/icon.*` and `assets/logo-256.png`
- Updated release workflow, README, and social preview script to reference `assets/logo/`
- README: added `pixel`, `pixels`, `clear`, `icon`, `atlas` to CLI reference; added New/Clear GUI buttons; moved atlas from Planned to Features; added auto-repair and icon export to feature list
- INSTRUCTIONS.md: expanded atlas index.json documentation with field-by-field reference table and game engine extraction guide
- Updated gridfab-create skill and project spec to reflect atlas as completed

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
