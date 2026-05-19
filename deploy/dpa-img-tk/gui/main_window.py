"""
Main application window for DPA Image Toolkit.

Sidebar-navigation layout with light/dark/system appearance, card-based content panels,
and a docked status bar with a thin progress indicator.
"""

import json
import os
import sys
from pathlib import Path

import customtkinter as ctk
from .styles import (
    get_theme, get_font,
    SIDEBAR_WIDTH, BUTTON, CARD, PROGRESS, RADIUS,
)


SETTINGS_FILENAME = "app-settings.json"
SETTINGS_ENV_VAR = "DPA_IMAGE_TOOLKIT_SETTINGS"
APPEARANCE_MODES = {"light", "dark", "system"}
APPEARANCE_MENU_LABELS = {
    "system": "System",
    "light": "Light",
    "dark": "Dark",
}
APPEARANCE_MENU_LABEL_TO_MODE = {
    label: mode for mode, label in APPEARANCE_MENU_LABELS.items()
}


def _resolve_env_settings_path(raw_path: str) -> Path:
    """Resolve env var path, allowing either a file or directory path."""
    candidate = Path(raw_path).expanduser()
    if candidate.suffix:
        return candidate
    return candidate / SETTINGS_FILENAME


def _get_settings_path() -> Path:
    """
    Return settings file path.

    Priority:
    1. `DPA_IMAGE_TOOLKIT_SETTINGS` environment variable (file or directory)
    2. `<launch_dir>/app-settings.json` (same folder as the launched script)
    """
    env_path = os.environ.get(SETTINGS_ENV_VAR, "").strip()
    if env_path:
        return _resolve_env_settings_path(env_path)

    launch_target = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path.cwd()
    launch_dir = launch_target.parent
    return launch_dir / SETTINGS_FILENAME


def _load_app_settings() -> dict:
    """Load settings JSON. Returns empty dict if missing or invalid."""
    path = _get_settings_path()
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _save_app_settings(settings: dict) -> bool:
    """Persist settings JSON atomically. Returns True on success."""
    path = _get_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, sort_keys=True)
        temp_path.replace(path)
        return True
    except Exception:
        return False


