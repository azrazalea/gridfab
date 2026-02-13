# tools/ — Standalone Utility Scripts

Scripts that support the GridFab workflow but are not part of the installable package.

## Scripts

- **`build_custom_atlas.py`** — Assembles individual tile PNGs into a single atlas texture + JSON index. Configurable input directory and tile size. Useful for game engine workflows where you need a packed spritesheet from individual GridFab exports.

## Usage

These are run directly with Python, not through the `gridfab` CLI:

```bash
python tools/build_custom_atlas.py [--input-dir DIR] [--tile-size N]
```
