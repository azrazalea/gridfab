# render/ — Image Generation

Uses Pillow to render grids into PNG images. Takes resolved color grids (hex strings or None).

## Modules

- **`preview.py`** — `render_preview()`: Checkerboard background for transparent pixels. Used by the `render` command.
- **`export.py`** — `render_export()`: True RGBA transparency. Used by the `export` command for game engine assets.

## Notes

- Both functions take `colors` (list of lists of hex strings or None), `width`, `height`, and `scale`
- The render modules don't know about Grid or Palette — they only work with resolved colors
- Pixel-by-pixel rendering via `putpixel()` is fine at this scale (up to 64x64 sprites)
