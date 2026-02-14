"""Shared pytest fixtures for GridFab tests."""

import json

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_grid(tmp_path: Path) -> Path:
    """Create a minimal 4x4 grid.txt in a temp directory."""
    grid_path = tmp_path / "grid.txt"
    grid_path.write_text(
        ". . R R\n"
        ". R R .\n"
        "R R . .\n"
        "R . . .\n"
    )
    return tmp_path


@pytest.fixture
def sample_palette(tmp_path: Path) -> Path:
    """Create a sample palette.txt in a temp directory."""
    palette_path = tmp_path / "palette.txt"
    palette_path.write_text(
        "# Test palette\n"
        "R=#CC3333\n"
        "B=#0000FF\n"
        "SK=#FFCCAA\n"
    )
    return tmp_path


@pytest.fixture
def sample_sprite(tmp_path: Path) -> Path:
    """Create a complete sprite directory with grid.txt and palette.txt."""
    (tmp_path / "grid.txt").write_text(
        ". . R R\n"
        ". R R .\n"
        "R R . .\n"
        "R . . .\n"
    )
    (tmp_path / "palette.txt").write_text(
        "# Test palette\n"
        "R=#CC3333\n"
    )
    return tmp_path


@pytest.fixture
def sprite_dir(tmp_path: Path) -> Path:
    """Create a 4x4 sprite directory ready for command tests."""
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


@pytest.fixture
def sprite_dir_with_config(sprite_dir: Path) -> Path:
    """Sprite directory with gridfab.json config (needed for export tests)."""
    config = {
        "grid": {"width": 4, "height": 4},
        "export": {"scales": [1, 2]},
    }
    (sprite_dir / "gridfab.json").write_text(json.dumps(config, indent=2) + "\n")
    return sprite_dir
