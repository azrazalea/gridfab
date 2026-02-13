# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CHANGELOG.md following Keep a Changelog format
- CONTRIBUTING.md with development setup and guidelines
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1) with contact info
- CI status badge and correct clone URL in README
- INSTRUCTIONS.md with full user manual, GUI guide, CLI reference, config docs, and suggested LLM prompt
- README.md, LICENSE.md, CHANGELOG.md, INSTRUCTIONS.md, source code, and tests included in build artifacts
- Documentation links section in README (INSTRUCTIONS, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, spec)
- CLAUDE.md: project documentation inventory, build/CI section, rule to update INSTRUCTIONS.md on behavior changes
- CONTRIBUTING.md: requirement to update INSTRUCTIONS.md and CHANGELOG.md

### Fixed
- GUI: Refresh now pushes an undo snapshot, so LLM edits can be reverted with Ctrl+Z
- Double-zipped artifacts in CI (upload-artifact was re-zipping our archives)
- Nuitka-Action `output-file` input name (was `output-filename`)
- Nuitka dist directory paths in merge step (`__main__.dist`/`gui.dist`)
- Version suffix (commit SHA or tag version) added to artifact and archive filenames

### Changed
- GUI: undo history increased from 50 to 512 steps
- Adopted Semantic Versioning, starting at 0.1.0

## [0.1.0] - Unreleased

### Added
- Core data structures: Grid and Palette with load/save, validation, manipulation
- CLI with subcommands: init, render, export, show, palette, row, rows, fill, rect
- tkinter GUI editor with undo/redo (50-step history), palette sidebar, canvas painting
- Preview rendering with checkerboard background for transparent pixels
- Export rendering with true RGBA transparency at configurable scales
- Configurable grid sizes via `gridfab.json`
- 1-2 character palette aliases with case-insensitive collision detection
- GitHub Actions CI: tests + Nuitka builds for Windows, macOS, Linux on every push
- Atlas builder tool for packing sprite tiles
- Example quern (hand mill) sprite
- AGPLv3 license
- 28 tests covering Grid and Palette modules
