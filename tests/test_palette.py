"""Tests for gridfab.core.palette."""

import pytest
from pathlib import Path

from gridfab.core.palette import Palette, validate_hex_color, hex_to_rgb


class TestHexColor:
    def test_valid(self):
        validate_hex_color("#CC3333")
        validate_hex_color("#000000")
        validate_hex_color("#FFFFFF")

    def test_missing_hash(self):
        with pytest.raises(ValueError, match="must start with '#'"):
            validate_hex_color("CC3333")

    def test_wrong_length(self):
        with pytest.raises(ValueError, match="#RRGGBB"):
            validate_hex_color("#FFF")

    def test_invalid_digits(self):
        with pytest.raises(ValueError, match="invalid hex"):
            validate_hex_color("#GGGGGG")

    def test_hex_to_rgb(self):
        assert hex_to_rgb("#CC3333") == (204, 51, 51)
        assert hex_to_rgb("#000000") == (0, 0, 0)
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


class TestPaletteLoad:
    def test_load_basic(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        assert palette.resolve("R") == "#CC3333"
        assert palette.resolve("B") == "#0000FF"
        assert palette.resolve("SK") == "#FFCCAA"

    def test_transparent(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        assert palette.resolve(".") is None

    def test_inline_hex(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        assert palette.resolve("#112233") == "#112233"

    def test_unknown_alias(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        with pytest.raises(ValueError, match="unknown palette alias"):
            palette.resolve("X")

    def test_missing_file(self, tmp_path: Path):
        palette = Palette.load(tmp_path / "nonexistent.txt")
        assert palette.resolve(".") is None


class TestPaletteValidation:
    def test_alias_too_long(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("ABC=#FF0000\n")
        with pytest.raises(ValueError, match="1-2 characters"):
            Palette.load(tmp_path / "palette.txt")

    def test_alias_starts_with_hash(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("#R=#FF0000\n")
        # Lines starting with # are comments, so this should be skipped
        palette = Palette.load(tmp_path / "palette.txt")
        assert len(palette.colors) == 0

    def test_case_insensitive_duplicate(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("SK=#FF0000\nsk=#00FF00\n")
        with pytest.raises(ValueError, match="case-insensitive"):
            Palette.load(tmp_path / "palette.txt")

    def test_exact_duplicate(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("R=#FF0000\nR=#00FF00\n")
        with pytest.raises(ValueError, match="duplicate alias"):
            Palette.load(tmp_path / "palette.txt")

    def test_dot_reserved(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text(".=#FF0000\n")
        with pytest.raises(ValueError, match="reserved"):
            Palette.load(tmp_path / "palette.txt")

    def test_one_char_alias(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        assert "R" in palette.entries

    def test_two_char_alias(self, sample_palette: Path):
        palette = Palette.load(sample_palette / "palette.txt")
        assert "SK" in palette.entries


class TestPaletteSave:
    def test_round_trip(self, tmp_path: Path):
        palette = Palette({"R": "#CC3333", "B": "#0000FF"})
        path = tmp_path / "palette.txt"
        palette.save(path)
        reloaded = Palette.load(path)
        assert reloaded.resolve("R") == "#CC3333"
        assert reloaded.resolve("B") == "#0000FF"

    def test_transparent_alias(self, tmp_path: Path):
        palette = Palette({"G": None})
        path = tmp_path / "palette.txt"
        palette.save(path)
        reloaded = Palette.load(path)
        assert reloaded.resolve("G") is None


class TestPaletteResolveGrid:
    def test_resolves_full_grid(self):
        palette = Palette({"R": "#CC3333", "B": "#0000FF"})
        raw = [["R", ".", "B"], [".", "R", "."]]
        resolved = palette.resolve_grid(raw)
        assert resolved[0] == ["#CC3333", None, "#0000FF"]
        assert resolved[1] == [None, "#CC3333", None]

    def test_unknown_alias_errors(self):
        palette = Palette({"R": "#CC3333"})
        raw = [["R", "NOPE"]]
        with pytest.raises(ValueError, match="unknown palette alias"):
            palette.resolve_grid(raw)


class TestPaletteRepr:
    def test_repr(self):
        palette = Palette({"R": "#CC3333", "B": "#0000FF"})
        assert repr(palette) == "Palette(2 colors)"


class TestPaletteEdgeCases:
    def test_malformed_line_no_equals(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("BADLINE\n")
        with pytest.raises(ValueError, match="expected ALIAS=COLOR"):
            Palette.load(tmp_path / "palette.txt")

    def test_non_printable_alias(self, tmp_path: Path):
        (tmp_path / "palette.txt").write_text("\x01=#FF0000\n")
        with pytest.raises(ValueError, match="printable"):
            Palette.load(tmp_path / "palette.txt")

    def test_hash_alias_via_equals(self, tmp_path: Path):
        """Alias starting with # using ALIAS=COLOR format (not a comment)."""
        # Writing "#X=#FF0000" — the line starts with # so it's a comment.
        # To actually test the _validate_alias #-check, call it directly.
        with pytest.raises(ValueError, match="cannot start with '#'"):
            Palette._validate_alias("#X")
