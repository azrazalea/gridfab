"""Palette: color alias management for GridFab sprites.

A palette maps 1-2 character aliases to #RRGGBB hex colors.
The "." alias is always reserved for transparent.

Alias rules:
- 1 or 2 characters long
- Case sensitive (R and r are different)
- No case-insensitive duplicates (can't have both SK and sk)
- Extended ASCII only (printable, ord <= 255)
- Cannot start with '#'
- '.' and '..' are reserved for transparent
"""

from __future__ import annotations

from pathlib import Path

TRANSPARENT = "."


def validate_hex_color(color: str, context: str = "") -> None:
    """Validate that a string is a proper #RRGGBB hex color."""
    ctx = f"{context}: " if context else ""
    if not color.startswith("#"):
        raise ValueError(f"{ctx}color must start with '#', got: '{color}'")
    if len(color) != 7:
        raise ValueError(f"{ctx}color must be #RRGGBB (7 chars), got: '{color}'")
    try:
        int(color[1:], 16)
    except ValueError:
        raise ValueError(f"{ctx}invalid hex digits in color: '{color}'")


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B) tuple."""
    return (
        int(hex_color[1:3], 16),
        int(hex_color[3:5], 16),
        int(hex_color[5:7], 16),
    )


class Palette:
    """Maps 1-2 character aliases to #RRGGBB hex colors."""

    def __init__(self, entries: dict[str, str | None] | None = None):
        self.entries: dict[str, str | None] = {TRANSPARENT: None}
        if entries:
            self.entries.update(entries)

    @classmethod
    def load(cls, path: Path) -> Palette:
        """Load a palette from a text file.

        Format: one alias per line as ALIAS=#RRGGBB
        Lines starting with # are comments. Blank lines are skipped.
        """
        palette = cls()
        if not path.exists():
            return palette

        with open(path) as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(
                        f"palette.txt:{line_num}: expected ALIAS=COLOR, got: '{line}'"
                    )
                alias, color = line.split("=", 1)
                alias = alias.strip()
                color = color.strip()

                palette._validate_alias(alias, line_num)

                if alias == TRANSPARENT:
                    raise ValueError(
                        f"palette.txt:{line_num}: '.' is reserved for transparent, "
                        f"cannot redefine"
                    )

                # Check case-insensitive duplicates
                for existing in palette.entries:
                    if existing == TRANSPARENT:
                        continue
                    if existing.lower() == alias.lower() and existing != alias:
                        raise ValueError(
                            f"palette.txt:{line_num}: alias '{alias}' conflicts with "
                            f"existing alias '{existing}' "
                            f"(case-insensitive duplicates not allowed)"
                        )

                if alias in palette.entries:
                    raise ValueError(
                        f"palette.txt:{line_num}: duplicate alias '{alias}'"
                    )

                if color.lower() == "transparent":
                    palette.entries[alias] = None
                else:
                    validate_hex_color(color, f"palette.txt:{line_num}")
                    palette.entries[alias] = color

        return palette

    def save(self, path: Path) -> None:
        """Save the palette to a text file."""
        with open(path, "w", newline="\n") as f:
            f.write("# Palette: ALIAS=#RRGGBB\n")
            for alias, color in self.entries.items():
                if alias == TRANSPARENT:
                    continue
                f.write(f"{alias}={color if color else 'transparent'}\n")

    def resolve(self, value: str, context: str = "") -> str | None:
        """Resolve a grid value to a hex color string or None (transparent).

        Accepts:
        - "." -> None (transparent)
        - A palette alias -> its hex color
        - An inline "#RRGGBB" -> itself
        """
        if value == TRANSPARENT:
            return None
        if value in self.entries:
            return self.entries[value]
        if value.startswith("#"):
            validate_hex_color(value, context)
            return value
        ctx = f" at {context}" if context else ""
        raise ValueError(
            f"unknown palette alias '{value}'{ctx} — "
            f"define it in palette.txt or use #RRGGBB"
        )

    @staticmethod
    def _validate_alias(alias: str, line_num: int | None = None) -> None:
        """Validate alias rules. Raises ValueError on violation."""
        ctx = f"palette.txt:{line_num}: " if line_num else ""
        if len(alias) < 1 or len(alias) > 2:
            raise ValueError(
                f"{ctx}alias must be 1-2 characters, got '{alias}' "
                f"({len(alias)} chars)"
            )
        if alias.startswith("#"):
            raise ValueError(f"{ctx}alias cannot start with '#': '{alias}'")
        if alias in (".", ".."):
            raise ValueError(f"{ctx}'{alias}' is reserved")
        for ch in alias:
            if ord(ch) > 255 or not ch.isprintable():
                raise ValueError(
                    f"{ctx}alias must be printable extended ASCII, got '{alias}'"
                )

    @property
    def colors(self) -> dict[str, str | None]:
        """Return all entries except transparent."""
        return {k: v for k, v in self.entries.items() if k != TRANSPARENT}

    def resolve_grid(self, raw_rows: list[list[str]]) -> list[list[str | None]]:
        """Convert an entire grid of raw values to resolved colors."""
        result = []
        for r, row in enumerate(raw_rows):
            resolved = []
            for c, val in enumerate(row):
                resolved.append(self.resolve(val, f"grid row {r} col {c}"))
            result.append(resolved)
        return result

    def __repr__(self) -> str:
        count = len(self.entries) - 1  # exclude transparent
        return f"Palette({count} colors)"
