# src/gridfab/tagger/ — Tileset Tagger

Interactive GUI for tagging tiles in existing spritesheet PNGs with AI-assisted naming via Claude Code CLI. Outputs GridFab-compatible index.json files.

## Modules

- **`tags.py`** — `DEFAULT_TAGS`, `RESERVED_KEYS`, `TagManager` class for tag shortcuts and persistence
- **`navigator.py`** — `TilesetNavigator` class for loading tilesets and tile-level image access
- **`ai.py`** — `AIAssistant` class for Claude Code CLI integration (name/description generation)
- **`app.py`** — `TaggerApp` GUI class + `main()` entry point

## Entry Points

- `gridfab tag <tileset.png>` — CLI subcommand (dispatched from `cli.py`)
- `gridfab-tagger` — Standalone GUI entry point (via `pyproject.toml` gui-scripts)

## Key Design

- Keyboard-driven workflow: press letter keys to toggle tags, Tab for AI generation, Enter to save
- Auto-saves progress to index.json; re-run to resume where you left off
- `tile_type` field auto-fills from active tags (single tag = that tag name, multiple = "multi")
- Completeness requires `description`, `tags`, and `tile_type` — incomplete sprites are queued for review on resume
