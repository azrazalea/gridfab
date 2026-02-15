"""Tag management for the tileset tagger."""

import json
from pathlib import Path

# ─── Default Tag Configuration ───────────────────────────────────────────────

DEFAULT_TAGS = {
    # Structural elements
    "w": "wall", "f": "floor", "d": "door", "g": "window",
    "r": "roof", "s": "stairs", "c": "column",
    # Furniture & objects
    "t": "table", "b": "bed", "l": "light", "p": "container",
    "k": "shelf",
    # Materials
    "1": "wood", "2": "stone", "3": "metal", "4": "fabric", "5": "glass",
    # Modifiers
    "q": "broken", "e": "ornate", "x": "exterior", "i": "interior",
    # Nature
    "n": "nature", "v": "vegetation", "a": "water",
    # Characters & creatures
    "h": "character", "j": "creature",
    # UI & icons
    "u": "ui", "y": "icon",
    # Items
    "z": "weapon", "m": "food",
}

# Keys reserved for commands (cannot be used as tag shortcuts)
RESERVED_KEYS = {
    "Tab", "Return", "space", "BackSpace", "Escape", "Delete",
    "Left", "Right", "Up", "Down", "plus", "equal", "F1",
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
}


def tiles_to_rects(tiles: set[tuple[int, int]]) -> list[dict]:
    """Merge a set of (row, col) tiles into minimal rectangles.

    Uses a greedy row-span algorithm: groups tiles by column ranges per row,
    then extends matching spans downward to form rectangles.
    """
    if not tiles:
        return []

    # Sort by row then col
    sorted_tiles = sorted(tiles)

    # Group into row spans: for each row, find contiguous col runs
    row_spans: dict[int, list[tuple[int, int]]] = {}
    for r, c in sorted_tiles:
        if r not in row_spans:
            row_spans[r] = []
        spans = row_spans[r]
        if spans and spans[-1][1] == c - 1:
            spans[-1] = (spans[-1][0], c)
        else:
            spans.append((c, c))

    # Merge spans vertically: if consecutive rows have the same span, extend
    rects = []
    used: set[tuple[int, int, int]] = set()  # (row, c0, c1) already merged

    rows_sorted = sorted(row_spans.keys())
    for r in rows_sorted:
        for c0, c1 in row_spans[r]:
            if (r, c0, c1) in used:
                continue
            # Try to extend downward
            r_end = r
            for r_next in range(r + 1, max(row_spans.keys()) + 1):
                if r_next in row_spans and (c0, c1) in row_spans[r_next] and (r_next, c0, c1) not in used:
                    r_end = r_next
                    used.add((r_next, c0, c1))
                else:
                    break
            rects.append({"r0": r, "c0": c0, "r1": r_end, "c1": c1})

    return rects


def rects_to_tiles(rects: list[dict]) -> set[tuple[int, int]]:
    """Expand a list of rect dicts back into a set of (row, col) tiles."""
    tiles = set()
    for rect in rects:
        for r in range(rect["r0"], rect["r1"] + 1):
            for c in range(rect["c0"], rect["c1"] + 1):
                tiles.add((r, c))
    return tiles


class TagManager:
    """Manages tag shortcuts, empty tile persistence, and lookup."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.tags: dict[str, str] = {}
        self.empty_rects: list[dict] = []
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.tags = data.get("tags", {})
                self.empty_rects = data.get("empty_rects", [])
                return
            except (json.JSONDecodeError, KeyError):
                pass
        self.tags = DEFAULT_TAGS.copy()
        self.empty_rects = []
        self.save()

    def save(self):
        data = {"tags": self.tags}
        if self.empty_rects:
            data["empty_rects"] = self.empty_rects
        self.config_path.write_text(json.dumps(data, indent=2))

    def save_empty_tiles(self, tiles: set[tuple[int, int]]):
        """Merge tiles into rects and persist."""
        self.empty_rects = tiles_to_rects(tiles)
        self.save()

    def load_empty_tiles(self) -> set[tuple[int, int]]:
        """Expand persisted rects back into tile set."""
        return rects_to_tiles(self.empty_rects)

    def add_tag(self, key: str, name: str) -> bool:
        """Add a new tag. Returns False if key is taken or reserved."""
        if key in self.tags or key in RESERVED_KEYS or len(key) != 1:
            return False
        self.tags[key] = name
        self.save()
        return True

    def remove_tag(self, key: str) -> bool:
        if key in self.tags:
            del self.tags[key]
            self.save()
            return True
        return False

    def get_sorted(self) -> list[tuple[str, str]]:
        """Return tags sorted: letters first, then digits."""
        return sorted(self.tags.items(), key=lambda x: (not x[0].isalpha(), x[0]))