def _normalize_appearance_mode(raw_value) -> str:
    """Normalize appearance mode input to one of: system, light, dark."""
    value = str(raw_value or "").strip().lower()
    if value in APPEARANCE_MODES:
        return value
    return "light"


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # ── Window setup ───────────────────────────────────────────────────────
        self.title("DPA Image Toolkit")
        self._set_window_geometry_top_aligned(1300, 950)
        self.minsize(1200, 860)

        # ── State ──────────────────────────────────────────────────────────────
        self.app_settings = _load_app_settings()
        saved_mode = self.app_settings.get("appearance_mode")
        if isinstance(saved_mode, str):
            self.appearance_mode = _normalize_appearance_mode(saved_mode)
        else:
            self.appearance_mode = "dark" if bool(self.app_settings.get("dark_mode", False)) else "light"
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")
        self.current_theme = get_theme(self._is_effective_dark_mode())
        self.current_panel = "menu"
        self.operation_in_progress = False
        self.operation_type = None
        self.sidebar_dividers = []
        self.status_panel_label = None
        self.status_meta_label = None

        # ── Root grid: sidebar | right-column ─────────────────────────────────
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_right_column()

    def get_last_source_directory(self):
        """Return the last selected source directory if available."""
        value = self.app_settings.get("last_source_directory")
        if not isinstance(value, str) or not value.strip():
            return None

        path = Path(value).expanduser()
        return path if path.is_dir() else None

    def set_last_source_directory(self, folder_path):
        """Persist the last selected source directory."""
        try:
            path = Path(folder_path).expanduser()
        except Exception:
            return

        if not path.is_dir():
            return

        self.app_settings["last_source_directory"] = str(path)
        _save_app_settings(self.app_settings)

    def _is_effective_dark_mode(self) -> bool:
        """
        Return whether the currently active appearance is dark.

        CustomTkinter resolves "system" mode internally to dark or light.
        """
        resolved = str(ctk.get_appearance_mode() or "").strip().lower()
        if resolved == "dark":
            return True
        if resolved == "light":
            return False
        return self.appearance_mode == "dark"

    def _persist_appearance_setting(self):
        """Save appearance mode, while preserving legacy dark_mode compatibility."""
        self.app_settings["appearance_mode"] = self.appearance_mode
        self.app_settings["dark_mode"] = self.appearance_mode == "dark"
        _save_app_settings(self.app_settings)

    def _set_appearance_mode(self, mode: str, persist: bool = True):
        """Apply appearance mode, refresh theme, and optionally persist setting."""
        self.appearance_mode = _normalize_appearance_mode(mode)
        ctk.set_appearance_mode(self.appearance_mode)
        if persist:
            self._persist_appearance_setting()
        self.current_theme = get_theme(self._is_effective_dark_mode())
        self._apply_theme()

    # ══════════════════════════════════════════════════════════════════════════
    # Sidebar
    # ══════════════════════════════════════════════════════════════════════════

    def _set_window_geometry_top_aligned(self, width: int, height: int):
        screen_width = self.winfo_screenwidth()
        x = max((screen_width - width) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+0")

    def _build_sidebar(self):
        t = self.current_theme

        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            fg_color=t["bg_sidebar"],
            corner_radius=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)   # spacer pushes bottom
        self.sidebar.grid_columnconfigure(0, weight=1)

        # ── Brand ──────────────────────────────────────────────────────────────
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        brand_inner = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_inner.pack(fill="x", padx=20, pady=(28, 24))

        title_lbl = ctk.CTkLabel(
            brand_inner,
            text="DPA\nImage\nToolkit",
            font=get_font("brand"),
            text_color=t["accent"],
            justify="left",
        )
        title_lbl.pack(anchor="w")
        self.brand_title_lbl = title_lbl

        for widget in (brand_inner, title_lbl):
            widget.bind("<Button-1>", lambda _event: self._on_home())

        # Divider
        self._sidebar_divider()

        # ── Nav items ──────────────────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        section_lbl = ctk.CTkLabel(
            nav_frame,
            text="TOOLS",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
        )
        section_lbl.pack(anchor="w", padx=20, pady=(16, 8))
        self.section_lbl = section_lbl

        self._nav_items = {}
        nav_defs = [
            ("auto_crop", "✂",  "AUTO CROP"),
            ("tiff_merge","⊞",  "MERGE TIFFS"),
            ("tiff_split","⇵",  "SPLIT TIFFS"),
            ("add_border","▣",  "ADD BORDER"),
            ("ocr_pdf",   "⎘",  "OCR TO PDF"),
            ("pdf_conversion", "🗎", "PDF TOOLS"),
        ]
        for key, icon, label in nav_defs:
            btn = self._make_nav_button(nav_frame, icon, label, key)
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_items[key] = btn

        # Spacer
        ctk.CTkFrame(self.sidebar, fg_color="transparent").grid(row=2, column=0)

        # Divider
        self._sidebar_divider(row=3)

        # ── Appearance mode ────────────────────────────────────────────────────
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=(0, 20))

        theme_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=20, pady=12)

        theme_header = ctk.CTkFrame(theme_row, fg_color="transparent")
        theme_header.pack(fill="x")

        theme_lbl = ctk.CTkLabel(
            theme_header,
            text="Appearance",
            font=get_font("small"),
            text_color=t["fg_secondary"],
        )
        theme_lbl.pack(side="left")
        self.theme_text_lbl = theme_lbl

        self.theme_mode_var = ctk.StringVar(
            value=APPEARANCE_MENU_LABELS.get(self.appearance_mode, "Light")
        )
        self.theme_mode_menu = ctk.CTkOptionMenu(
            theme_row,
            values=[
                APPEARANCE_MENU_LABELS["system"],
                APPEARANCE_MENU_LABELS["light"],
                APPEARANCE_MENU_LABELS["dark"],
            ],
            variable=self.theme_mode_var,
            command=self._on_appearance_mode_selected,
            font=get_font("small"),
            dropdown_font=get_font("small"),
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
            dynamic_resizing=False,
        )
        self.theme_mode_menu.pack(fill="x", pady=(8, 0))

        # Version tag
        ver_lbl = ctk.CTkLabel(
            bottom_frame,
            text="v1.0",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
        )
        ver_lbl.pack(anchor="center")
        self.ver_lbl = ver_lbl

        self._update_nav_highlight("menu")

    def _sidebar_divider(self, row=None):
        t = self.current_theme
        if row is not None:
            div = ctk.CTkFrame(
                self.sidebar,
                fg_color=t["border"],
                height=1,
                corner_radius=0,
            )
            div.grid(row=row, column=0, sticky="ew", padx=0, pady=0)
            self.sidebar_dividers.append(div)
        else:
            div = ctk.CTkFrame(
                self.sidebar,
                fg_color=t["border"],
                height=1,
                corner_radius=0,
            )
            div.grid_remove()
            self.sidebar_dividers.append(div)
            return div

    def _make_nav_button(self, parent, icon, label, key):
        t = self.current_theme
        btn = ctk.CTkButton(
            parent,
            text=f"  {icon}   {label}",
            font=get_font("nav"),
            height=40,
            corner_radius=RADIUS["md"],
            anchor="w",
            fg_color="transparent",
            text_color=t["sidebar_fg"],
            hover_color=t["sidebar_hover"],
            border_width=0,
            command=lambda k=key: self._nav_click(k),
        )
        return btn

    def _nav_click(self, key):
        if key == "auto_crop":
            self._show_auto_crop_panel()
        elif key == "tiff_merge":
            self._show_tiff_merge_panel()
        elif key == "tiff_split":
            self._show_tiff_split_panel()
        elif key == "add_border":
            self._show_add_border_panel()
        elif key == "ocr_pdf":
            self._show_ocr_pdf_panel()
        elif key == "pdf_conversion":
            self._show_pdf_conversion_panel()

    def _update_nav_highlight(self, active_key):
        t = self.current_theme
        for key, btn in self._nav_items.items():
            if key == active_key:
                btn.configure(
                    fg_color=t["sidebar_bg_active"],
                    text_color=t["sidebar_fg_active"],
                    font=get_font("nav_bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=t["sidebar_fg"],
                    font=get_font("nav"),
                )

    # ══════════════════════════════════════════════════════════════════════════
    # Right column (content + status bar)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_right_column(self):
        t = self.current_theme

        right_col = ctk.CTkFrame(self, fg_color=t["bg_primary"], corner_radius=0)
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(0, weight=1)
        right_col.grid_columnconfigure(0, weight=1)
        self.right_col = right_col

        # Content area
        self.content = ctk.CTkFrame(right_col, fg_color="transparent", corner_radius=0)
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.panel_container = ctk.CTkFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
        )
        self.panel_container.grid(row=0, column=0, sticky="nsew")
        self.panel_container.grid_rowconfigure(0, weight=1)
        self.panel_container.grid_columnconfigure(0, weight=1)

        # Status bar
        self._build_status_bar(right_col)

        # Show menu
        self._show_menu()

    def _build_status_bar(self, parent):
        t = self.current_theme

        bar = ctk.CTkFrame(
            parent,
            fg_color=t["bg_secondary"],
            corner_radius=0,
            height=52,
        )
        bar.grid(row=1, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)
        self.status_bar = bar

        # Thin accent line at very top of bar
        accent_line = ctk.CTkFrame(
            bar,
            fg_color=t["border"],
            height=1,
            corner_radius=0,
        )
        accent_line.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            bar,
            fg_color=t["progress_track"],
            progress_color=t["accent"],
            height=PROGRESS["height_normal"],
            corner_radius=0,
        )
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.progress_bar.set(0)

        # Status row
        status_row = ctk.CTkFrame(bar, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        status_row.grid_columnconfigure(1, weight=1)

        self.status_panel_label = ctk.CTkLabel(
            status_row,
            text="Home",
            font=get_font("micro"),
            text_color=t["fg_tertiary"],
            anchor="w",
        )
        self.status_panel_label.grid(row=0, column=0, sticky="w")

        self.progress_label = ctk.CTkLabel(
            status_row,
            text="Ready",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.progress_label.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.status_meta_label = ctk.CTkLabel(
            status_row,
            text="Idle",
            font=get_font("micro"),
            text_color=t["fg_tertiary"],
            anchor="e",
        )
        self.status_meta_label.grid(row=0, column=2, sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # Menu screen
    # ══════════════════════════════════════════════════════════════════════════

    def _show_menu(self):
        self._clear_panel()
        self.current_panel = "menu"
        self._update_nav_highlight("menu")
        self._refresh_chrome_context()

        t = self.current_theme

        # Outer centering frame
        outer = ctk.CTkFrame(self.panel_container, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=34, pady=(30, 30))
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=0)

        tools_frame = ctk.CTkFrame(outer, fg_color="transparent")
        tools_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        tools_frame.grid_columnconfigure(0, weight=1, uniform="tool")
        tools_frame.grid_columnconfigure(1, weight=1, uniform="tool")
        tools_frame.grid_rowconfigure(0, weight=1)
        tools_frame.grid_rowconfigure(1, weight=1)
        tools_frame.grid_rowconfigure(2, weight=1)

        self._make_tool_card(
            tools_frame,
            icon="✂",
            title="Auto Crop Images",
            desc="Automatically detect and crop objects\nfrom image backgrounds",
            command=self._show_auto_crop_panel,
            row=0,
            column=0,
        )

        self._make_tool_card(
            tools_frame,
            icon="⊞",
            title="Merge TIFF Files",
            desc="Combine multi-page TIFF sequences\ninto single multi-frame files",
            command=self._show_tiff_merge_panel,
            row=0,
            column=1,
        )

        self._make_tool_card(
            tools_frame,
            icon="⇵",
            title="Split Multi-Page TIFFs",
            desc="Extract multi-page TIFF files\ninto single-page TIFF files",
            command=self._show_tiff_split_panel,
            row=1,
            column=0,
        )

        self._make_tool_card(
            tools_frame,
            icon="▣",
            title="Add Border",
            desc="Add white border padding to images\nusing auto-crop spacing rules",
            command=self._show_add_border_panel,
            row=1,
            column=1,
        )

        self._make_tool_card(
            tools_frame,
            icon="⎘",
            title="OCR to PDF",
            desc="Convert scanned images into\nsearchable PDF files with OCR",
            command=self._show_ocr_pdf_panel,
            row=2,
            column=0,
        )

        self._make_tool_card(
            tools_frame,
            icon="🗎",
            title="PDF Conversion",
            desc="Reduce PDF size, split pages,\nand extract selected page ranges",
            command=self._show_pdf_conversion_panel,
            row=2,
            column=1,
        )

        side_note = ctk.CTkFrame(
            outer,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["xl"],
            border_width=1,
            border_color=t["border_subtle"],
            width=256,
        )
        side_note.grid(row=0, column=1, sticky="ns")

        note_inner = ctk.CTkFrame(side_note, fg_color="transparent")
        note_inner.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            note_inner,
            text="PROCESS NOTES",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            note_inner,
            text="Toolkit overview",
            font=get_font("heading"),
            text_color=t["accent"],
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 12))

        for line in (
            "Auto Crop detects content and crops out scanner-created white space.",
            "Merge TIFFs merges TIFF files by named groups.",
            "Split TIFFs allows you to split multi-page TIFFs or a folder containing them.",
            "Add Border adds a border to images, such as book scans.",
        ):
            ctk.CTkLabel(
                note_inner,
                text=f"•  {line}",
                font=get_font("small"),
                text_color=t["fg_secondary"],
                justify="left",
                wraplength=220,
                anchor="w",
            ).pack(anchor="w", pady=(0, 10))

    def _make_tool_card(self, parent, icon, title, desc, command, row, column):
        t = self.current_theme

        card = ctk.CTkFrame(
            parent,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
            height=244,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        # Icon badge
        badge = ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI", 28),
            fg_color=t["accent_dim"],
            text_color=t["accent"],
            width=72,
            height=72,
            corner_radius=RADIUS["md"],
        )
        badge.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        title_lbl = ctk.CTkLabel(
            card,
            text=title,
            font=get_font("heading"),
            text_color=t["accent"],
            anchor="w",
            justify="left",
            wraplength=320,
        )
        title_lbl.grid(row=1, column=0, sticky="nw", padx=18, pady=(0, 8))

        desc_lbl = ctk.CTkLabel(
            card,
            text=desc,
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
            justify="left",
            wraplength=320,
        )
        desc_lbl.grid(row=2, column=0, sticky="nw", padx=18, pady=(0, 12))

        btn = ctk.CTkButton(
            card,
            text="Open Tool  →",
            font=get_font("small"),
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=command,
        )
        btn.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))

    # ══════════════════════════════════════════════════════════════════════════
    # Panel switching
    # ══════════════════════════════════════════════════════════════════════════

    def _clear_panel(self):
        for w in self.panel_container.winfo_children():
            w.destroy()

    def _show_auto_crop_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "auto_crop"
        self._update_nav_highlight("auto_crop")
        self._refresh_chrome_context()
        from .auto_crop_panel import AutoCropPanel
        AutoCropPanel(self).build(self.panel_container)

    def _show_tiff_merge_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "tiff_merge"
        self._update_nav_highlight("tiff_merge")
        self._refresh_chrome_context()
        from .tiff_merge_panel import TiffMergePanel
        TiffMergePanel(self).build(self.panel_container)

    def _show_tiff_split_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "tiff_split"
        self._update_nav_highlight("tiff_split")
        self._refresh_chrome_context()
        from .tiff_split_panel import TiffSplitPanel
        TiffSplitPanel(self).build(self.panel_container)

    def _show_add_border_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "add_border"
        self._update_nav_highlight("add_border")
        self._refresh_chrome_context()
        from .add_border_panel import AddBorderPanel
        AddBorderPanel(self).build(self.panel_container)

    def _show_ocr_pdf_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "ocr_pdf"
        self._update_nav_highlight("ocr_pdf")
        self._refresh_chrome_context()
        from .ocr_pdf_panel import OcrPdfPanel
        OcrPdfPanel(self).build(self.panel_container)

    def _show_pdf_conversion_panel(self):
        if self.operation_in_progress:
            self._show_warning(
                "Operation In Progress",
                "Please wait for the current operation to complete before switching panels.",
            )
            return
        self._clear_panel()
        self.current_panel = "pdf_conversion"
        self._update_nav_highlight("pdf_conversion")
        self._refresh_chrome_context()
        from .pdf_conversion_panel import PdfConversionPanel
        PdfConversionPanel(self).build(self.panel_container)

    def _on_home(self):
        if self.operation_in_progress:
            self._show_confirmation(
                "Operation In Progress",
                "A file operation is currently running.\nAre you sure you want to go back to the menu?",
                self._show_menu,
            )
        else:
            self._show_menu()

    # ══════════════════════════════════════════════════════════════════════════
    # Theme
    # ══════════════════════════════════════════════════════════════════════════

    def _on_appearance_mode_selected(self, selected_label: str):
        selected_mode = APPEARANCE_MENU_LABEL_TO_MODE.get(selected_label, "light")
        if selected_mode == self.appearance_mode:
            return
        self._set_appearance_mode(selected_mode, persist=True)

    def _apply_theme(self):
        t = self.current_theme

        # Icon + label update
        self.theme_mode_var.set(
            APPEARANCE_MENU_LABELS.get(self.appearance_mode, "Light")
        )
        self.theme_mode_menu.configure(
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        )
        self.theme_text_lbl.configure(text_color=t["fg_secondary"])

        # Sidebar
        self.sidebar.configure(fg_color=t["bg_sidebar"])
        self.brand_title_lbl.configure(text_color=t["accent"])
        self.section_lbl.configure(text_color=t["fg_tertiary"])
        self.ver_lbl.configure(text_color=t["fg_tertiary"])
        for divider in self.sidebar_dividers:
            divider.configure(fg_color=t["border"])

        # Right column
        self.right_col.configure(fg_color=t["bg_primary"])

        # Status bar
        self.status_bar.configure(fg_color=t["bg_secondary"])
        self.progress_bar.configure(
            fg_color=t["progress_track"],
            progress_color=t["accent"],
        )
        self.progress_label.configure(text_color=t["fg_secondary"])
        self.status_panel_label.configure(text_color=t["fg_tertiary"])
        self.status_meta_label.configure(text_color=t["fg_tertiary"])

        # Rebuild nav highlights
        self._update_nav_highlight(self.current_panel)

        # Redraw current panel
        if self.current_panel == "menu":
            self._show_menu()
        elif self.current_panel == "auto_crop":
            self._show_auto_crop_panel()
        elif self.current_panel == "tiff_merge":
            self._show_tiff_merge_panel()
        elif self.current_panel == "tiff_split":
            self._show_tiff_split_panel()
        elif self.current_panel == "add_border":
            self._show_add_border_panel()
        elif self.current_panel == "ocr_pdf":
            self._show_ocr_pdf_panel()
        elif self.current_panel == "pdf_conversion":
            self._show_pdf_conversion_panel()

    def _refresh_chrome_context(self):
        panel_titles = {
            "menu": "Home",
            "auto_crop": "Auto Crop",
            "tiff_merge": "Merge TIFFs",
            "tiff_split": "Split TIFFs",
            "add_border": "Add Border",
            "ocr_pdf": "OCR to PDF",
            "pdf_conversion": "PDF Conversion",
        }
        self.status_panel_label.configure(
            text=panel_titles.get(self.current_panel, "Home")
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Public API (called by panels)
    # ══════════════════════════════════════════════════════════════════════════

    def set_status(self, message: str, percentage: float = None):
        """Update the status bar message and optional progress 0–1."""
        self.progress_label.configure(text=message)
        self._refresh_chrome_context()
        if percentage is not None:
            percentage = max(0.0, min(1.0, percentage))
            self.progress_bar.set(percentage)
            if percentage >= 1.0:
                self.status_meta_label.configure(text="Complete")
            elif percentage > 0:
                self.status_meta_label.configure(text=f"{int(percentage * 100)}%")
            else:
                self.status_meta_label.configure(text="Idle")
        else:
            self.status_meta_label.configure(text="Idle")

    def log_message(self, message: str, level: str = "info"):
        """Append a message to the active panel's log display."""
        if not hasattr(self, "log_display"):
            return
        prefixes = {
            "info":    "  ℹ  ",
            "success": "  ✓  ",
            "warning": "  ⚠  ",
            "error":   "  ✕  ",
        }
        prefix = prefixes.get(level, "  ·  ")
        self.log_display.configure(state="normal")
        self.log_display.insert("end", f"{prefix}{message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # Dialogs
    # ══════════════════════════════════════════════════════════════════════════

    def _dialog_base(self, title: str, width: int = 440, height: int = 220):
        t = self.current_theme
        d = ctk.CTkToplevel(self)
        d.title(title)
        d.geometry(f"{width}x{height}")
        d.resizable(False, False)
        d.attributes("-topmost", True)
        d.configure(fg_color=t["bg_secondary"])
        d.grab_set()
        self._position_dialog_top_aligned(d, width, height)
        return d

    def _position_dialog_top_aligned(self, dialog, width: int, height: int):
        self.update_idletasks()
        dialog.update_idletasks()

        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_width = self.winfo_width()
        x = parent_x + max((parent_width - width) // 2, 0)
        y = max(parent_y, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _show_warning(self, title: str, message: str):
        t = self.current_theme
        d = self._dialog_base(title, height=200)

        icon = ctk.CTkLabel(d, text="⚠", font=("Segoe UI", 28), text_color=t["warning"])
        icon.pack(pady=(24, 0))

        ctk.CTkLabel(
            d, text=message, font=get_font("normal"),
            text_color=t["fg_primary"], wraplength=380,
        ).pack(pady=12, padx=24)

        ctk.CTkButton(
            d, text="OK", width=100,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"], hover_color=t["accent_hover"],
            text_color=t["accent_text"], command=d.destroy,
        ).pack(pady=(0, 20))

    def _show_confirmation(self, title: str, message: str, callback):
        t = self.current_theme
        d = self._dialog_base(title, height=210)

        icon = ctk.CTkLabel(d, text="?", font=("Segoe UI", 28, "bold"), text_color=t["accent"])
        icon.pack(pady=(24, 0))

        ctk.CTkLabel(
            d, text=message, font=get_font("normal"),
            text_color=t["fg_primary"], wraplength=380, justify="center",
        ).pack(pady=12, padx=24)

        btn_row = ctk.CTkFrame(d, fg_color="transparent")
        btn_row.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Cancel", width=110,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color="transparent", hover_color=t["bg_tertiary"],
            text_color=t["fg_secondary"],
            border_width=1, border_color=t["border"],
            command=d.destroy,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row, text="Yes, go back", width=130,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"], hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=lambda: (d.destroy(), callback()),
        ).pack(side="left", padx=6)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
