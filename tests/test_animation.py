"""Tests for the animation system: core data model, frame management, anim commands."""

import json
import pytest
from pathlib import Path

from gridfab.core.animation import (
    discover_frames,
    is_animated,
    frame_path,
    resolve_grid_path,
    load_state,
    save_state,
    load_animations,
    save_animations,
    validate_animation,
    max_frame_number,
)
from gridfab.commands.frame_cmd import (
    cmd_frame_add,
    cmd_frame_delete,
    cmd_frame_select,
    cmd_frame_list,
    cmd_frame_copy_rect,
)
from gridfab.commands.anim_cmd import (
    cmd_anim_add,
    cmd_anim_list,
    cmd_anim_delete,
    cmd_anim_sheet,
    cmd_anim_gif,
)
from gridfab.render.spritesheet import render_spritesheet
from gridfab.render.gif import render_gif


# --- discover_frames ---

def test_discover_frames_empty(tmp_path):
    """No frame files returns empty list."""
    assert discover_frames(tmp_path) == []


def test_discover_frames_finds_frames(tmp_path):
    """Discovers frame_NNN.txt files in sorted order."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "frame_003.txt").write_text(". .\n")
    (tmp_path / "frame_002.txt").write_text(". .\n")
    assert discover_frames(tmp_path) == [1, 2, 3]


def test_discover_frames_ignores_non_frame_files(tmp_path):
    """Ignores grid.txt, palette.txt, and other non-frame files."""
    (tmp_path / "grid.txt").write_text(". .\n")
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "notes.txt").write_text("hello\n")
    assert discover_frames(tmp_path) == [1]


# --- is_animated ---

def test_is_animated_false_no_frames(tmp_path):
    """Non-animated sprite has no frame files."""
    (tmp_path / "grid.txt").write_text(". .\n")
    assert is_animated(tmp_path) is False


def test_is_animated_true_with_frames(tmp_path):
    """Animated sprite has frame_NNN.txt files."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    assert is_animated(tmp_path) is True


# --- frame_path ---

def test_frame_path_format(tmp_path):
    """Returns correctly zero-padded path."""
    assert frame_path(tmp_path, 1) == tmp_path / "frame_001.txt"
    assert frame_path(tmp_path, 42) == tmp_path / "frame_042.txt"
    assert frame_path(tmp_path, 999) == tmp_path / "frame_999.txt"


# --- resolve_grid_path ---

def test_resolve_grid_path_non_animated_uses_grid_txt(tmp_path):
    """Non-animated dir uses grid.txt."""
    (tmp_path / "grid.txt").write_text(". .\n")
    assert resolve_grid_path(tmp_path) == tmp_path / "grid.txt"


def test_resolve_grid_path_frame_override(tmp_path):
    """--frame flag overrides everything."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "frame_002.txt").write_text(". .\n")
    assert resolve_grid_path(tmp_path, frame=2) == tmp_path / "frame_002.txt"


def test_resolve_grid_path_animated_uses_state(tmp_path):
    """Animated dir reads active frame from .gridfab_state."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "frame_002.txt").write_text(". .\n")
    save_state(tmp_path, {"active_frame": 2})
    assert resolve_grid_path(tmp_path) == tmp_path / "frame_002.txt"


def test_resolve_grid_path_animated_defaults_to_frame_1(tmp_path):
    """Animated dir with no state file defaults to frame 1."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "frame_002.txt").write_text(". .\n")
    assert resolve_grid_path(tmp_path) == tmp_path / "frame_001.txt"


def test_resolve_grid_path_missing_frame_errors(tmp_path):
    """Requesting non-existent frame raises FileNotFoundError."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    with pytest.raises(FileNotFoundError, match="frame_005.txt not found"):
        resolve_grid_path(tmp_path, frame=5)


# --- load_state / save_state ---

def test_state_round_trip(tmp_path):
    """State file round-trips correctly."""
    save_state(tmp_path, {"active_frame": 3})
    state = load_state(tmp_path)
    assert state["active_frame"] == 3


def test_load_state_missing_returns_empty(tmp_path):
    """Missing state file returns empty dict."""
    assert load_state(tmp_path) == {}


# --- load_animations / save_animations ---

def test_animations_round_trip(tmp_path):
    """Animation definitions round-trip correctly."""
    anims = {
        "walk": {"frames": [1, 2, 3, 4], "fps": 8, "loop": True},
        "idle": {"frames": [1], "fps": 1, "loop": False},
    }
    save_animations(tmp_path, anims)
    loaded = load_animations(tmp_path)
    assert loaded == anims


def test_load_animations_missing_returns_empty(tmp_path):
    """Missing animation.json returns empty dict."""
    assert load_animations(tmp_path) == {}


# --- validate_animation ---

def test_validate_animation_valid():
    """Valid animation passes validation."""
    validate_animation("walk", [1, 2, 3], existing_frames=[1, 2, 3, 4])


def test_validate_animation_nonexistent_frame():
    """Animation referencing non-existent frame raises ValueError."""
    with pytest.raises(ValueError, match="frame 5"):
        validate_animation("walk", [1, 5], existing_frames=[1, 2, 3])


def test_validate_animation_empty_frames():
    """Animation with no frames raises ValueError."""
    with pytest.raises(ValueError, match="at least one frame"):
        validate_animation("walk", [], existing_frames=[1, 2, 3])


# --- max_frame_number ---

