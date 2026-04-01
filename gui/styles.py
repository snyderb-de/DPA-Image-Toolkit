"""
Styling and theming for DPA Image Toolkit GUI.

Modern, minimal glass-morphism aesthetic with light/dark mode.
Orange accent color. Grey and black/white base colors.
"""

# Color Schemes - Modern Glass-morphism Design
LIGHT_MODE = {
    "bg_primary": "#f5f5f5",       # Main window background (light grey)
    "bg_secondary": "#ffffff",     # Panels - white glass effect
    "bg_tertiary": "#efefef",      # Hover states - subtle grey
    "fg_primary": "#1a1a1a",       # Primary text (near black)
    "fg_secondary": "#4a4a4a",     # Secondary text (grey)
    "fg_tertiary": "#7a7a7a",      # Tertiary text (muted grey)
    "border": "#d0d0d0",           # Subtle border
    "accent": "#ff8800",           # Orange accent for actions
    "success": "#22c55e",          # Green success
    "warning": "#eab308",          # Yellow warning
    "error": "#ef4444",            # Red error
}

DARK_MODE = {
    "bg_primary": "#0f0f0f",       # Main window background (near black)
    "bg_secondary": "#1a1a1a",     # Panels - dark glass effect
    "bg_tertiary": "#262626",      # Hover states - subtle lighter
    "fg_primary": "#f5f5f5",       # Primary text (light grey)
    "fg_secondary": "#d0d0d0",     # Secondary text (grey)
    "fg_tertiary": "#808080",      # Tertiary text (muted grey)
    "border": "#333333",           # Subtle border
    "accent": "#ff8800",           # Orange accent (same)
    "success": "#22c55e",          # Green success
    "warning": "#eab308",          # Yellow warning
    "error": "#ef4444",            # Red error
}

# Font Definitions
FONTS = {
    "title": ("Segoe UI", 14, "bold"),
    "heading": ("Segoe UI", 12, "bold"),
    "normal": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "monospace": ("Courier New", 9),
}

# Component Styling
BUTTON_STYLE = {
    "corner_radius": 4,
    "border_width": 1,
    "height": 36,
}

ENTRY_STYLE = {
    "corner_radius": 4,
    "border_width": 1,
    "height": 32,
}

PANEL_STYLE = {
    "corner_radius": 4,
    "border_width": 1,
}

PROGRESSBAR_STYLE = {
    "corner_radius": 3,
    "border_width": 0,
    "height": 8,
}

TEXTBOX_STYLE = {
    "corner_radius": 4,
    "border_width": 1,
}


def get_theme(dark_mode=True):
    """
    Get the active color scheme.

    Args:
        dark_mode (bool): If True, return dark mode colors. Otherwise light mode.

    Returns:
        dict: Color scheme dictionary
    """
    return DARK_MODE if dark_mode else LIGHT_MODE


def get_font(font_type="normal"):
    """
    Get a font tuple.

    Args:
        font_type (str): Type of font ('title', 'heading', 'normal', 'small', 'monospace')

    Returns:
        tuple: Font specification (family, size, style)
    """
    return FONTS.get(font_type, FONTS["normal"])
