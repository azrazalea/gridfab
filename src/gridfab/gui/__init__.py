"""GridFab GUI package — re-exports all public names for backward compatibility."""

# Pure functions and constants (always available, no tkinter needed)
from gridfab.gui.pure import (  # noqa: F401
    ZOOM_LEVELS, DEFAULT_CELL_SIZE, CHECKER_LIGHT, CHECKER_DARK,
    TOOL_BRUSH, TOOL_EYEDROPPER, TOOL_FILL, SWATCH_COLS,
    checker_color, _contrast_color, format_status_text, grid_line_config,
    zoom_step, cell_at_coords, fit_zoom_level, cursor_preview_color,
    palette_key_to_index, palette_index_to_alias, render_frame_thumbnail,
    frame_strip_layout, blend_hex_colors, onion_skin_color,
    playback_frame_sequence, frame_interval_ms, frame_cell_at_coords,
    side_by_side_layout, anim_dir_choices, eyedropper_pick,
    cell_display_color,
)


def __getattr__(name):
    """Lazy import for PixelEditor and main to avoid importing tkinter in tests."""
    if name in ("PixelEditor", "main"):
        from gridfab.gui.app import PixelEditor, main
        return {"PixelEditor": PixelEditor, "main": main}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