def test_max_frame_number_with_frames(tmp_path):
    """Returns highest frame number."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    (tmp_path / "frame_003.txt").write_text(". .\n")
    assert max_frame_number(tmp_path) == 3


def test_max_frame_number_no_frames(tmp_path):
    """Returns 0 when no frames exist."""
    assert max_frame_number(tmp_path) == 0


# ===================================================================
# Commit 2: Frame management commands
# ===================================================================

@pytest.fixture
def sprite_dir(tmp_path):
    """4x4 blank sprite with R/B/G palette for frame command tests."""
    (tmp_path / "grid.txt").write_text(
        ". . . .\n"
        ". . . .\n"
        ". . . .\n"
        ". . . .\n"
    )
    (tmp_path / "palette.txt").write_text(
        "R=#CC3333\n"
        "B=#0000FF\n"
        "G=#00CC00\n"
    )
    return tmp_path


# --- cmd_frame_add ---

def test_frame_add_first_renames_grid_txt(sprite_dir):
    """First frame add renames grid.txt to frame_001.txt and adds frame_002.txt."""
    cmd_frame_add(sprite_dir)
    assert not (sprite_dir / "grid.txt").exists()
    assert (sprite_dir / "frame_001.txt").exists()
    assert (sprite_dir / "frame_002.txt").exists()
    assert discover_frames(sprite_dir) == [1, 2]


def test_frame_add_copies_active_frame(sprite_dir):
    """Frame add copies content from active frame by default."""
    (sprite_dir / "grid.txt").write_text("R R\nB B\n")
    cmd_frame_add(sprite_dir)
    # frame_002 should be copy of frame_001 (which was grid.txt)
    content = (sprite_dir / "frame_002.txt").read_text()
    assert content == "R. R.\nB. B.\n"


def test_frame_add_blank(sprite_dir):
    """Frame add --blank creates transparent frame."""
    cmd_frame_add(sprite_dir)  # convert to animated
    cmd_frame_add(sprite_dir, blank=True)
    content = (sprite_dir / "frame_003.txt").read_text()
    lines = [line for line in content.strip().split("\n") if line]
    # all cells should be transparent (padded as "..")
    for line in lines:
        assert all(v == ".." for v in line.split())


def test_frame_add_from_specific_frame(sprite_dir):
    """Frame add --from N copies from a specific frame."""
    cmd_frame_add(sprite_dir)  # now have frames 1 and 2
    # Write distinct content to frame 1
    (sprite_dir / "frame_001.txt").write_text("R R R R\n. . . .\n. . . .\n. . . .\n")
    cmd_frame_add(sprite_dir, from_frame=1)  # frame 3 copies from 1
    content = (sprite_dir / "frame_003.txt").read_text()
    assert content.startswith("R. R. R. R.\n")


def test_frame_add_updates_state(sprite_dir):
    """Frame add sets active_frame to the new frame."""
    cmd_frame_add(sprite_dir)
    state = load_state(sprite_dir)
    assert state["active_frame"] == 2


# --- cmd_frame_delete ---

def test_frame_delete_middle_renumbers(sprite_dir):
    """Deleting middle frame renumbers remaining frames contiguously."""
    cmd_frame_add(sprite_dir)  # 1, 2
    cmd_frame_add(sprite_dir)  # 1, 2, 3
    # Put distinct content in each
    (sprite_dir / "frame_001.txt").write_text("R . . .\n. . . .\n. . . .\n. . . .\n")
    (sprite_dir / "frame_003.txt").write_text(". . . R\n. . . .\n. . . .\n. . . .\n")
    cmd_frame_delete(sprite_dir, 2)
    assert discover_frames(sprite_dir) == [1, 2]
    # Old frame 3 is now frame 2
    content = (sprite_dir / "frame_002.txt").read_text()
    assert content.startswith(". . . R\n")


def test_frame_delete_last_frame_errors(sprite_dir):
    """Cannot delete the only frame."""
    cmd_frame_add(sprite_dir)  # convert to animated (1 frame + 1 new = 2)
    cmd_frame_delete(sprite_dir, 2)  # delete one, leaving 1
    with pytest.raises(ValueError, match="cannot delete the only frame"):
        cmd_frame_delete(sprite_dir, 1)


def test_frame_delete_updates_state(sprite_dir):
    """Deleting active frame sets state to frame 1."""
    cmd_frame_add(sprite_dir)  # 1, 2 (active = 2)
    cmd_frame_delete(sprite_dir, 2)
    state = load_state(sprite_dir)
    assert state["active_frame"] == 1


def test_frame_delete_updates_animation_refs(sprite_dir):
    """Deleting a frame decrements animation frame refs >= deleted."""
    cmd_frame_add(sprite_dir)  # 1, 2
    cmd_frame_add(sprite_dir)  # 1, 2, 3
    anims = {"walk": {"frames": [1, 2, 3], "fps": 8, "loop": True}}
    save_animations(sprite_dir, anims)
    cmd_frame_delete(sprite_dir, 2)
    loaded = load_animations(sprite_dir)
    assert loaded["walk"]["frames"] == [1, 2]


# --- cmd_frame_select ---

def test_frame_select(sprite_dir):
    """Selecting a frame updates state."""
    cmd_frame_add(sprite_dir)  # 1, 2
    cmd_frame_select(sprite_dir, 1)
    state = load_state(sprite_dir)
    assert state["active_frame"] == 1


def test_frame_select_invalid_errors(sprite_dir):
    """Selecting non-existent frame raises ValueError."""
    cmd_frame_add(sprite_dir)
    with pytest.raises(ValueError, match="frame 99"):
        cmd_frame_select(sprite_dir, 99)


# --- cmd_frame_list ---

def test_frame_list(sprite_dir, capsys):
    """Frame list prints frames with active marker."""
    cmd_frame_add(sprite_dir)  # 1, 2 (active = 2)
    cmd_frame_list(sprite_dir)
    output = capsys.readouterr().out
    assert "frame_001.txt" in output
    assert "frame_002.txt" in output
    assert "*" in output  # active marker


# ===================================================================
# Commit 4: Animation management commands
# ===================================================================

@pytest.fixture
def animated_3_frames(tmp_path):
    """Animated sprite with 3 frames for animation tests."""
    (tmp_path / "palette.txt").write_text("R=#CC3333\nB=#0000FF\nG=#00CC00\n")
    (tmp_path / "grid.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    cmd_frame_add(tmp_path)  # 1, 2
    cmd_frame_add(tmp_path)  # 1, 2, 3
    return tmp_path


def test_anim_add(animated_3_frames):
    """Add a named animation."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2, 3], fps=8, loop=True)
    anims = load_animations(animated_3_frames)
    assert "walk" in anims
    assert anims["walk"]["frames"] == [1, 2, 3]
    assert anims["walk"]["fps"] == 8
    assert anims["walk"]["loop"] is True


