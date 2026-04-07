"""
Add border panel for DPA Image Toolkit.
"""

import customtkinter as ctk
from pathlib import Path

from utils.file_handler import create_error_folder, pick_folder, validate_image_files
from utils.tool_dependencies import (
    check_tool_dependencies,
    get_tool_dependency_panel_content,
    get_tool_dependency_statuses,
    show_dependency_warning,
)
from utils.worker import AddBorderWorker
from modules.auto_cropping.core import (
    DEFAULT_PADDING_PERCENT,
    DEFAULT_PADDING_MIN,
    DEFAULT_PADDING_MAX,
)
from .dependency_sidebar import build_dependency_sidebar, refresh_dependency_sidebar
from .styles import get_font, BUTTON, RADIUS


class AddBorderPanel:
    """Add border panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme
        self.selected_folder: Path = None
        self.output_folder: Path = None
        self.error_folder: Path = None
        self.worker = None
        self.has_errors = False

        self.folder_label = None
        self.file_count_lbl = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_new_job = None
        self.btn_cancel = None
        self.btn_error_report = None
        self.dependency_rows = []

    def build(self, container):
        t = self.theme

        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(4, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=0)

        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Add Border",
            font=get_font("title"),
            text_color=t["fg_primary"],
        ).grid(row=0, column=0, sticky="sw")

        ctk.CTkLabel(
            hdr,
            text="Add a white border using the same padding logic as auto-crop",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, sticky="nw", pady=(8, 0))

        picker_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        picker_card.grid(row=1, column=0, sticky="ew", padx=36, pady=(24, 0))
        picker_card.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
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
        ).grid(row=0, column=0, padx=14, pady=14, sticky="w")

        self.folder_label = ctk.CTkLabel(
            picker_card,
            text="No folder selected",
            font=get_font("small"),
            text_color=t["fg_tertiary"],
            anchor="w",
        )
        self.folder_label.grid(row=0, column=1, padx=(0, 14), pady=14, sticky="ew")

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

        self.info_card = ctk.CTkFrame(
            panel,
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["md"],
            border_width=0,
        )
        self.info_card.grid(row=2, column=0, sticky="ew", padx=36, pady=(12, 0))

        self.info_lbl = ctk.CTkLabel(
            self.info_card,
            text=(
                f"Padding uses auto-crop settings: {int(DEFAULT_PADDING_PERCENT * 100)}% "
                f"of image size, clamped to {DEFAULT_PADDING_MIN}-{DEFAULT_PADDING_MAX}px."
            ),
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        dependency_content = get_tool_dependency_panel_content("add_border")
        side_panel, self.dependency_rows = build_dependency_sidebar(
            panel,
            t,
            heading=dependency_content["heading"],
            statuses=get_tool_dependency_statuses("add_border"),
            support_lines=dependency_content["support_lines"],
        )
        side_panel.grid(row=1, column=1, rowspan=4, sticky="nsew", padx=(0, 36), pady=(24, 0))

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
            "Add Border adds a border to images such as book scans and page captures.",
            "It uses the same padding logic as auto-crop so the spacing stays consistent.",
            "Bordered images are written into bordered/ and the originals are left untouched.",
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

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        log_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_hdr,
            text="ACTIVITY LOG",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
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

        ctk.CTkFrame(log_card, fg_color=t["border_subtle"], height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=0, pady=(8, 0)
        )

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
            text_color_disabled=t["button_disabled_text"],
            command=self._on_view_error_report,
            state="disabled",
        )
        self.btn_error_report.grid(row=0, column=0, sticky="w")

        self.btn_new_job = ctk.CTkButton(
            action_bar,
            text="  ↺  Clear/New Job",
            font=get_font("small"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            text_color_disabled=t["button_disabled_text"],
            command=self._on_clear_new_job,
            state="normal",
        )
        self.btn_new_job.grid(row=0, column=1, sticky="e", padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            action_bar,
            text="  ■  Cancel",
            font=get_font("small"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["warning_dim"],
            hover_color=t["warning"],
            text_color=t["warning"],
            border_width=1,
            border_color=t["warning"],
            text_color_disabled=t["button_disabled_text"],
            command=self._on_cancel,
            state="disabled",
        )
        self.btn_cancel.grid(row=0, column=2, sticky="e", padx=(0, 10))

        self.btn_start = ctk.CTkButton(
            action_bar,
            text="  ▶  Add Border",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            text_color_disabled=t["button_disabled_text"],
            command=self._on_start,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=3, sticky="e")

        self._refresh_dependency_panel()
        self._log("Ready — select an image folder to add borders.", "info")

    def _on_select_folder(self):
        folder = pick_folder("Select folder with images to add borders")
        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        is_valid, files, error = validate_image_files(folder)
        if not is_valid:
            self._log(f"No images found: {error}", "error")
            self._set_info(f"✕  {error}", "error")
            return

        self.selected_folder = folder
        self.output_folder = folder / "bordered"
        self.error_folder = self._prepare_error_folder(folder)
        self.has_errors = False
        self.folder_label.configure(text=str(folder), text_color=self.theme["fg_primary"])
        self.file_count_lbl.configure(text=f"  {len(files)} images  ")
        self.file_count_lbl.grid(row=0, column=2, padx=(0, 14))
        self.btn_start.configure(state="normal")
        self.btn_error_report.configure(state="disabled")
        self._set_info(
            f"✓  Found {len(files)} image file(s). Output will be saved to bordered/.",
            "success",
        )
        self._log(f"Folder: {folder}", "info")
        self._log(f"Found {len(files)} image file(s).", "success")

    def _on_start(self):
        if not self.selected_folder:
            self._log("No folder selected.", "error")
            return

        ok, error_msg, _details = check_tool_dependencies("add_border")
        self._refresh_dependency_panel()
        if not ok:
            show_dependency_warning(self.parent, "Add Border", error_msg)
            self._set_info(
                "⚠  Add Border dependencies are missing. Contact support for installation.",
                "warning",
            )
            self._log(error_msg, "warning")
            self._log("Contact support for dependency installation on this machine.", "warning")
            self.parent.set_status("Add Border dependencies are missing", 1.0)
            return

        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.btn_new_job.configure(state="normal")
        self.btn_error_report.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "border"
        self.has_errors = False

        if not self.error_folder:
            self.error_folder = self._prepare_error_folder(self.selected_folder)

        self.parent.set_status("Starting border operation…", 0.0)
        self._log("Starting border operation…", "info")

        self.worker = AddBorderWorker(self.selected_folder, self.output_folder)
        self.worker.set_progress_callback(lambda p: self._dispatch(self._on_progress, p))
        self.worker.set_status_callback(lambda m: self._dispatch(self._on_status, m))
        self.worker.set_error_callback(lambda f, e: self._dispatch(self._on_error, f, e))
        self.worker.start()
        self._poll_worker()

    def _on_progress(self, progress):
        current = progress["current"]
        total = progress["total"]
        pct = progress["percentage"] / 100.0
        filename = progress.get("filename", "")
        self.parent.set_status(f"Adding border {current} / {total} — {filename}", pct)
        self._log(f"Processing: {filename}", "info")

    def _on_status(self, message):
        self.parent.set_status(message)
        self._log(message, "success" if "✅" in message else "info")

    def _on_error(self, filename, error_message):
        self.has_errors = True
        self._log(f"{filename} — {error_message}", "error")
        if self.btn_error_report:
            self.btn_error_report.configure(state="normal")

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self.btn_cancel.configure(state="disabled")
            self._log("Cancellation requested — waiting for the current image to finish.", "warning")
            self._set_info(
                "Cancellation requested — waiting for the current image to finish.",
                "warning",
            )

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.05)
            self.parent.after(100, self._poll_worker)
        else:
            results = self.worker.get_results() if self.worker else {}
            cancelled = results.get("cancelled", False)
            level = "warning" if results.get("failed", 0) or cancelled else "success"
            if cancelled:
                self._set_info(
                    f"⚠  Cancelled — {results.get('success', 0)} bordered  ·  "
                    f"{results.get('failed', 0)} failed",
                    level,
                )
                self._log("Add Border was cancelled before all images were processed.", "warning")
            else:
                self._set_info(
                    f"✓  Complete — {results.get('success', 0)} bordered  ·  "
                    f"{results.get('failed', 0)} failed",
                    level,
                )
            if results.get("errors"):
                self._generate_error_report(results)
                self.btn_error_report.configure(state="normal")
                self._log("Some files failed — click 'View Errors' for details.", "warning")
            self.btn_start.configure(state="normal", text="  ▶  Add Border")
            self.btn_new_job.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            self.parent.operation_in_progress = False
            self.parent.operation_type = None
            self.parent.set_status("Ready", 1.0)

    def _on_clear_new_job(self):
        if self.worker and self.worker.is_alive():
            return

        self.worker = None
        self.selected_folder = None
        self.output_folder = None
        self.error_folder = None
        self.has_errors = False

        self.folder_label.configure(text="No folder selected", text_color=self.theme["fg_tertiary"])
        self.file_count_lbl.grid_remove()
        self.btn_start.configure(state="disabled", text="  ▶  Add Border")
        self.btn_cancel.configure(state="disabled")
        self.btn_error_report.configure(state="disabled")
        self.btn_new_job.configure(state="normal")
        self._set_info(
            (
                f"Padding uses auto-crop settings: {int(DEFAULT_PADDING_PERCENT * 100)}% "
                f"of image size, clamped to {DEFAULT_PADDING_MIN}-{DEFAULT_PADDING_MAX}px."
            ),
            "info",
        )
        self._clear_log()
        self._refresh_dependency_panel()
        self.parent.operation_in_progress = False
        self.parent.operation_type = None
        self.parent.set_status("Ready", 1.0)
        self._log("Ready — select an image folder to add borders.", "info")

    def _on_view_error_report(self):
        if not self.error_folder or not self.error_folder.exists():
            self._log("No add-border error folder found.", "warning")
            return

        import platform
        import subprocess

        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{self.error_folder}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(self.error_folder)])
            else:
                subprocess.Popen(["xdg-open", str(self.error_folder)])
            self._log(f"Opened error folder: {self.error_folder}", "info")
        except Exception as exc:
            self._log(f"Failed to open error folder: {exc}", "error")

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _refresh_dependency_panel(self):
        refresh_dependency_sidebar(
            self.dependency_rows,
            get_tool_dependency_statuses("add_border"),
        )

    def _set_info(self, text, level="info"):
        t = self.theme
        color_map = {
            "info": (t["fg_secondary"], t["accent_dim"]),
            "success": (t["success"], t["success_dim"]),
            "warning": (t["warning"], t["warning_dim"]),
            "error": (t["error"], t["error_dim"]),
        }
        text_color, bg_color = color_map.get(level, (t["fg_secondary"], t["accent_dim"]))
        self.info_card.configure(fg_color=bg_color)
        self.info_lbl.configure(text=text, text_color=text_color)

    def _clear_log(self):
        self.log_display.configure(state="normal")
        self.log_display.delete("1.0", "end")
        self.log_display.configure(state="disabled")

    def _log(self, message, level="info"):
        prefixes = {
            "info": "  ·  ",
            "success": "  ✓  ",
            "warning": "  ⚠  ",
            "error": "  ✕  ",
        }
        self.log_display.configure(state="normal")
        self.log_display.insert("end", f"{prefixes.get(level, '  ·  ')}{message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    def _prepare_error_folder(self, base_folder: Path):
        error_root = create_error_folder(base_folder)
        if not error_root:
            return None

        error_folder = error_root / "add-border"
        error_folder.mkdir(parents=True, exist_ok=True)
        return error_folder

    def _generate_error_report(self, results: dict):
        if not self.error_folder:
            return

        report_file = self.error_folder / "ADD_BORDER_ERROR_REPORT.txt"
        lines = [
            "DPA Image Toolkit — Add Border Error Report",
            "=" * 60,
            "",
            f"Total Errors: {len(results.get('errors', []))}",
            "",
        ]
        for error in results.get("errors", []):
            lines += [
                f"File:  {error['file']}",
                f"Error: {error['error']}",
                "",
            ]
        lines += [
            "=" * 60,
            "Review these files before rerunning Add Border.",
        ]

        try:
            report_file.write_text("\n".join(lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as exc:
            self._log(f"Failed to save error report: {exc}", "error")
