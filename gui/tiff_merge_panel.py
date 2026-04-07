"""
TIFF merge panel for DPA Image Toolkit.

Modern card-based layout: folder picker, group stats, naming validation
dialog, live log, and a docked action bar.
"""

import customtkinter as ctk
from pathlib import Path

from utils.file_handler import pick_folder, validate_tif_files, create_error_folder
from modules.tiff_combine.naming import validate_naming_convention
from .styles import get_theme, get_font, BUTTON, CARD, RADIUS


class TiffMergePanel:
    """TIFF merge panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.selected_folder: Path = None
        self.error_folder: Path = None
        self.groups: dict = None
        self.worker = None

        # Widget refs
        self.folder_label = None
        self.group_count_lbl = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_error_report = None

    # ──────────────────────────────────────────────────────────────────────────
    # UI Build
    # ──────────────────────────────────────────────────────────────────────────

    def build(self, container):
        t = self.theme

        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(4, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # ── Page header ───────────────────────────────────────────────────────
        hdr_row = ctk.CTkFrame(panel, fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))
        hdr_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_row,
            text="Merge TIFF Files",
            font=get_font("title"),
            text_color=t["fg_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="sw")

        ctk.CTkLabel(
            hdr_row,
            text="Combine multi-page TIFF sequences into single multi-frame files",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            anchor="w",
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, sticky="nw", pady=(8, 0))

        # ── Folder picker card ────────────────────────────────────────────────
        picker_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        picker_card.grid(row=1, column=0, sticky="ew", padx=36, pady=(24, 0))
        picker_card.grid_columnconfigure(1, weight=1)

        btn_folder = ctk.CTkButton(
            picker_card,
            text="  📁  Select TIFF Folder",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=self._on_select_folder,
        )
        btn_folder.grid(row=0, column=0, padx=14, pady=14, sticky="w")

        self.folder_label = ctk.CTkLabel(
            picker_card,
            text="No folder selected",
            font=get_font("small"),
            text_color=t["fg_tertiary"],
            anchor="w",
        )
        self.folder_label.grid(row=0, column=1, padx=(0, 14), pady=14, sticky="ew")

        # Group count badge (hidden initially)
        self.group_count_lbl = ctk.CTkLabel(
            picker_card,
            text="",
            font=get_font("micro"),
            text_color=t["accent"],
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["pill"],
            padx=8,
            pady=2,
        )

        # ── Info banner ───────────────────────────────────────────────────────
        self.info_card = ctk.CTkFrame(
            panel,
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["md"],
            border_width=0,
        )
        self.info_card.grid(row=2, column=0, sticky="ew", padx=36, pady=(12, 0))

        self.info_lbl = ctk.CTkLabel(
            self.info_card,
            text="Files must be named:  groupname_###.tif",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        notes_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        notes_card.grid(row=3, column=0, sticky="ew", padx=36, pady=(12, 0))

        ctk.CTkLabel(
            notes_card,
            text="PROCESS NOTES",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(14, 2))

        for line in (
            "Merge TIFFs groups files by shared names such as groupname_001.tif, groupname_002.tif.",
            "Files in valid groups are merged in number order into a single multi-page TIFF.",
            "TIFFs that do not match a valid group name are skipped rather than stopping the run.",
        ):
            ctk.CTkLabel(
                notes_card,
                text=f"•  {line}",
                font=get_font("small"),
                text_color=t["fg_secondary"],
                justify="left",
                wraplength=860,
                anchor="w",
            ).pack(anchor="w", padx=16, pady=(0, 8))

        # ── Log card ──────────────────────────────────────────────────────────
        log_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        log_card.grid(row=4, column=0, sticky="nsew", padx=36, pady=(12, 0))
        log_card.grid_rowconfigure(2, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        # Log header
        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        log_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_hdr,
            text="Activity Log",
            font=get_font("eyebrow"),
            text_color=t["fg_secondary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_hdr,
            text="Clear",
            font=get_font("micro"),
            height=22,
            corner_radius=RADIUS["sm"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_secondary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=self._clear_log,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkFrame(
            log_card, fg_color=t["border_subtle"], height=1, corner_radius=0,
        ).grid(row=1, column=0, sticky="ew", padx=0, pady=(8, 0))

        self.log_display = ctk.CTkTextbox(
            log_card,
            fg_color="transparent",
            text_color=t["fg_primary"],
            border_width=0,
            corner_radius=0,
            font=get_font("mono"),
            wrap="word",
        )
        self.log_display.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.log_display.configure(state="disabled")

        # ── Action bar ────────────────────────────────────────────────────────
        action_bar = ctk.CTkFrame(panel, fg_color="transparent")
        action_bar.grid(row=5, column=0, sticky="ew", padx=36, pady=(12, 20))
        action_bar.grid_columnconfigure(1, weight=1)

        self.btn_error_report = ctk.CTkButton(
            action_bar,
            text="  📋  View Errors",
            font=get_font("small"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["error_dim"],
            hover_color=t["error"],
            text_color=t["error"],
            border_width=1,
            border_color=t["error"],
            command=self._on_view_error_report,
            state="disabled",
        )
        self.btn_error_report.grid(row=0, column=0, sticky="w")

        self.btn_start = ctk.CTkButton(
            action_bar,
            text="  ▶  Start Merge",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=self._on_start_merge,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=2, sticky="e")

        self._log("Ready — select a TIFF folder to get started.", "info")

    # ──────────────────────────────────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def _on_select_folder(self):
        folder = pick_folder("Select folder with TIFF files to merge")

        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        is_valid, files, error = validate_tif_files(folder)

        if not is_valid:
            self._log(f"No TIFF files found: {error}", "error")
            self._set_info(f"✕  {error}", level="error")
            return

        groups, naming_valid, issues = validate_naming_convention(folder)

        if not groups:
            self._log("No valid TIFF groups found.", "error")
            for issue in issues:
                self._log(f"  {issue}", "warning")
            self._set_info("✕  No valid TIFF groups found — check naming.", level="error")
            return

        if not naming_valid:
            self._log(f"Naming issues found ({len(issues)} file(s)):", "warning")
            for issue in issues:
                self._log(f"  {issue}", "warning")

        self.selected_folder = folder
        self.error_folder = create_error_folder(folder)
        self.groups = groups

        self.folder_label.configure(
            text=str(folder),
            text_color=self.theme["fg_primary"],
        )

        total_valid = sum(len(f) for f in groups.values())
        single = len(files) - total_valid

        self.group_count_lbl.configure(
            text=f"  {len(groups)} groups / {total_valid} files  "
        )
        self.group_count_lbl.grid(row=0, column=2, padx=(0, 14))

        info = f"✓  Found {len(groups)} group(s) with {total_valid} TIFF file(s)"
        if single:
            info += f"  ·  {single} single file(s) will be skipped"
        self._set_info(info, level="success")
        self.btn_start.configure(state="normal")

        self._log(f"Folder: {folder}", "info")
        self._log(f"Found {len(groups)} group(s):", "success")
        for name, grp_files in groups.items():
            self._log(f"  {name}  ({len(grp_files)} files)", "info")
        if single:
            self._log(f"{single} file(s) without matching pattern will be skipped.", "info")

        # Show spot-check dialog
        self._show_validation_dialog()

    def _on_start_merge(self):
        if not self.selected_folder or not self.groups:
            self._log("No folder selected.", "error")
            return

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "merge"

        self.parent.set_status("Starting TIFF merge…", 0.0)
        self._log("Starting TIFF merge operation…", "info")

        output_folder = self.selected_folder / "merged"
        output_folder.mkdir(parents=True, exist_ok=True)

        from utils.worker import TiffMergeWorker

        self.worker = TiffMergeWorker(
            self.selected_folder,
            output_folder,
            self.error_folder,
            self.groups,
        )
        self.worker.set_progress_callback(
            lambda p: self._dispatch(self._on_progress, p)
        )
        self.worker.set_status_callback(
            lambda m: self._dispatch(self._on_status, m)
        )
        self.worker.set_error_callback(
            lambda f, e: self._dispatch(self._on_error, f, e)
        )

        self.worker.start()
        self._log(f"Merging {len(self.groups)} group(s)…", "success")

    def _on_progress(self, progress: dict):
        current = progress.get("current", 0)
        total = progress.get("total", 1)
        pct = progress.get("percentage", 0) / 100.0
        filename = progress.get("filename", "")

        self.parent.set_status(f"Merging {current} / {total}", pct)
        if filename:
            self._log(f"Processing group: {filename}", "info")

    def _on_status(self, message: str):
        self._log(message, "info")

        if "✅" in message or "❌" in message or "cancelled" in message.lower():
            self.btn_start.configure(state="normal", text="  ▶  Start Merge")
            self.parent.operation_in_progress = False
            self.parent.set_status("Ready", 1.0)

            results = getattr(self.worker, "get_results", lambda: {})()
            if results.get("failed", 0) > 0:
                self.btn_error_report.configure(state="normal")
                self._log("Some groups failed — click 'View Errors' for details.", "warning")

    def _on_error(self, filename: str, error_message: str):
        self._log(f"{filename}: {error_message}", "error")

    def _on_view_error_report(self):
        if not self.error_folder or not self.error_folder.exists():
            self._log("No error folder found.", "warning")
            return

        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{self.error_folder}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(self.error_folder)])
            else:
                subprocess.Popen(["xdg-open", str(self.error_folder)])
            self._log(f"Opened error folder: {self.error_folder}", "info")
        except Exception as e:
            self._log(f"Failed to open folder: {e}", "error")

    # ──────────────────────────────────────────────────────────────────────────
    # Validation dialog
    # ──────────────────────────────────────────────────────────────────────────

    def _show_validation_dialog(self):
        if not self.groups:
            return

        t = self.theme
        d = ctk.CTkToplevel(self.parent)
        d.title("Confirm File Groups")
        width = 520
        height = 460
        d.geometry(f"{width}x{height}")
        d.resizable(False, False)
        d.attributes("-topmost", True)
        d.transient(self.parent)
        d.configure(fg_color=t["bg_secondary"])
        d.grab_set()

        # Header
        hdr = ctk.CTkFrame(d, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(24, 0))

        ctk.CTkLabel(
            hdr,
            text="  🔍  Verify File Groups",
            font=get_font("title"),
            text_color=t["fg_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text="Spot-check: first, middle, and last groups are shown below.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
        ).pack(anchor="w", pady=(4, 0))

        # Divider
        ctk.CTkFrame(d, fg_color=t["border"], height=1, corner_radius=0).pack(
            fill="x", padx=0, pady=16
        )

        # Scrollable group list
        scroll = ctk.CTkScrollableFrame(
            d,
            fg_color=t["bg_tertiary"],
            corner_radius=RADIUS["md"],
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 0))

        group_names = list(self.groups.keys())
        indices = {0}
        if len(group_names) > 2:
            indices.add(len(group_names) // 2)
        if len(group_names) > 1:
            indices.add(len(group_names) - 1)
        indices = sorted(indices)

        for i, idx in enumerate(indices):
            name = group_names[idx]
            files = self.groups[name]

            row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            row_frame.pack(fill="x", padx=8, pady=(12, 0))

            # Group header row
            gh = ctk.CTkFrame(row_frame, fg_color="transparent")
            gh.pack(fill="x")
            gh.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                gh,
                text="📁",
                font=("Segoe UI", 14),
            ).grid(row=0, column=0, padx=(0, 8))

            ctk.CTkLabel(
                gh,
                text=name,
                font=get_font("subheading"),
                text_color=t["fg_primary"],
                anchor="w",
            ).grid(row=0, column=1, sticky="w")

            # Count badge
            ctk.CTkLabel(
                gh,
                text=f"  {len(files)} files  ",
                font=get_font("micro"),
                text_color=t["accent"],
                fg_color=t["accent_dim"],
                corner_radius=RADIUS["pill"],
                padx=4,
            ).grid(row=0, column=2, padx=8)

            # File list preview
            if len(files) <= 3:
                preview_files = files
                ellipsis = False
            else:
                preview_files = [files[0], files[-1]]
                ellipsis = True

            for j, fname in enumerate(preview_files):
                if ellipsis and j == 1:
                    ctk.CTkLabel(
                        row_frame,
                        text=f"    … {len(files) - 2} more files …",
                        font=get_font("mono_sm"),
                        text_color=t["fg_tertiary"],
                        anchor="w",
                    ).pack(fill="x", padx=(32, 8))

                ctk.CTkLabel(
                    row_frame,
                    text=f"    {fname}",
                    font=get_font("mono_sm"),
                    text_color=t["fg_secondary"],
                    anchor="w",
                ).pack(fill="x", padx=(32, 8))

            # Divider between groups
            if i < len(indices) - 1:
                ctk.CTkFrame(
                    scroll, fg_color=t["border"], height=1, corner_radius=0,
                ).pack(fill="x", padx=8, pady=(12, 0))

        # Buttons
        ctk.CTkFrame(d, fg_color=t["border"], height=1, corner_radius=0).pack(
            fill="x", padx=0, pady=(16, 0)
        )

        btn_row = ctk.CTkFrame(d, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=16)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_secondary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=d.destroy,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="  ✓  Looks Good — Proceed",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=lambda: (
                d.destroy(),
                self._log("File grouping confirmed by user.", "success"),
            ),
        ).grid(row=0, column=2, sticky="e")

        d.wait_visibility()
        self._center_dialog(d, width, height)
        d.focus_force()

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _center_dialog(self, dialog, width: int, height: int):
        """Center a modal dialog over the main application window."""
        self.parent.update_idletasks()
        dialog.update_idletasks()

        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        x = parent_x + max((parent_width - width) // 2, 0)
        y = parent_y + max((parent_height - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _set_info(self, text: str, level: str = "info"):
        t = self.theme
        color_map = {
            "info":    (t["fg_secondary"], t["accent_dim"]),
            "success": (t["success"], t["success_dim"]),
            "warning": (t["warning"], t["warning_dim"]),
            "error":   (t["error"], t["error_dim"]),
        }
        text_color, bg_color = color_map.get(level, (t["fg_secondary"], t["accent_dim"]))
        self.info_card.configure(fg_color=bg_color)
        self.info_lbl.configure(
            text=text,
            text_color=text_color,
        )

    def _clear_log(self):
        self.log_display.configure(state="normal")
        self.log_display.delete("1.0", "end")
        self.log_display.configure(state="disabled")

    def _log(self, message: str, level: str = "info"):
        prefixes = {
            "info":    "  ·  ",
            "success": "  ✓  ",
            "warning": "  ⚠  ",
            "error":   "  ✕  ",
        }
        prefix = prefixes.get(level, "  ·  ")
        self.log_display.configure(state="normal")
        self.log_display.insert("end", f"{prefix}{message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")