def test_anim_add_duplicate_name_errors(animated_3_frames):
    """Adding duplicate animation name raises ValueError."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2], fps=8)
    with pytest.raises(ValueError, match="already exists"):
        cmd_anim_add(animated_3_frames, "walk", [2, 3], fps=8)


def test_anim_add_nonexistent_frame_errors(animated_3_frames):
    """Adding animation with non-existent frame raises ValueError."""
    with pytest.raises(ValueError, match="frame 99"):
        cmd_anim_add(animated_3_frames, "walk", [1, 99], fps=8)


def test_anim_list(animated_3_frames, capsys):
    """List all animations."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2, 3], fps=8, loop=True)
    cmd_anim_add(animated_3_frames, "idle", [1], fps=1, loop=False)
    cmd_anim_list(animated_3_frames)
    output = capsys.readouterr().out
    assert "walk" in output
    assert "idle" in output


def test_anim_list_empty(animated_3_frames, capsys):
    """List prints message when no animations defined."""
    cmd_anim_list(animated_3_frames)
    output = capsys.readouterr().out
    assert "no animation" in output.lower()


def test_anim_delete(animated_3_frames):
    """Delete an animation by name."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2, 3], fps=8)
    cmd_anim_add(animated_3_frames, "idle", [1], fps=1)
    cmd_anim_delete(animated_3_frames, "walk")
    anims = load_animations(animated_3_frames)
    assert "walk" not in anims
    assert "idle" in anims


def test_anim_delete_missing_errors(animated_3_frames):
    """Deleting non-existent animation raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        cmd_anim_delete(animated_3_frames, "walk")


# ===================================================================
# Commit 5: Spritesheet and GIF Export
# ===================================================================

# --- render_spritesheet ---

def test_spritesheet_horizontal():
    """Horizontal spritesheet has correct dimensions."""
    # 3 frames, 4x4, scale 1
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
        [["#0000FF"] * 4] * 4,
    ]
    img, meta = render_spritesheet(frames_colors, 4, 4, scale=1, layout="horizontal")
    assert img.size == (12, 4)  # 3 frames * 4 wide
    assert len(meta["animations"]["default"]["frames"]) == 3


def test_spritesheet_vertical():
    """Vertical spritesheet has correct dimensions."""
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
    ]
    img, meta = render_spritesheet(frames_colors, 4, 4, scale=1, layout="vertical")
    assert img.size == (4, 8)  # 2 frames * 4 tall


def test_spritesheet_grid_layout():
    """Grid spritesheet with columns has correct dimensions."""
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
        [["#0000FF"] * 4] * 4,
        [[None] * 4] * 4,
    ]
    img, meta = render_spritesheet(frames_colors, 4, 4, scale=1, layout="grid", columns=2)
    assert img.size == (8, 8)  # 2 cols * 4, 2 rows * 4


def test_spritesheet_scale():
    """Spritesheet respects scale factor."""
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
    ]
    img, meta = render_spritesheet(frames_colors, 4, 4, scale=2, layout="horizontal")
    assert img.size == (16, 8)  # 2 frames * 4*2 wide, 4*2 tall


def test_spritesheet_metadata_structure():
    """Spritesheet metadata has expected structure."""
    frames_colors = [
        [["#FF0000"] * 2] * 2,
        [["#00FF00"] * 2] * 2,
    ]
    _, meta = render_spritesheet(frames_colors, 2, 2, scale=4, layout="horizontal", anim_name="walk", fps=12, loop=False)
    assert meta["frame_size"] == {"w": 8, "h": 8}
    walk = meta["animations"]["walk"]
    assert walk["loop"] is False
    assert len(walk["frames"]) == 2
    assert walk["frames"][0]["x"] == 0
    assert walk["frames"][1]["x"] == 8
    assert walk["frames"][0]["duration"] == 83  # 1000/12


# --- render_gif ---

def test_gif_frame_count():
    """GIF has correct number of frames."""
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
        [["#0000FF"] * 4] * 4,
    ]
    images, duration = render_gif(frames_colors, 4, 4, scale=1, fps=8)
    assert len(images) == 3
    assert duration == 125  # 1000/8


def test_gif_dimensions():
    """GIF frames have correct dimensions."""
    frames_colors = [
        [["#FF0000"] * 4] * 4,
        [["#00FF00"] * 4] * 4,
    ]
    images, _ = render_gif(frames_colors, 4, 4, scale=2, fps=8)
    assert images[0].size == (8, 8)


# --- cmd_anim_sheet / cmd_anim_gif ---

