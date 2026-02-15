# tools/ — Standalone Utility Scripts

Scripts that support the GridFab workflow but are not part of the installable package.

## Scripts

- **`make_social_preview.py`** — Generates the GitHub social preview image from the logo assets.
- **`tileset_tagger.py`** — **Deprecated.** Thin wrapper that imports from `gridfab.tagger`. Use `gridfab tag` or `gridfab-tagger` instead.

## Usage

These are run directly with Python, not through the `gridfab` CLI:

```bash
python tools/make_social_preview.py
```
