"""
Shared styling tokens for the DPA Image Toolkit GUI.

The visual direction follows a preservation-lab look with layered
slate surfaces in dark mode and cooler archive-paper blues in light mode.
"""

# ── Dark Mode ──────────────────────────────────────────────────────────────────
DARK_MODE = {
    # Backgrounds
    "bg_base":        "#171B21",
    "bg_primary":     "#1D2229",
    "bg_secondary":   "#262C34",
    "bg_tertiary":    "#313844",
    "bg_sidebar":     "#1B2026",
    "bg_topbar":      "#313844",
    "bg_glass":       "#2B333D",

    # Foregrounds
    "fg_primary":     "#E6ECF3",
    "fg_secondary":   "#C2CDD8",
    "fg_tertiary":    "#94A3B8",
    "fg_inverse":     "#1B2530",

    # Accent (muted preservation blue)
    "accent":         "#7A9BBC",
    "accent_hover":   "#6B8CAF",
    "accent_dim":     "#243242",
    "accent_text":    "#FFFFFF",

    # Sidebar-specific
    "sidebar_fg":     "#BDC7D2",
    "sidebar_fg_active": "#D7E5F4",
    "sidebar_bg_active": "#2C3846",
    "sidebar_hover":  "#26303B",

    # Semantic
    "success":        "#74B79A",
    "success_dim":    "#1F312A",
    "warning":        "#C8AA72",
    "warning_dim":    "#3A3020",
    "error":          "#D98982",
    "error_dim":      "#3A2426",

    # Borders / dividers
    "border":         "#3E4A58",
    "border_subtle":  "#333C47",

    # Progress bar track
    "progress_track": "#3A4451",
}

# ── Light Mode ─────────────────────────────────────────────────────────────────
LIGHT_MODE = {
    # Backgrounds
    "bg_base":        "#E9EEF5",
    "bg_primary":     "#F3F7FC",
    "bg_secondary":   "#FFFFFF",
    "bg_tertiary":    "#E5ECF4",
    "bg_sidebar":     "#E6EDF6",
    "bg_topbar":      "#D7E1EC",
    "bg_glass":       "#F4F8FD",

    # Foregrounds
    "fg_primary":     "#1F2A37",
    "fg_secondary":   "#475569",
    "fg_tertiary":    "#64748B",
    "fg_inverse":     "#FFF9F0",

    # Accent
    "accent":         "#5D7695",
    "accent_hover":   "#4C6685",
    "accent_dim":     "#E7EEF7",
    "accent_text":    "#FFFFFF",

    # Sidebar-specific
    "sidebar_fg":     "#526274",
    "sidebar_fg_active": "#37506C",
    "sidebar_bg_active": "#DCE6F2",
    "sidebar_hover":  "#DCE5EF",

    # Semantic
    "success":        "#3E7C62",
    "success_dim":    "#DCEEE6",
    "warning":        "#8A6A3F",
    "warning_dim":    "#F2E7D5",
    "error":          "#B4534B",
    "error_dim":      "#F8DEDB",

    # Borders
    "border":         "#C7D3E0",
    "border_subtle":  "#DCE5EF",

    # Progress bar track
    "progress_track": "#D7E0EA",
}

# ── Typography ─────────────────────────────────────────────────────────────────
FONTS = {
    "display":   ("Georgia", 30, "bold"),
    "title":     ("Georgia", 24, "bold"),
    "heading":   ("Georgia", 16, "bold"),
    "subheading":("Segoe UI", 13, "bold"),
    "normal":    ("Segoe UI", 13),
    "small":     ("Segoe UI", 12),
    "micro":     ("Segoe UI", 11),
    "eyebrow":   ("Segoe UI", 10, "bold"),
    "mono":      ("Consolas", 12),
    "mono_sm":   ("Consolas", 11),
    "nav":       ("Segoe UI", 11, "bold"),
    "nav_bold":  ("Segoe UI", 11, "bold"),
    "brand":     ("Georgia", 22, "bold"),
    "brand_sm":  ("Georgia", 16, "italic"),
}

# ── Component Tokens ───────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 220

RADIUS = {
    "sm":   4,
    "md":   8,
    "lg":   14,
    "xl":   20,
    "pill": 999,
}

BUTTON = {
    "height_lg": 46,
    "height_md": 38,
    "height_sm": 28,
    "corner_radius": RADIUS["md"],
}

INPUT = {
    "height": 36,
    "corner_radius": RADIUS["md"],
    "border_width": 1,
}

CARD = {
    "corner_radius": RADIUS["lg"],
    "border_width": 1,
    "pad_x": 18,
    "pad_y": 16,
}

PROGRESS = {
    "height_thin": 3,
    "height_normal": 6,
    "corner_radius": RADIUS["pill"],
}

# ── Log level colors (used as tag colors in textbox) ──────────────────────────
LOG_PREFIXES = {
    "info":    ("ℹ ", "info"),
    "success": ("✓ ", "success"),
    "warning": ("⚠ ", "warning"),
    "error":   ("✕ ", "error"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_theme(dark_mode: bool = True) -> dict:
    """Return the active color scheme dict."""
    return DARK_MODE if dark_mode else LIGHT_MODE


def get_font(font_type: str = "normal") -> tuple:
    """Return a font tuple by name."""
    return FONTS.get(font_type, FONTS["normal"])