def test_cmd_anim_sheet_creates_files(animated_3_frames):
    """anim sheet creates PNG and JSON files."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2, 3], fps=8)
    cmd_anim_sheet(animated_3_frames, "walk", scale=1)
    assert (animated_3_frames / "walk_sheet.png").exists()
    assert (animated_3_frames / "walk_sheet.json").exists()


def test_cmd_anim_gif_creates_file(animated_3_frames):
    """anim gif creates GIF file."""
    cmd_anim_add(animated_3_frames, "walk", [1, 2, 3], fps=8)
    cmd_anim_gif(animated_3_frames, "walk", scale=1)
    assert (animated_3_frames / "walk.gif").exists()


def test_cmd_anim_sheet_missing_anim_errors(animated_3_frames):
    """anim sheet with non-existent animation raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        cmd_anim_sheet(animated_3_frames, "walk", scale=1)


def test_cmd_anim_gif_missing_anim_errors(animated_3_frames):
    """anim gif with non-existent animation raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        cmd_anim_gif(animated_3_frames, "walk", scale=1)


# ===================================================================
# Commit 9: Frame swap and reorder
# ===================================================================

from gridfab.core.animation import swap_frame_files, update_animations_after_swap


def test_swap_frame_files(animated_3_frames):
    """Swapping two frames exchanges their file contents."""
    from gridfab.core.grid import Grid
    # Write distinct content to frames 1 and 2
    g1 = Grid.load(frame_path(animated_3_frames, 1))
    g1.set(0, 0, "R")
    g1.save(frame_path(animated_3_frames, 1))

    g2 = Grid.load(frame_path(animated_3_frames, 2))
    g2.set(0, 0, "B")
    g2.save(frame_path(animated_3_frames, 2))

    swap_frame_files(animated_3_frames, 1, 2)

    after1 = Grid.load(frame_path(animated_3_frames, 1))
    after2 = Grid.load(frame_path(animated_3_frames, 2))
    assert after1.data[0][0] == "B"
    assert after2.data[0][0] == "R"


def test_swap_frame_files_nonexistent_errors(tmp_path):
    """Swapping non-existent frame raises FileNotFoundError."""
    (tmp_path / "frame_001.txt").write_text(". .\n. .\n")
    with pytest.raises(FileNotFoundError):
        swap_frame_files(tmp_path, 1, 5)


def test_update_animations_after_swap():
    """Swapping frames updates animation references."""
    anims = {
        "walk": {"frames": [1, 2, 3], "fps": 8, "loop": True},
        "idle": {"frames": [1], "fps": 1, "loop": False},
    }
    result = update_animations_after_swap(anims, 1, 2)
    assert result["walk"]["frames"] == [2, 1, 3]
    assert result["idle"]["frames"] == [2]


def test_update_animations_after_swap_no_affected():
    """Swapping frames not referenced by animations leaves them unchanged."""
    anims = {
        "walk": {"frames": [1, 2], "fps": 8, "loop": True},
    }
    result = update_animations_after_swap(anims, 3, 4)
    assert result["walk"]["frames"] == [1, 2]


def test_update_animations_after_swap_same_frame():
    """Swapping a frame with itself is a no-op."""
    anims = {"walk": {"frames": [1, 2, 3], "fps": 8, "loop": True}}
    result = update_animations_after_swap(anims, 2, 2)
    assert result["walk"]["frames"] == [1, 2, 3]


def test_swap_and_move_frame_left(animated_3_frames):
    """Moving frame 2 left (swap 1,2) puts it in position 1."""
    from gridfab.core.grid import Grid
    g2 = Grid.load(frame_path(animated_3_frames, 2))
    g2.set(1, 1, "G")
    g2.save(frame_path(animated_3_frames, 2))

    # Save animation referencing frames
    anims = {"walk": {"frames": [1, 2, 3], "fps": 8, "loop": True}}
    save_animations(animated_3_frames, anims)

    swap_frame_files(animated_3_frames, 1, 2)
    updated_anims = update_animations_after_swap(
        load_animations(animated_3_frames), 1, 2,
    )
    save_animations(animated_3_frames, updated_anims)

    # Frame 1 now has the content that was in frame 2
    after = Grid.load(frame_path(animated_3_frames, 1))
    assert after.data[1][1] == "G"
    # Animation refs updated
    final_anims = load_animations(animated_3_frames)
    assert final_anims["walk"]["frames"] == [2, 1, 3]


# ===================================================================
# Commit 10: Integration tests
# ===================================================================

from gridfab.core.grid import Grid
from gridfab.commands.edit import cmd_pixel, cmd_fill, cmd_clear, cmd_rect
from gridfab.commands.render_cmd import cmd_render
from gridfab.commands.export_cmd import cmd_export


def test_full_animation_workflow(tmp_path):
    """End-to-end: init → frame add → pixel edits → anim → sheet → gif."""
    # Set up a sprite with palette
    (tmp_path / "palette.txt").write_text("R=#CC3333\nB=#0000FF\n")
    (tmp_path / "grid.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")

    # Add frames (converts to animated mode)
    cmd_frame_add(tmp_path)
    cmd_frame_add(tmp_path)
    cmd_frame_add(tmp_path, blank=True)
    assert discover_frames(tmp_path) == [1, 2, 3, 4]
    assert not (tmp_path / "grid.txt").exists()

    # Edit specific frames
    cmd_pixel(tmp_path, 0, 0, "R", frame=1)
    cmd_pixel(tmp_path, 0, 1, "B", frame=2)
    cmd_pixel(tmp_path, 1, 0, "R", frame=3)

    # Verify edits landed on correct frames
    g1 = Grid.load(frame_path(tmp_path, 1))
    assert g1.data[0][0] == "R"
    assert g1.data[0][1] == "."

    g2 = Grid.load(frame_path(tmp_path, 2))
    assert g2.data[0][1] == "B"

    g3 = Grid.load(frame_path(tmp_path, 3))
    assert g3.data[1][0] == "R"

    # Define animation and export
    cmd_anim_add(tmp_path, "walk", [1, 2, 3], fps=8, loop=True)
    cmd_anim_sheet(tmp_path, "walk", scale=1)
    cmd_anim_gif(tmp_path, "walk", scale=1)

    assert (tmp_path / "walk_sheet.png").exists()
    assert (tmp_path / "walk_sheet.json").exists()
    assert (tmp_path / "walk.gif").exists()

    # Frame list
    frames = discover_frames(tmp_path)
    assert frames == [1, 2, 3, 4]

    # Delete frame 4 (shouldn't affect walk animation)
    cmd_frame_delete(tmp_path, 4)
    assert discover_frames(tmp_path) == [1, 2, 3]
    anims = load_animations(tmp_path)
    assert anims["walk"]["frames"] == [1, 2, 3]


def test_backward_compat_non_animated_unchanged(tmp_path):
    """Non-animated sprite works exactly as before with all commands."""
    (tmp_path / "palette.txt").write_text("R=#CC3333\nB=#0000FF\n")
    (tmp_path / "grid.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")

    # Pixel edit
    cmd_pixel(tmp_path, 0, 0, "R")
    g = Grid.load(tmp_path / "grid.txt")
    assert g.data[0][0] == "R"

    # Fill (row 1, col 0 to 1)
    cmd_fill(tmp_path, 1, 0, 1, "B")
    g = Grid.load(tmp_path / "grid.txt")
    assert g.data[1][0] == "B"
    assert g.data[1][1] == "B"

    # Render
    cmd_render(tmp_path)
    assert (tmp_path / "preview.png").exists()

    # Export
    cmd_export(tmp_path)
    assert (tmp_path / "output.png").exists()

    # Clear
    cmd_clear(tmp_path)
    g = Grid.load(tmp_path / "grid.txt")
    assert g.data[0][0] == "."
    assert g.data[1][0] == "."

    # No frame files created
    assert not is_animated(tmp_path)
    assert (tmp_path / "grid.txt").exists()


def test_frame_select_then_edit_targets_correct_frame(tmp_path):
    """frame select + edit without --frame targets selected frame."""
    (tmp_path / "palette.txt").write_text("R=#CC3333\n")
    (tmp_path / "grid.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    cmd_frame_add(tmp_path)  # 1, 2
    cmd_frame_add(tmp_path)  # 1, 2, 3

    cmd_frame_select(tmp_path, 2)
    cmd_pixel(tmp_path, 0, 0, "R")  # Should edit frame 2 (active)

    g2 = Grid.load(frame_path(tmp_path, 2))
    assert g2.data[0][0] == "R"

    # Frame 1 and 3 untouched
    g1 = Grid.load(frame_path(tmp_path, 1))
    assert g1.data[0][0] == "."
    g3 = Grid.load(frame_path(tmp_path, 3))
    assert g3.data[0][0] == "."


def test_delete_frame_updates_animation_refs_integration(tmp_path):
    """Deleting a frame renumbers and updates animation references correctly."""
    (tmp_path / "palette.txt").write_text("R=#CC3333\n")
    (tmp_path / "grid.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    cmd_frame_add(tmp_path)
    cmd_frame_add(tmp_path)
    cmd_frame_add(tmp_path)
    # 4 frames: 1, 2, 3, 4
    cmd_anim_add(tmp_path, "walk", [1, 2, 3, 4], fps=8, loop=True)

    # Delete frame 2 — frames renumber: 1, 2(was 3), 3(was 4)
    cmd_frame_delete(tmp_path, 2)
    assert discover_frames(tmp_path) == [1, 2, 3]
    anims = load_animations(tmp_path)
    # Frame 2 removed, frames 3→2 and 4→3
    assert anims["walk"]["frames"] == [1, 2, 3]


def test_animated_sprite_dir_fixture(animated_sprite_dir):
    """animated_sprite_dir fixture has expected structure."""
    assert discover_frames(animated_sprite_dir) == [1, 2, 3]
    assert is_animated(animated_sprite_dir)
    anims = load_animations(animated_sprite_dir)
    assert "walk" in anims
    assert anims["walk"]["frames"] == [1, 2, 3]
    assert anims["walk"]["fps"] == 8
    assert anims["walk"]["loop"] is True


# --- cmd_frame_copy_rect ---

def test_frame_copy_rect_copies_region(animated_3_frames):
    """copy-rect copies a rectangular region from one frame to another."""
    g1 = Grid.load(frame_path(animated_3_frames, 1))
    g1.set(0, 0, "R")
    g1.set(0, 1, "B")
    g1.set(1, 0, "G")
    g1.set(1, 1, "R")
    g1.save(frame_path(animated_3_frames, 1))

    g2 = Grid.load(frame_path(animated_3_frames, 2))
    assert g2.data[0][0] == "."

    cmd_frame_copy_rect(animated_3_frames, 0, 0, 1, 1, src_frame=1, dst_frame=2)

    g2 = Grid.load(frame_path(animated_3_frames, 2))
    assert g2.data[0][0] == "R"
    assert g2.data[0][1] == "B"
    assert g2.data[1][0] == "G"
    assert g2.data[1][1] == "R"
    assert g2.data[0][2] == "."


def test_frame_copy_rect_nonexistent_frame_errors(animated_3_frames):
    """copy-rect with non-existent frame raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        cmd_frame_copy_rect(animated_3_frames, 0, 0, 1, 1, src_frame=1, dst_frame=99)


