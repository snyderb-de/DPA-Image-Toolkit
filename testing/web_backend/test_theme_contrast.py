import re
import unittest
from pathlib import Path


TOKEN_CSS = Path(__file__).resolve().parents[2] / "web" / "static" / "tokens.css"
AA_NORMAL = 4.5


def _parse_vars():
    css = TOKEN_CSS.read_text(encoding="utf-8")
    blocks = {}
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]+)\}", css, re.S):
        selectors = match.group("selectors")
        body = match.group("body")
        values = dict(re.findall(r"--([a-zA-Z0-9-]+):\s*([^;]+);", body))
        if "[data-theme=\"dark\"]" in selectors:
            blocks["dark"] = values
        elif "[data-theme=\"light\"]" in selectors:
            blocks["light"] = values
    return blocks


def _hex_to_rgb(value):
    value = value.strip().lower()
    if value == "#fff":
        value = "#ffffff"
    if value == "#000":
        value = "#000000"
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _rgba(value):
    parts = [float(p.strip()) for p in re.search(r"rgba\(([^)]+)\)", value).group(1).split(",")]
    return (parts[0] / 255, parts[1] / 255, parts[2] / 255, parts[3])


def _composite(foreground, background):
    r, g, b, alpha = foreground
    return tuple(alpha * c + (1 - alpha) * bg for c, bg in zip((r, g, b), background))


def _linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(rgb):
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(foreground, background):
    l1, l2 = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _theme(name):
    return _parse_vars()[name]


def _contrast_pair(theme_name, fg_var, bg_var):
    values = _theme(theme_name)
    return _contrast(_hex_to_rgb(values[fg_var]), _hex_to_rgb(values[bg_var]))


def _contrast_overlay_pair(theme_name, fg_var, overlay_var, base_var):
    values = _theme(theme_name)
    background = _composite(_rgba(values[overlay_var]), _hex_to_rgb(values[base_var]))
    return _contrast(_hex_to_rgb(values[fg_var]), background)


class ThemeContrastTests(unittest.TestCase):
    def assert_aa(self, ratio, label):
        self.assertGreaterEqual(ratio, AA_NORMAL, f"{label} is {ratio:.2f}:1")

    def test_text_tokens_meet_wcag_aa_on_primary_surfaces(self):
        for theme_name in ("dark", "light"):
            for fg_var in ("ink", "muted", "faint", "accent"):
                for bg_var in ("bg", "panel", "panel2"):
                    with self.subTest(theme=theme_name, foreground=fg_var, background=bg_var):
                        self.assert_aa(
                            _contrast_pair(theme_name, fg_var, bg_var),
                            f"{theme_name} {fg_var} on {bg_var}",
                        )

    def test_filled_control_text_meets_wcag_aa(self):
        for theme_name in ("dark", "light"):
            for fg_var, bg_var in (
                ("accent-text", "accent-fill"),
                ("warn-text", "warn"),
                ("err-text", "err"),
            ):
                with self.subTest(theme=theme_name, foreground=fg_var, background=bg_var):
                    self.assert_aa(
                        _contrast_pair(theme_name, fg_var, bg_var),
                        f"{theme_name} {fg_var} on {bg_var}",
                    )

    def test_sidebar_text_meets_wcag_aa(self):
        for theme_name in ("dark", "light"):
            for fg_var in ("sidebar-ink", "sidebar-ink-act", "sidebar-brand-ink", "accent"):
                with self.subTest(theme=theme_name, foreground=fg_var):
                    self.assert_aa(
                        _contrast_pair(theme_name, fg_var, "sidebar-bg"),
                        f"{theme_name} {fg_var} on sidebar-bg",
                    )

    def test_status_banner_text_meets_wcag_aa(self):
        for theme_name in ("dark", "light"):
            for fg_var, overlay_var in (
                ("muted", "accent-dim"),
                ("ok", "ok-dim"),
                ("warn", "warn-dim"),
                ("err", "err-dim"),
            ):
                with self.subTest(theme=theme_name, foreground=fg_var, overlay=overlay_var):
                    self.assert_aa(
                        _contrast_overlay_pair(theme_name, fg_var, overlay_var, "bg"),
                        f"{theme_name} {fg_var} on {overlay_var}/bg",
                    )
