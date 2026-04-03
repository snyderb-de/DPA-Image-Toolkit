"""
Auto-crop panel for DPA Image Toolkit.

Modern card-based layout: drop-zone folder picker, stats strip,
live log with colored levels, and a docked action bar.
"""

import customtkinter as ctk
from pathlib import Path

from utils.file_handler import pick_folder, validate_image_files, create_error_folder
from utils.worker import AutoCropWorker
from .styles import get_theme, get_font, BUTTON, CARD, RADIUS


class AutoCropPanel:
    """Auto-crop panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.worker: AutoCropWorker = None
        self.selected_folder: Path = None
        self.output_folder: Path = None
        self.error_folder: Path = None
        self.has_errors = False

        # widget refs (set during build)
        self.folder_label = None
        self.file_count_lbl = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_cancel = None
        self.btn_error_report = None

    # ──────────────────────────────────────────────────────────────────────────
    # UI Build
    # ──────────────────────────────────────────────────────────────────────────

    def build(self, container):
        t = self.theme

        # Root panel fills container
        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(4, weight=1)   # log stretches
        panel.grid_columnconfigure(0, weight=1)

        # ── Page header ───────────────────────────────────────────────────────
        hdr_row = ctk.CTkFrame(panel, fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))
        hdr_row.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(
            hdr_row,
            text="✂",
            font=("Segoe UI", 22),
            fg_color=t["accent_dim"],
            text_color=t["accent"],
            width=48, height=48,
            corner_radius=RADIUS["md"],
        )
        badge.grid(row=0, column=0, rowspan=2)

        ctk.CTkLabel(
            hdr_row,
            text="PROCESSING MODULE",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", padx=(16, 0))

        title = ctk.CTkLabel(
            hdr_row,
            text="Auto Crop Images",
            font=get_font("title"),
            text_color=t["fg_primary"],
            anchor="w",
        )
        title.grid(row=1, column=1, sticky="nw", padx=(16, 0))

        subtitle = ctk.CTkLabel(
            hdr_row,
            text="Detect and crop objects from image backgrounds automatically",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        subtitle.grid(row=2, column=1, sticky="w", padx=(16, 0), pady=(8, 0))

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

        # Folder button
        btn_folder = ctk.CTkButton(
            picker_card,
            text="  📁  Select Image Folder",
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

        # Path / status label
        self.folder_label = ctk.CTkLabel(
            picker_card,
            text="No folder selected",
            font=get_font("small"),
            text_color=t["fg_tertiary"],
            anchor="w",
        )
        self.folder_label.grid(row=0, column=1, padx=(0, 14), pady=14, sticky="ew")

        # File count badge
        self.file_count_lbl = ctk.CTkLabel(
            picker_card,
            text="",
            font=get_font("micro"),
            text_color=t["accent"],
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["pill"],
            padx=8,
            pady=2,
        )
        # hidden until a folder is selected

        # ── Info / status banner ──────────────────────────────────────────────
        self.info_card = ctk.CTkFrame(
            panel,
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["md"],
            border_width=0,
        )
        self.info_card.grid(row=2, column=0, sticky="ew", padx=36, pady=(12, 0))

        self.info_lbl = ctk.CTkLabel(
            self.info_card,
            text="Select a folder containing images to begin.",
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
            "Auto Crop detects content and crops out scanner-created white space.",
            "Best results come from pages with clear contrast against the scanner bed.",
            "Cropped images are written to cropped/ and failed files are reported separately.",
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

        self.log_clear_btn = ctk.CTkButton(
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
        )
        self.log_clear_btn.grid(row=0, column=1, sticky="e")

        # Divider
        ctk.CTkFrame(
            log_card, fg_color=t["border_subtle"], height=1, corner_radius=0,
        ).grid(row=1, column=0, sticky="ew", padx=0, pady=(8, 0))

        # Textbox
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
            text="  ▶  Start Auto Crop",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=self._on_start_crop,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=2, sticky="e")

        self._log("Ready — select an image folder to get started.", "info")

    # ──────────────────────────────────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def _on_select_folder(self):
        folder = pick_folder("Select folder with images to auto-crop")

        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        is_valid, files, error = validate_image_files(folder)

        if not is_valid:
            self._log(f"No images found: {error}", "error")
            self._set_info(f"✕  {error}", level="error")
            return

        self.selected_folder = folder
        self.error_folder = create_error_folder(folder)

        # Update picker row
        self.folder_label.configure(
            text=str(folder),
            text_color=self.theme["fg_primary"],
        )

        # Show file count badge
        self.file_count_lbl.configure(text=f"  {len(files)} images  ")
        self.file_count_lbl.grid(row=0, column=2, padx=(0, 14))

        self._set_info(
            f"✓  Found {len(files)} image file(s) in '{folder.name}' — click Start to begin.",
            level="success",
        )
        self.btn_start.configure(state="normal")

        self._log(f"Folder: {folder}", "info")
        self._log(f"Found {len(files)} image file(s).", "success")

    def _on_start_crop(self):
        if not self.selected_folder:
            self._log("No folder selected.", "error")
            return

        self.output_folder = create_error_folder(self.selected_folder).parent / "cropped"
        self.output_folder.mkdir(parents=True, exist_ok=True)
        error_folder = create_error_folder(self.selected_folder)

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "crop"
        self.has_errors = False

        self.parent.set_status("Starting auto-crop…", 0.0)
        self._log("Starting auto-crop operation…", "info")

        self.worker = AutoCropWorker(
            input_folder=self.selected_folder,
            output_folder=self.output_folder,
            error_folder=error_folder,
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
        self._poll_worker()

    def _on_progress(self, progress: dict):
        current = progress["current"]
        total = progress["total"]
        pct = progress["percentage"] / 100.0
        filename = progress.get("filename", "")

        self.parent.set_status(f"Cropping {current} / {total} — {filename}", pct)
        self._log(f"Processing: {filename}", "info")

    def _on_status(self, message: str):
        self.parent.set_status(message)
        self._log(message, "success")

    def _on_error(self, filename: str, error_message: str):
        self.has_errors = True
        self._log(f"{filename} — {error_message}", "error")
        if self.btn_error_report:
            self.btn_error_report.configure(state="normal")

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.05)
            self.parent.after(100, self._poll_worker)
        else:
            self._on_worker_done()

    def _on_worker_done(self):
        if self.worker:
            results = self.worker.get_results()
            level = "warning" if self.has_errors else "success"
            self._log(
                f"Done — {results['success']} cropped, "
                f"{results['skipped']} skipped, {results['failed']} failed.",
                level,
            )
            self._set_info(
                f"✓  Complete — {results['success']} cropped  ·  "
                f"{results['skipped']} skipped  ·  {results['failed']} failed",
                level=level,
            )

            if results.get("errors"):
                self._generate_error_report(results)

        self.btn_start.configure(state="normal", text="  ▶  Start Auto Crop")
        self.parent.operation_in_progress = False
        self.parent.set_status("Ready", 1.0)

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
            self._log(f"Failed to open error folder: {e}", "error")

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

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
        t = self.theme
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

    def _generate_error_report(self, results: dict):
        if not self.error_folder:
            return
        report_file = self.error_folder / "CROP_ERROR_REPORT.txt"
        lines = [
            "DPA Image Toolkit — Auto Crop Error Report",
            "=" * 60, "",
            f"Total Errors: {len(results['errors'])}", "",
        ]
        for e in results["errors"]:
            lines += [f"File:  {e['file']}", f"Error: {e['error']}", ""]
        lines += [
            "=" * 60,
            "These files have been moved to the errored-files/ folder.",
        ]
        try:
            report_file.write_text("\n".join(lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as ex:
            self._log(f"Failed to save error report: {ex}", "error")