# ===================================================================
# Animation Subdirectory Model — Phase 1: Core Data Model
# ===================================================================

from gridfab.core.animation import (
    resolve_palette_path,
    resolve_config_path,
    is_anim_subdir,
    discover_anim_dirs,
    parse_frame_ref,
    resolve_frame_path,
    load_subdir_animation,
)


# --- resolve_palette_path ---

def test_resolve_palette_path_in_dir(tmp_path):
    """Finds palette.txt in the directory itself."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    assert resolve_palette_path(tmp_path) == tmp_path / "palette.txt"


def test_resolve_palette_path_in_parent(tmp_path):
    """Falls back to parent directory when palette.txt not in dir."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    subdir = tmp_path / "burn"
    subdir.mkdir()
    assert resolve_palette_path(subdir) == tmp_path / "palette.txt"


def test_resolve_palette_path_not_found(tmp_path):
    """Raises FileNotFoundError when palette.txt in neither dir nor parent."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    with pytest.raises(FileNotFoundError, match="palette.txt"):
        resolve_palette_path(subdir)


# --- resolve_config_path ---

def test_resolve_config_path_in_dir(tmp_path):
    """Finds gridfab.json in the directory itself."""
    (tmp_path / "gridfab.json").write_text('{"grid": {"width": 16}}\n')
    assert resolve_config_path(tmp_path) == tmp_path / "gridfab.json"


def test_resolve_config_path_in_parent(tmp_path):
    """Falls back to parent directory."""
    (tmp_path / "gridfab.json").write_text('{"grid": {"width": 16}}\n')
    subdir = tmp_path / "burn"
    subdir.mkdir()
    assert resolve_config_path(subdir) == tmp_path / "gridfab.json"


def test_resolve_config_path_not_found(tmp_path):
    """Returns None when gridfab.json in neither dir nor parent."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    assert resolve_config_path(subdir) is None


