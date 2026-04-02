"""
Styling and theming for DPA Image Toolkit GUI.

Modern design system with rich dark/light palettes, sidebar layout,
card-based components, and orange accent throughout.
"""

# ── Dark Mode ──────────────────────────────────────────────────────────────────
DARK_MODE = {
    # Backgrounds (layered depth)
    "bg_base":        "#0D1117",   # window root — deepest
    "bg_primary":     "#161B22",   # main content area
    "bg_secondary":   "#232A33",   # cards / panels
    "bg_tertiary":    "#343C46",   # hover / input / nested
    "bg_sidebar":     "#010409",   # sidebar rail

    # Foregrounds
    "fg_primary":     "#E6EDF3",   # headings / primary text
    "fg_secondary":   "#A7B0BA",   # subtext / labels
    "fg_tertiary":    "#6E7681",   # muted / placeholders

    # Accent (orange)
    "accent":         "#F97316",   # primary actions
    "accent_hover":   "#EA580C",   # hover state
    "accent_dim":     "#1F1109",   # accent-tinted background
    "accent_text":    "#FFFFFF",   # text on accent buttons

    # Sidebar-specific
    "sidebar_fg":     "#B4BDC8",   # sidebar nav text
    "sidebar_fg_active": "#F97316",   # active nav item text
    "sidebar_bg_active": "#2B1C0E",   # active nav item bg
    "sidebar_hover":  "#212A33",   # hover on nav item

    # Semantic
    "success":        "#3FB950",
    "success_dim":    "#0A1F0F",
    "warning":        "#E3B341",
    "warning_dim":    "#1F1600",
    "error":          "#F85149",
    "error_dim":      "#200D0C",

    # Borders / dividers
    "border":         "#3A424D",
    "border_subtle":  "#2A313A",

    # Progress bar track
    "progress_track": "#343C46",
}

# ── Light Mode ─────────────────────────────────────────────────────────────────
LIGHT_MODE = {
    # Backgrounds
    "bg_base":        "#F0F2F5",
    "bg_primary":     "#F4F7FB",
    "bg_secondary":   "#FFFFFF",
    "bg_tertiary":    "#E6EBF2",
    "bg_sidebar":     "#EEF2F7",

    # Foregrounds
    "fg_primary":     "#1F2328",
    "fg_secondary":   "#475467",
    "fg_tertiary":    "#667085",

    # Accent
    "accent":         "#EA580C",
    "accent_hover":   "#C2410C",
    "accent_dim":     "#FFF1E6",
    "accent_text":    "#FFFFFF",

    # Sidebar-specific
    "sidebar_fg":     "#344054",
    "sidebar_fg_active": "#EA580C",
    "sidebar_bg_active": "#FFE9D5",
    "sidebar_hover":  "#DCE3EC",

    # Semantic
    "success":        "#1A7F37",
    "success_dim":    "#DCFCE7",
    "warning":        "#9A6700",
    "warning_dim":    "#FEF9C3",
    "error":          "#CF222E",
    "error_dim":      "#FEE2E2",

    # Borders
    "border":         "#C4CDD8",
    "border_subtle":  "#D9E1EA",

    # Progress bar track
    "progress_track": "#D7DEE8",
}

# ── Typography ─────────────────────────────────────────────────────────────────
FONTS = {
    "display":   ("Segoe UI", 24, "bold"),   # hero titles
    "title":     ("Segoe UI", 18, "bold"),   # panel headings
    "heading":   ("Segoe UI", 15, "bold"),   # card headings
    "subheading":("Segoe UI", 13, "bold"),   # sub-sections
    "normal":    ("Segoe UI", 13),           # body text
    "small":     ("Segoe UI", 12),           # labels / metadata
    "micro":     ("Segoe UI", 11),           # fine print
    "mono":      ("Consolas", 12),           # log / code
    "mono_sm":   ("Consolas", 11),
    "nav":       ("Segoe UI", 14),           # sidebar nav items
    "nav_bold":  ("Segoe UI", 14, "bold"),
}

# ── Component Tokens ───────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 220

RADIUS = {
    "sm":   4,
    "md":   8,
    "lg":   12,
    "xl":   16,
    "pill": 999,
}

BUTTON = {
    "height_lg": 44,
    "height_md": 36,
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
    "pad_x": 16,
    "pad_y": 14,
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
