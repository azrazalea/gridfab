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