# --- is_anim_subdir ---

def test_is_anim_subdir_true(tmp_path):
    """Subdir with frames whose parent has grid.txt is an anim subdir."""
    (tmp_path / "grid.txt").write_text(". .\n")
    subdir = tmp_path / "burn"
    subdir.mkdir()
    (subdir / "frame_001.txt").write_text(". .\n")
    assert is_anim_subdir(subdir) is True


def test_is_anim_subdir_true_parent_has_frames(tmp_path):
    """Subdir with frames whose parent has frame_NNN.txt is an anim subdir."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    subdir = tmp_path / "burn"
    subdir.mkdir()
    (subdir / "frame_001.txt").write_text(". .\n")
    assert is_anim_subdir(subdir) is True


def test_is_anim_subdir_false_no_frames(tmp_path):
    """Subdir without frame files is not an anim subdir."""
    (tmp_path / "grid.txt").write_text(". .\n")
    subdir = tmp_path / "burn"
    subdir.mkdir()
    assert is_anim_subdir(subdir) is False


def test_is_anim_subdir_false_standalone_sprite(tmp_path):
    """Dir with frames but no sprite parent is a standalone sprite, not anim subdir."""
    (tmp_path / "frame_001.txt").write_text(". .\n")
    assert is_anim_subdir(tmp_path) is False


# --- discover_anim_dirs ---

def test_discover_anim_dirs_finds_subdirs(tmp_path):
    """Discovers animation subdirectories with frame files."""
    (tmp_path / "grid.txt").write_text(". .\n")
    burn = tmp_path / "burn"
    burn.mkdir()
    (burn / "frame_001.txt").write_text(". .\n")
    ext = tmp_path / "extinguish"
    ext.mkdir()
    (ext / "frame_001.txt").write_text(". .\n")
    result = discover_anim_dirs(tmp_path)
    assert [d.name for d in result] == ["burn", "extinguish"]


def test_discover_anim_dirs_ignores_non_anim_subdirs(tmp_path):
    """Ignores subdirectories without frame files."""
    (tmp_path / "grid.txt").write_text(". .\n")
    other = tmp_path / "notes"
    other.mkdir()
    (other / "readme.txt").write_text("hello\n")
    assert discover_anim_dirs(tmp_path) == []


def test_discover_anim_dirs_empty(tmp_path):
    """Returns empty list when no subdirectories exist."""
    assert discover_anim_dirs(tmp_path) == []


# --- parse_frame_ref ---

def test_parse_frame_ref_integer():
    """Integer reference returns ('local', N)."""
    assert parse_frame_ref(3) == ("local", 3)


def test_parse_frame_ref_base_string():
    """'base:N' string returns ('base', N)."""
    assert parse_frame_ref("base:3") == ("base", 3)


def test_parse_frame_ref_local_int_in_json():
    """Integer from JSON returns ('local', N)."""
    assert parse_frame_ref(1) == ("local", 1)


def test_parse_frame_ref_invalid():
    """Invalid reference format raises ValueError."""
    with pytest.raises(ValueError, match="invalid frame reference"):
        parse_frame_ref("invalid:3")


# --- resolve_frame_path ---

def test_resolve_frame_path_local(tmp_path):
    """Local int reference resolves to dir/frame_NNN.txt."""
    assert resolve_frame_path(3, tmp_path) == tmp_path / "frame_003.txt"


def test_resolve_frame_path_base(tmp_path):
    """'base:N' reference resolves to parent/frame_NNN.txt."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    assert resolve_frame_path("base:1", subdir) == tmp_path / "frame_001.txt"


# --- load_subdir_animation ---

