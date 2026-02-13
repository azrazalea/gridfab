"""Shared pytest fixtures for GridFab tests."""

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
