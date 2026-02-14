"""Tests for gridfab.cli — argument parsing and dispatch."""

import json
import sys
import pytest
from unittest.mock import patch
from pathlib import Path

from gridfab.cli import parse_size, main
from gridfab.commands.init import cmd_init


class TestParseSize:
    def test_valid_square(self):
        assert parse_size("32x32") == (32, 32)

    def test_valid_non_square(self):
        assert parse_size("16x32") == (16, 32)

    def test_uppercase_x(self):
        assert parse_size("16X16") == (16, 16)

    def test_missing_x(self):
        with pytest.raises(ValueError, match="WxH"):
            parse_size("3232")

    def test_non_integer(self):
        with pytest.raises(ValueError, match="integer"):
            parse_size("abcxdef")

    def test_zero_width(self):
        with pytest.raises(ValueError, match="positive"):
            parse_size("0x16")

    def test_zero_height(self):
        with pytest.raises(ValueError, match="positive"):
            parse_size("16x0")

    def test_negative(self):
        with pytest.raises(ValueError, match="positive"):
            parse_size("-1x16")

    def test_non_integer_height(self):
        with pytest.raises(ValueError, match="height must be an integer"):
            parse_size("16xabc")


class TestMainNoCommand:
    def test_exits_with_no_args(self):
        with patch.object(sys, "argv", ["gridfab"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1


class TestMainDispatch:
    def test_init_dispatches(self, tmp_path: Path):
        target = str(tmp_path / "test_sprite")
        with patch.object(sys, "argv", ["gridfab", "init", "--size", "4x4", target]):
            main()
        assert (tmp_path / "test_sprite" / "grid.txt").exists()

    def test_invalid_command(self):
        with patch.object(sys, "argv", ["gridfab", "nonexistent"]):
            with pytest.raises(SystemExit):
                main()

    def test_error_prints_to_stderr(self, tmp_path: Path, capsys):
        with patch.object(sys, "argv", ["gridfab", "render", str(tmp_path)]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr()
        assert "ERROR" in captured.err

    def test_render_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "render", str(sprite_dir)]):
            main()
        assert (sprite_dir / "preview.png").exists()

    def test_show_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "show", str(sprite_dir)]):
            main()
        assert (sprite_dir / "preview.png").exists()

    def test_pixel_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "pixel", "0", "0", "R", "--dir", str(sprite_dir)]):
            main()

    def test_pixels_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "pixels", "0,0,R", "1,1,B", "--dir", str(sprite_dir)]):
            main()

    def test_row_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "row", "0", "R", "B", "G", "R", "--dir", str(sprite_dir)]):
            main()

    def test_rows_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "rows", "0", "1", "R", "B", "G", "R", ".", ".", ".", ".", "--dir", str(sprite_dir)]):
            main()

    def test_fill_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "fill", "0", "0", "3", "R", "--dir", str(sprite_dir)]):
            main()

    def test_rect_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "rect", "0", "0", "1", "1", "B", "--dir", str(sprite_dir)]):
            main()

    def test_clear_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "clear", str(sprite_dir)]):
            main()

    def test_export_dispatches(self, sprite_dir_with_config: Path):
        with patch.object(sys, "argv", ["gridfab", "export", str(sprite_dir_with_config)]):
            main()
        assert (sprite_dir_with_config / "output.png").exists()

    def test_palette_dispatches(self, sprite_dir: Path):
        with patch.object(sys, "argv", ["gridfab", "palette", str(sprite_dir)]):
            main()

    def test_icon_dispatches(self, sprite_dir_with_config: Path):
        with patch.object(sys, "argv", ["gridfab", "icon", str(sprite_dir_with_config)]):
            main()
        assert (sprite_dir_with_config / "icon.ico").exists()

    def test_init_bad_size_exits(self, tmp_path: Path):
        with patch.object(sys, "argv", ["gridfab", "init", "--size", "notasize", str(tmp_path)]):
            with pytest.raises(SystemExit):
                main()