def test_load_subdir_animation(tmp_path):
    """Loads simplified animation.json from a subdirectory."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    data = {"frames": ["base:1", 1, 2], "fps": 8, "loop": True}
    (subdir / "animation.json").write_text(json.dumps(data))
    result = load_subdir_animation(subdir)
    assert result == data


def test_load_subdir_animation_defaults(tmp_path):
    """Missing fps/loop get defaults."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    (subdir / "animation.json").write_text('{"frames": [1]}')
    result = load_subdir_animation(subdir)
    assert result["fps"] == 8
    assert result["loop"] is True


def test_load_subdir_animation_missing(tmp_path):
    """Missing animation.json returns default empty structure."""
    subdir = tmp_path / "burn"
    subdir.mkdir()
    result = load_subdir_animation(subdir)
    assert result == {"frames": [], "fps": 8, "loop": True}


# --- load_animations with subdirectories ---

def test_load_animations_includes_subdirs(tmp_path):
    """load_animations discovers animation subdirectories."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "frame_001.txt").write_text(". .\n")
    # Old-style animation in root
    save_animations(tmp_path, {"idle": {"frames": [1], "fps": 1, "loop": False}})
    # Subdir animation
    burn = tmp_path / "burn"
    burn.mkdir()
    (burn / "frame_001.txt").write_text(". .\n")
    (burn / "animation.json").write_text(
        '{"frames": ["base:1", 1], "fps": 8, "loop": true}'
    )
    anims = load_animations(tmp_path)
    assert "idle" in anims
    assert "burn" in anims
    assert anims["burn"]["frames"] == ["base:1", 1]


# --- load_config with parent fallback ---

def test_load_config_parent_fallback(tmp_path):
    """load_config falls back to parent directory."""
    from gridfab.core.grid import load_config
    (tmp_path / "gridfab.json").write_text('{"grid": {"width": 16, "height": 16}}\n')
    subdir = tmp_path / "burn"
    subdir.mkdir()
    config = load_config(subdir)
    assert config["grid"]["width"] == 16


# ===================================================================
# Animation Subdirectory Model — Phase 3: anim create, frame ops in subdirs
# ===================================================================

from gridfab.commands.anim_cmd import cmd_anim_create


def test_anim_create_basic(tmp_path):
    """anim create creates subdirectory with animation.json."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "frame_001.txt").write_text(". .\n")
    cmd_anim_create(tmp_path, "burn", fps=8, loop=True)
    burn = tmp_path / "burn"
    assert burn.is_dir()
    assert (burn / "animation.json").exists()
    data = json.loads((burn / "animation.json").read_text())
    assert data == {"frames": [], "fps": 8, "loop": True}


def test_anim_create_custom_fps_loop(tmp_path):
    """anim create respects fps and loop flags."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "grid.txt").write_text(". .\n")
    cmd_anim_create(tmp_path, "slow", fps=4, loop=False)
    data = json.loads((tmp_path / "slow" / "animation.json").read_text())
    assert data["fps"] == 4
    assert data["loop"] is False


def test_anim_create_duplicate_errors(tmp_path):
    """anim create on existing directory raises FileExistsError."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "grid.txt").write_text(". .\n")
    cmd_anim_create(tmp_path, "burn")
    with pytest.raises(FileExistsError, match="burn"):
        cmd_anim_create(tmp_path, "burn")


