# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
