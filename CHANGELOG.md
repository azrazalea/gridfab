# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Native `.ico` and `.icns` export via `gridfab icon` command (multi-size: 16, 32, 48, 256)
- Project logo and application window icon
- Logo in README, social preview image, icon in Nuitka builds
- Claude Code skills: gridfab-contribute (repo contributors), gridfab-release (release process), gridfab-create (end-user pixel art creation)
- Claude Code skill installation instructions in README and INSTRUCTIONS.md
- Veil of Ages credit in README "Why This Exists" section
- Roadmap items: pixel/pixels coordinate commands, graceful malformed-file handling, GUI Init/New button, atlas builder CLI integration
- Auto-repair for malformed grid.txt files: trims extra columns, pads short rows, replaces invalid cell values with transparent, skips blank lines — with loud warnings to stderr
- pytest-cov dev dependency and slow test marker
- Comprehensive grid tests: auto-repair, set_row, fill_row, edge cases, config loading (42 tests, up from 11)
- `pixel` command: set a single pixel by coordinate (`gridfab pixel <row> <col> <color>`)
- `pixels` command: batch pixel placement (`gridfab pixels <row,col,color> ...`)
- `clear` command: reset grid to all transparent without re-initializing (`gridfab clear [dir]`)
- GUI "Clear" button: resets all pixels to transparent with confirmation dialog
- GUI "New" button: creates a new grid with user-specified dimensions
- Command tests: 35 tests covering init, row, rows, fill, rect, pixel, pixels, clear
- GUI pure function tests: checker_color, cell_display_color (7 tests)
- Examples and skills directories included in release archives
- Comprehensive test suite: 135 tests across 6 files (test_grid, test_palette, test_commands, test_render, test_cli, test_gui)
- Extracted `parse_size()` as public function in cli.py for testability

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
