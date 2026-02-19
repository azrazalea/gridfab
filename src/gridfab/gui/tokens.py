"""Design tokens for GridFab GUI — VS Code Dark+ inspired theme.

All values are plain strings/ints so this module has zero tkinter imports.
CTkFont objects require a root window, so fonts are stored as tuples.
"""

# ── Backgrounds ──────────────────────────────────────────────────────
BG_BASE = "#1E1E1E"         # Canvas / main area
BG_SURFACE = "#252526"      # Side panels
BG_ELEVATED = "#2D2D2D"     # Toolbar, status bar, frame strip
BG_WIDGET = "#3C3C3C"       # Input fields, spinboxes

# ── Text ─────────────────────────────────────────────────────────────
TEXT_PRIMARY = "#CCCCCC"     # Main text
TEXT_SECONDARY = "#858585"   # Labels, hints
TEXT_DISABLED = "#5A5A5A"    # Disabled items

# ── Accent ───────────────────────────────────────────────────────────
ACCENT = "#007ACC"           # Selected tool, active frame, focus rings
ACCENT_HOVER = "#1C8AD4"    # Hover on accent items
ACCENT_PRESSED = "#005A9E"  # Pressed accent

# ── Borders ──────────────────────────────────────────────────────────
BORDER = "#3E3E3E"           # Panel separators
BORDER_FOCUS = "#007ACC"     # Focused input borders

# ── Semantic colors ──────────────────────────────────────────────────
SELECTED_UNFOCUS = "#094771" # Multi-selected but not active
HOVER_BUTTON = "#404040"     # Button hover
ACTIVE_BUTTON = "#37373D"   # Active/pressed button

# ── Swatch selection ─────────────────────────────────────────────────
SWATCH_SELECTED_BORDER = ACCENT
SWATCH_SELECTED_WIDTH = 2

# ── Grid lines (on dark canvas) ─────────────────────────────────────
GRID_LINE_COLOR = "#333333"
GRID_LINE_COLOR_DARK = "#2A2A2A"  # Alternative for dark bg

# ── Menu styling ─────────────────────────────────────────────────────
MENU_BG = BG_ELEVATED
MENU_FG = TEXT_PRIMARY
MENU_ACTIVE_BG = ACCENT
MENU_ACTIVE_FG = "#FFFFFF"
MENU_DISABLED_FG = TEXT_DISABLED

# ── Tooltip ──────────────────────────────────────────────────────────
TOOLTIP_BG = "#383838"
TOOLTIP_FG = TEXT_PRIMARY
TOOLTIP_BORDER = "#505050"

# ── Spacing (4px grid) ──────────────────────────────────────────────
PAD_XS = 2
PAD_SM = 4
PAD_MD = 8
PAD_LG = 12
PAD_XL = 16
PAD_2X = 20

# ── Component heights ───────────────────────────────────────────────
TOOLBAR_HEIGHT = 36
STATUS_BAR_HEIGHT = 22
FRAME_STRIP_HEIGHT = 50
PALETTE_WIDTH = 260

# ── Font tuples (family, size[, weight]) ─────────────────────────────
FONT_BODY = ("Segoe UI", 11)
FONT_BODY_BOLD = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 11, "bold")
FONT_HEADER = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 12)
FONT_MONO_SMALL = ("Consolas", 10)
FONT_STATUS = ("Consolas", 12)
FONT_TOOLTIP = ("Segoe UI", 10)