def test_frame_add_in_subdir_updates_animation_json(tmp_path):
    """frame add in an animation subdir auto-appends to animation.json."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "frame_001.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    burn = tmp_path / "burn"
    burn.mkdir()
    (burn / "animation.json").write_text('{"frames": [], "fps": 8, "loop": true}')
    cmd_frame_add(burn, blank=True)
    # Should have created frame_001.txt in burn/
    assert (burn / "frame_001.txt").exists()
    data = json.loads((burn / "animation.json").read_text())
    assert 1 in data["frames"]


def test_frame_delete_in_subdir_updates_animation_json(tmp_path):
    """frame delete in an animation subdir removes from animation.json."""
    (tmp_path / "palette.txt").write_text("R=#FF0000\n")
    (tmp_path / "frame_001.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    burn = tmp_path / "burn"
    burn.mkdir()
    (burn / "frame_001.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    (burn / "frame_002.txt").write_text(". . . .\n. . . .\n. . . .\n. . . .\n")
    (burn / "animation.json").write_text('{"frames": [1, 2], "fps": 8, "loop": true}')
    cmd_frame_delete(burn, 1)
    data = json.loads((burn / "animation.json").read_text())
    # Frame 1 removed, frame 2 renumbered to 1
    assert data["frames"] == [1]


# ===================================================================
# Animation Subdirectory Model — Phase 2: Commands in subdirs
# ===================================================================


@pytest.fixture
def sprite_with_anim_subdir(tmp_path):
    """Sprite root with base frames + 'burn' animation subdirectory."""
    # Palette in root
    (tmp_path / "palette.txt").write_text("R=#CC3333\nB=#0000FF\nG=#00CC00\n")
    # Base frames in root
    (tmp_path / "frame_001.txt").write_text("R. R. R. R.\nR. R. R. R.\nR. R. R. R.\nR. R. R. R.\n")
    (tmp_path / "frame_002.txt").write_text("B. B. B. B.\nB. B. B. B.\nB. B. B. B.\nB. B. B. B.\n")
    # Animation subdir
    burn = tmp_path / "burn"
    burn.mkdir()
    (burn / "frame_001.txt").write_text("G. G. G. G.\nG. G. G. G.\nG. G. G. G.\nG. G. G. G.\n")
    (burn / "frame_002.txt").write_text(".. .. .. ..\n.. .. .. ..\n.. .. .. ..\n.. .. .. ..\n")
    (burn / "animation.json").write_text(
        json.dumps({"frames": ["base:1", 1, 2], "fps": 8, "loop": True})
    )
    return tmp_path


def test_edit_load_in_subdir(sprite_with_anim_subdir):
    """_load() finds palette in parent dir when in an animation subdir."""
    from gridfab.commands.edit import _load
    burn = sprite_with_anim_subdir / "burn"
    grid, palette, grid_path = _load(burn, frame=1)
    assert "R" in palette.entries
    assert grid_path == burn / "frame_001.txt"


def test_render_in_subdir(sprite_with_anim_subdir):
    """render command works in animation subdirectory."""
    from gridfab.commands.render_cmd import cmd_render
    burn = sprite_with_anim_subdir / "burn"
    cmd_render(burn, frame=1)
    assert (burn / "preview.png").exists()


def test_export_in_subdir(sprite_with_anim_subdir):
    """export command works in animation subdirectory."""
    from gridfab.commands.export_cmd import cmd_export
    burn = sprite_with_anim_subdir / "burn"
    cmd_export(burn, frame=1)
    assert (burn / "output.png").exists()


def test_anim_sheet_with_base_refs(sprite_with_anim_subdir):
    """anim sheet resolves base:N references when in subdirectory."""
    burn = sprite_with_anim_subdir / "burn"
    cmd_anim_sheet(burn, "burn", scale=1)
    assert (burn / "burn_sheet.png").exists()
    assert (burn / "burn_sheet.json").exists()
    # Load metadata — should have 3 frames
    meta = json.loads((burn / "burn_sheet.json").read_text())
    assert len(meta["animations"]["burn"]["frames"]) == 3


def test_anim_gif_with_base_refs(sprite_with_anim_subdir):
    """anim gif resolves base:N references when in subdirectory."""
    burn = sprite_with_anim_subdir / "burn"
    cmd_anim_gif(burn, "burn", scale=1)
    assert (burn / "burn.gif").exists()


def test_anim_sheets_discovers_subdirs(sprite_with_anim_subdir):
    """anim sheets at root discovers and exports subdir animations."""
    from gridfab.commands.anim_cmd import cmd_anim_sheets
    # Also add a root-level animation
    save_animations(sprite_with_anim_subdir,
                    {"idle": {"frames": [1, 2], "fps": 4, "loop": True}})
    cmd_anim_sheets(sprite_with_anim_subdir, scale=1)
    # Root animation exported
    assert (sprite_with_anim_subdir / "idle_sheet.png").exists()
    # Subdir animation exported
    assert (sprite_with_anim_subdir / "burn" / "burn_sheet.png").exists()


def test_clean_recurses_into_subdirs(sprite_with_anim_subdir):
    """clean removes generated files from animation subdirectories too."""
    from gridfab.commands.edit import cmd_clean_files
    burn = sprite_with_anim_subdir / "burn"
    # Create files that clean should remove
    (burn / "preview.png").write_text("fake")
    (burn / "output_2x.png").write_text("fake")
    (sprite_with_anim_subdir / "preview.png").write_text("fake")
    cmd_clean_files(sprite_with_anim_subdir)
    assert not (sprite_with_anim_subdir / "preview.png").exists()
    assert not (burn / "preview.png").exists()
    assert not (burn / "output_2x.png").exists()


# --- Relative path (Path(".")) tests ---
# These verify that functions relying on directory.parent work correctly
# when called with Path(".") (the default CLI argument), where
# Path(".").parent == Path(".") and Path(".").name == "".

def test_is_anim_subdir_with_relative_path(sprite_with_anim_subdir, monkeypatch):
    """is_anim_subdir works when called with Path('.') from inside a subdir."""
    from gridfab.core.animation import is_anim_subdir
    # From inside burn/, Path(".") should be detected as anim subdir
    monkeypatch.chdir(sprite_with_anim_subdir / "burn")
    assert is_anim_subdir(Path(".")) is True
    # From the sprite root, Path(".") should NOT be detected as anim subdir
    monkeypatch.chdir(sprite_with_anim_subdir)
    assert is_anim_subdir(Path(".")) is False


def test_resolve_palette_path_with_relative_path(sprite_with_anim_subdir, monkeypatch):
    """resolve_palette_path finds parent palette when called with Path('.')."""
    from gridfab.core.animation import resolve_palette_path
    monkeypatch.chdir(sprite_with_anim_subdir / "burn")
    result = resolve_palette_path(Path("."))
    assert result.name == "palette.txt"
    assert result.exists()


def test_resolve_frame_path_base_ref_with_relative_path(sprite_with_anim_subdir, monkeypatch):
    """resolve_frame_path resolves 'base:1' correctly from Path('.')."""
    from gridfab.core.animation import resolve_frame_path
    monkeypatch.chdir(sprite_with_anim_subdir / "burn")
    result = resolve_frame_path("base:1", Path("."))
    assert result.exists()
    assert result.name == "frame_001.txt"
    # Should point to parent's frame, not burn's frame
    assert result.parent == sprite_with_anim_subdir


def test_anim_sheet_with_relative_path(sprite_with_anim_subdir, monkeypatch):
    """anim sheet works when called with Path('.') from inside a subdir."""
    monkeypatch.chdir(sprite_with_anim_subdir / "burn")
    cmd_anim_sheet(Path("."), "burn", scale=1)
    assert (sprite_with_anim_subdir / "burn" / "burn_sheet.png").exists()


def test_anim_gif_with_relative_path(sprite_with_anim_subdir, monkeypatch):
    """anim gif works when called with Path('.') from inside a subdir."""
    monkeypatch.chdir(sprite_with_anim_subdir / "burn")
    cmd_anim_gif(Path("."), "burn", scale=1)
    assert (sprite_with_anim_subdir / "burn" / "burn.gif").exists()
