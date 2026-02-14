"""Tests for the atlas command: packing sprites into a spritesheet."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from gridfab.commands.atlas_cmd import (
    cmd_atlas,
    compute_placement,
    load_existing_index,
    resolve_sprite_dirs,
)


def _make_sprite(parent: Path, name: str, width: int = 4, height: int = 4) -> Path:
    """Create a minimal sprite directory with grid.txt and palette.txt."""
    d = parent / name
    d.mkdir()
    rows = " ".join(["R"] * width)
    grid = "\n".join([rows] * height) + "\n"
    (d / "grid.txt").write_text(grid)
    (d / "palette.txt").write_text("R=#CC3333\n")
    return d


# ── TestResolveSpriteDirs ────────────────────────────────────────────


class TestResolveSpriteDirs:

    def test_positional_dirs_found(self, tmp_path):
        a = _make_sprite(tmp_path, "alpha")
        b = _make_sprite(tmp_path, "beta")
        result = resolve_sprite_dirs([str(a), str(b)], include=None, exclude=None)
        assert result == [a, b]

    def test_missing_grid_txt_raises(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(ValueError, match="No grid.txt"):
            resolve_sprite_dirs([str(d)], include=None, exclude=None)

    def test_nonexistent_dir_raises(self, tmp_path):
        bad = tmp_path / "nope"
        with pytest.raises(FileNotFoundError, match="Not a directory"):
            resolve_sprite_dirs([str(bad)], include=None, exclude=None)

    def test_include_glob_matches(self, tmp_path):
        _make_sprite(tmp_path, "tile_grass")
        _make_sprite(tmp_path, "tile_stone")
        _make_sprite(tmp_path, "enemy_bat")
        result = resolve_sprite_dirs(
            [], include=[str(tmp_path / "tile_*")], exclude=None,
        )
        names = [p.name for p in result]
        assert names == ["tile_grass", "tile_stone"]

    def test_exclude_glob_filters(self, tmp_path):
        _make_sprite(tmp_path, "tile_grass")
        _make_sprite(tmp_path, "tile_stone")
        result = resolve_sprite_dirs(
            [],
            include=[str(tmp_path / "tile_*")],
            exclude=[str(tmp_path / "tile_stone")],
        )
        names = [p.name for p in result]
        assert names == ["tile_grass"]

    def test_no_sprites_found_raises(self, tmp_path):
        with pytest.raises(ValueError, match="No sprite directories"):
            resolve_sprite_dirs(
                [], include=[str(tmp_path / "nonexistent_*")], exclude=None,
            )

    def test_glob_mode_alphabetical_order(self, tmp_path):
        _make_sprite(tmp_path, "cherry")
        _make_sprite(tmp_path, "apple")
        _make_sprite(tmp_path, "banana")
        result = resolve_sprite_dirs(
            [], include=[str(tmp_path / "*")], exclude=None,
        )
        names = [p.name for p in result]
        assert names == ["apple", "banana", "cherry"]

    def test_positional_and_glob_conflict_raises(self, tmp_path):
        a = _make_sprite(tmp_path, "alpha")
        with pytest.raises(ValueError, match="Cannot combine"):
            resolve_sprite_dirs(
                [str(a)], include=["*"], exclude=None,
            )


# ── TestComputePlacement ─────────────────────────────────────────────


class TestComputePlacement:

    def test_single_1x1_sprite(self):
        sprites = [("grass", 1, 1)]
        result = compute_placement(sprites, existing_index=None, columns=4, reorder=False)
        assert result == [("grass", 0, 0)]

    def test_multiple_1x1_fill_left_to_right(self):
        sprites = [("a", 1, 1), ("b", 1, 1), ("c", 1, 1), ("d", 1, 1), ("e", 1, 1)]
        result = compute_placement(sprites, existing_index=None, columns=4, reorder=False)
        assert result == [
            ("a", 0, 0),
            ("b", 0, 1),
            ("c", 0, 2),
            ("d", 0, 3),
            ("e", 1, 0),
        ]

    def test_2x2_sprite_placed(self):
        sprites = [("dragon", 2, 2)]
        result = compute_placement(sprites, existing_index=None, columns=4, reorder=False)
        assert result == [("dragon", 0, 0)]

    def test_mixed_sizes_no_overlap(self):
        sprites = [("big", 2, 2), ("small", 1, 1)]
        result = compute_placement(sprites, existing_index=None, columns=4, reorder=False)
        # big at (0,0), small at first available: (0,2)
        assert result == [("big", 0, 0), ("small", 0, 2)]

    def test_existing_index_preserves_positions(self):
        existing = {
            "tile_size": [4, 4],
            "columns": 4,
            "sprites": {
                "grass": {"row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1},
                "stone": {"row": 0, "col": 2, "tiles_x": 1, "tiles_y": 1},
            },
        }
        sprites = [("grass", 1, 1), ("stone", 1, 1)]
        result = compute_placement(sprites, existing_index=existing, columns=4, reorder=False)
        # Should preserve original positions
        assert ("grass", 0, 0) in result
        assert ("stone", 0, 2) in result

    def test_new_sprites_placed_after_existing(self):
        existing = {
            "tile_size": [4, 4],
            "columns": 4,
            "sprites": {
                "grass": {"row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1},
            },
        }
        sprites = [("grass", 1, 1), ("tree", 1, 1)]
        result = compute_placement(sprites, existing_index=existing, columns=4, reorder=False)
        assert ("grass", 0, 0) in result
        assert ("tree", 0, 1) in result

    def test_reorder_ignores_existing_index(self):
        existing = {
            "tile_size": [4, 4],
            "columns": 4,
            "sprites": {
                "grass": {"row": 0, "col": 3, "tiles_x": 1, "tiles_y": 1},
            },
        }
        sprites = [("grass", 1, 1), ("tree", 1, 1)]
        result = compute_placement(sprites, existing_index=existing, columns=4, reorder=True)
        # With reorder, grass should be at (0,0) not (0,3)
        assert result == [("grass", 0, 0), ("tree", 0, 1)]

    def test_removed_sprites_leave_gaps_new_fills(self):
        existing = {
            "tile_size": [4, 4],
            "columns": 4,
            "sprites": {
                "grass": {"row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1},
                "removed": {"row": 0, "col": 1, "tiles_x": 1, "tiles_y": 1},
                "stone": {"row": 0, "col": 2, "tiles_x": 1, "tiles_y": 1},
            },
        }
        # "removed" is no longer in sprites list; "tree" is new
        sprites = [("grass", 1, 1), ("stone", 1, 1), ("tree", 1, 1)]
        result = compute_placement(sprites, existing_index=existing, columns=4, reorder=False)
        assert ("grass", 0, 0) in result
        assert ("stone", 0, 2) in result
        # tree should fill the gap at (0,1) left by "removed"
        assert ("tree", 0, 1) in result


# ── TestCmdAtlas ─────────────────────────────────────────────────────


class TestCmdAtlas:

    def test_creates_atlas_and_index(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        _make_sprite(tmp_path, "s2")
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1", tmp_path / "s2"])
        assert (out / "atlas.png").exists()
        assert (out / "index.json").exists()

    def test_atlas_png_dimensions(self, tmp_path):
        _make_sprite(tmp_path, "s1", 4, 4)
        _make_sprite(tmp_path, "s2", 4, 4)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1", tmp_path / "s2"])
        img = Image.open(out / "atlas.png")
        # 2 sprites, ceil(sqrt(2))=2 columns → 2x1 atlas
        # Each sprite is 4x4 pixels at scale 1
        assert img.width == 2 * 4
        assert img.height == 1 * 4

    def test_index_json_structure(self, tmp_path):
        _make_sprite(tmp_path, "grass", 4, 4)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "grass"])
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert idx["tile_size"] == [4, 4]
        assert idx["columns"] == 1
        assert "grass" in idx["sprites"]
        sprite = idx["sprites"]["grass"]
        assert sprite["row"] == 0
        assert sprite["col"] == 0
        assert sprite["tiles_x"] == 1
        assert sprite["tiles_y"] == 1

    def test_multi_tile_sprite_spans(self, tmp_path):
        # 8x8 sprite on 4x4 tile grid → 2x2 tiles
        _make_sprite(tmp_path, "big", 8, 8)
        _make_sprite(tmp_path, "small", 4, 4)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "big", tmp_path / "small"], tile_size=(4, 4))
        with open(out / "index.json") as f:
            idx = json.load(f)
        big = idx["sprites"]["big"]
        assert big["tiles_x"] == 2
        assert big["tiles_y"] == 2

    def test_non_multiple_sprite_skipped(self, tmp_path, capsys):
        _make_sprite(tmp_path, "good", 4, 4)
        _make_sprite(tmp_path, "bad", 5, 5)  # not a multiple of 4
        out = tmp_path / "output"
        cmd_atlas(
            out,
            [tmp_path / "good", tmp_path / "bad"],
            tile_size=(4, 4),
        )
        captured = capsys.readouterr()
        assert "Skipping" in captured.out
        assert "bad" in captured.out
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert "bad" not in idx["sprites"]
        assert "good" in idx["sprites"]

    def test_tile_size_auto_detected(self, tmp_path):
        _make_sprite(tmp_path, "s1", 8, 8)
        _make_sprite(tmp_path, "s2", 8, 8)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1", tmp_path / "s2"])
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert idx["tile_size"] == [8, 8]

    def test_explicit_tile_size_used(self, tmp_path):
        _make_sprite(tmp_path, "s1", 8, 8)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1"], tile_size=(4, 4))
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert idx["tile_size"] == [4, 4]

    def test_columns_from_existing_index(self, tmp_path):
        _make_sprite(tmp_path, "s1", 4, 4)
        _make_sprite(tmp_path, "s2", 4, 4)
        out = tmp_path / "output"
        out.mkdir()
        # Write an existing index with columns=8
        existing = {
            "tile_size": [4, 4],
            "columns": 8,
            "sprites": {
                "s1": {"row": 0, "col": 0, "tiles_x": 1, "tiles_y": 1},
            },
        }
        with open(out / "index.json", "w") as f:
            json.dump(existing, f)
        cmd_atlas(out, [tmp_path / "s1", tmp_path / "s2"])
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert idx["columns"] == 8

    def test_output_dir_created(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        out = tmp_path / "nested" / "deep" / "output"
        cmd_atlas(out, [tmp_path / "s1"])
        assert (out / "atlas.png").exists()

    def test_single_sprite_1x1_atlas(self, tmp_path):
        _make_sprite(tmp_path, "solo", 4, 4)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "solo"])
        img = Image.open(out / "atlas.png")
        assert img.size == (4, 4)

    def test_stable_rebuild(self, tmp_path):
        _make_sprite(tmp_path, "a", 4, 4)
        _make_sprite(tmp_path, "b", 4, 4)
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "a", tmp_path / "b"])
        with open(out / "index.json") as f:
            idx1 = json.load(f)
        # Rebuild with same inputs
        cmd_atlas(out, [tmp_path / "a", tmp_path / "b"])
        with open(out / "index.json") as f:
            idx2 = json.load(f)
        assert idx1 == idx2

    def test_all_sprites_skipped_raises(self, tmp_path):
        _make_sprite(tmp_path, "bad", 5, 5)
        out = tmp_path / "output"
        with pytest.raises(ValueError, match="No valid sprites"):
            cmd_atlas(out, [tmp_path / "bad"], tile_size=(4, 4))


# ── TestCmdAtlasCli ──────────────────────────────────────────────────


class TestCmdAtlasCli:

    def test_dispatch_via_sysargv(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        out = tmp_path / "output"
        from gridfab.cli import main

        with patch.object(
            sys, "argv", ["gridfab", "atlas", str(out), str(tmp_path / "s1")]
        ):
            main()
        assert (out / "atlas.png").exists()

    def test_no_sprites_error_exit(self, tmp_path):
        out = tmp_path / "output"
        from gridfab.cli import main

        with patch.object(sys, "argv", ["gridfab", "atlas", str(out)]):
            with pytest.raises(SystemExit):
                main()

    def test_tile_size_parsed(self, tmp_path):
        _make_sprite(tmp_path, "s1", 8, 8)
        out = tmp_path / "output"
        from gridfab.cli import main

        with patch.object(
            sys,
            "argv",
            ["gridfab", "atlas", str(out), str(tmp_path / "s1"), "--tile-size", "4x4"],
        ):
            main()
        with open(out / "index.json") as f:
            idx = json.load(f)
        assert idx["tile_size"] == [4, 4]

    def test_cli_custom_names(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        out = tmp_path / "output"
        from gridfab.cli import main

        with patch.object(
            sys,
            "argv",
            [
                "gridfab", "atlas", str(out), str(tmp_path / "s1"),
                "--atlas-name", "custom_atlas.png",
                "--index-name", "custom_atlas_index.json",
            ],
        ):
            main()
        assert (out / "custom_atlas.png").exists()
        assert (out / "custom_atlas_index.json").exists()
        assert not (out / "atlas.png").exists()
        assert not (out / "index.json").exists()


# ── TestCustomFilenames ─────────────────────────────────────────────


class TestCustomFilenames:

    def test_custom_atlas_name(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1"], atlas_name="my_sheet.png")
        assert (out / "my_sheet.png").exists()
        assert not (out / "atlas.png").exists()
        # index.json should still use default
        assert (out / "index.json").exists()

    def test_custom_index_name(self, tmp_path):
        _make_sprite(tmp_path, "s1")
        _make_sprite(tmp_path, "s2")
        out = tmp_path / "output"
        cmd_atlas(out, [tmp_path / "s1"], index_name="sprites.json")
        assert (out / "sprites.json").exists()
        assert not (out / "index.json").exists()
        # atlas.png should still use default
        assert (out / "atlas.png").exists()
        # load_existing_index should read back the custom name
        existing = load_existing_index(out, index_name="sprites.json")
        assert existing is not None
        assert "s1" in existing["sprites"]
        # Rebuild with s2 added — should preserve s1 position
        cmd_atlas(
            out, [tmp_path / "s1", tmp_path / "s2"],
            index_name="sprites.json",
        )
        with open(out / "sprites.json") as f:
            idx = json.load(f)
        assert "s1" in idx["sprites"]
        assert "s2" in idx["sprites"]
