# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
