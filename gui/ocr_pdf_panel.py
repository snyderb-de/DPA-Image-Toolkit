"""
OCR-to-PDF panel for DPA Image Toolkit.

Batch-converts image folders into searchable PDFs using local OCR tooling.
"""

import customtkinter as ctk
from pathlib import Path

from modules.ocr_pdf.core import check_ocr_dependencies, find_ocr_input_files
from utils.file_handler import create_error_folder, create_output_folder, pick_folder
from utils.worker import OcrPdfWorker
from .styles import BUTTON, RADIUS, get_font


class OcrPdfPanel:
    """OCR-to-PDF panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.worker: OcrPdfWorker = None
        self.selected_folder: Path = None
        self.output_folder: Path = None
        self.error_folder: Path = None
        self.has_errors = False

        self.recurse_var = ctk.BooleanVar(value=False)
        self.skip_existing_var = ctk.BooleanVar(value=True)
        self.save_pdfa_var = ctk.BooleanVar(value=True)
        self.skip_messy_var = ctk.BooleanVar(value=True)
        self.language_var = ctk.StringVar(value="eng")

        self.folder_label = None
        self.file_count_lbl = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_cancel = None
        self.btn_error_report = None
        self.language_entry = None

    def build(self, container):
        t = self.theme

        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(5, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        hdr_row = ctk.CTkFrame(panel, fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))
        hdr_row.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            hdr_row,
            text="OCR Images to Searchable PDF",
            font=get_font("title"),
            text_color=t["fg_primary"],
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="sw")

        subtitle = ctk.CTkLabel(
            hdr_row,
            text="Convert scanned image folders into searchable PDF files with local OCR and optional PDF/A output",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            anchor="w",
            justify="left",
            wraplength=760,
        )
        subtitle.grid(row=1, column=0, sticky="nw", pady=(8, 0))

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
            text="  📁  Select OCR Input Folder",
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
            text="Select a folder containing scanned image files to begin.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        options_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        options_card.grid(row=3, column=0, sticky="ew", padx=36, pady=(12, 0))
        options_card.grid_columnconfigure(1, weight=1)
        options_card.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            options_card,
            text="OPTIONS",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 6))

        recurse_cb = ctk.CTkCheckBox(
            options_card,
            text="Recurse into subfolders",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.recurse_var,
            command=self._on_option_change,
        )
        recurse_cb.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        skip_cb = ctk.CTkCheckBox(
            options_card,
            text="Skip existing PDFs",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.skip_existing_var,
        )
        skip_cb.grid(row=1, column=1, sticky="w", padx=16, pady=(0, 14))

        pdfa_cb = ctk.CTkCheckBox(
            options_card,
            text="Save as PDF/A",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.save_pdfa_var,
        )
        pdfa_cb.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

        messy_cb = ctk.CTkCheckBox(
            options_card,
            text="Skip scans that fail OCR quality precheck",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.skip_messy_var,
        )
        messy_cb.grid(row=2, column=1, columnspan=3, sticky="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            options_card,
            text="OCR Language",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        ).grid(row=1, column=2, sticky="e", padx=(16, 8), pady=(0, 14))

        self.language_entry = ctk.CTkEntry(
            options_card,
            textvariable=self.language_var,
            width=140,
        )
        self.language_entry.grid(row=1, column=3, sticky="w", padx=(0, 16), pady=(0, 14))

        notes_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        notes_card.grid(row=4, column=0, sticky="ew", padx=36, pady=(12, 0))

        ctk.CTkLabel(
            notes_card,
            text="PROCESS NOTES",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(14, 2))

        for line in (
            "OCR creates one searchable PDF per supported image file.",
            "Output is written to ocr-pdf/ so original images stay untouched.",
            "PDF/A mode is on by default and requires OCRmyPDF plus local OCR dependencies.",
            "A conservative quality precheck can skip scans that are likely to produce bad OCR.",
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
        log_card.grid(row=5, column=0, sticky="nsew", padx=36, pady=(12, 0))
        log_card.grid_rowconfigure(2, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        log_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_hdr,
            text="Activity Log",
            font=get_font("eyebrow"),
            text_color=t["fg_secondary"],
        ).grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
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
        clear_btn.grid(row=0, column=1, sticky="e")

        ctk.CTkFrame(
            log_card,
            fg_color=t["border_subtle"],
            height=1,
            corner_radius=0,
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

        action_bar = ctk.CTkFrame(panel, fg_color="transparent")
        action_bar.grid(row=6, column=0, sticky="ew", padx=36, pady=(12, 20))
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
            command=self._on_cancel,
            state="disabled",
        )
        self.btn_cancel.grid(row=0, column=1, sticky="e", padx=(0, 10))

        self.btn_start = ctk.CTkButton(
            action_bar,
            text="  ▶  Start OCR",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            command=self._on_start_ocr,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=2, sticky="e")

        self._log("Ready — select a folder of scanned images to get started.", "info")

    def _on_select_folder(self):
        folder = pick_folder("Select folder with images to OCR into PDFs")

        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        self.selected_folder = folder
        self.folder_label.configure(
            text=str(folder),
            text_color=self.theme["fg_primary"],
        )
        self._log(f"Folder: {folder}", "info")
        self._refresh_folder_summary()

    def _on_option_change(self):
        if self.selected_folder:
            self._refresh_folder_summary()

    def _refresh_folder_summary(self):
        files = find_ocr_input_files(
            self.selected_folder,
            recurse=self.recurse_var.get(),
        )

        if not files:
            self.file_count_lbl.grid_remove()
            self.btn_start.configure(state="disabled")
            self._set_info(
                f"✕  No supported image files found in '{self.selected_folder.name}'.",
                level="error",
            )
            self._log("No supported image files found for OCR.", "warning")
            return

        self.file_count_lbl.configure(text=f"  {len(files)} images  ")
        self.file_count_lbl.grid(row=0, column=2, padx=(0, 14))
        self.btn_start.configure(state="normal")
        recurse_text = "including subfolders" if self.recurse_var.get() else "in the selected folder"
        self._set_info(
            f"✓  Found {len(files)} image file(s) {recurse_text} — click Start to begin.",
            level="success",
        )
        self._log(f"Found {len(files)} image file(s) ready for OCR.", "success")

    def _on_start_ocr(self):
        if not self.selected_folder:
            self._log("No folder selected.", "error")
            return

        language = self.language_var.get().strip() or "eng"
        self.language_var.set(language)

        ok, error_msg, dependency_info = check_ocr_dependencies(
            language=language,
            require_pdfa=self.save_pdfa_var.get(),
        )
        if not ok:
            self._set_info(f"✕  {error_msg}", level="error")
            self._log(error_msg, "error")
            return

        files = find_ocr_input_files(
            self.selected_folder,
            recurse=self.recurse_var.get(),
        )
        if not files:
            self._set_info("✕  No supported image files found.", level="error")
            self._log("No supported image files found for OCR.", "error")
            return

        self.output_folder = create_output_folder(self.selected_folder, "ocr-pdf")
        error_root = create_error_folder(self.selected_folder)
        if not self.output_folder or not error_root:
            self._set_info("✕  Failed to create OCR output folders.", level="error")
            self._log("Failed to create OCR output folders.", "error")
            return
        self.error_folder = error_root / "ocr-pdf"
        self.error_folder.mkdir(parents=True, exist_ok=True)

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.btn_cancel.configure(state="normal")
        self.btn_error_report.configure(state="disabled")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "ocr_pdf"
        self.has_errors = False

        self.parent.set_status("Starting OCR to PDF…", 0.0)
        self._set_info(
            (
                f"Running OCR on {len(files)} image file(s) using language '{language}'. "
                f"PDF/A is {'on' if self.save_pdfa_var.get() else 'off'}."
            ),
            level="info",
        )
        self._log("Starting OCR to PDF operation…", "info")
        self._log(
            f"Using Tesseract at: {dependency_info.get('tesseract_path')}",
            "info",
        )
        if self.save_pdfa_var.get():
            self._log("PDF/A backend: OCRmyPDF", "info")

        self.worker = OcrPdfWorker(
            input_folder=self.selected_folder,
            output_folder=self.output_folder,
            error_folder=self.error_folder,
            recurse=self.recurse_var.get(),
            language=language,
            skip_existing=self.skip_existing_var.get(),
            save_pdfa=self.save_pdfa_var.get(),
            skip_messy=self.skip_messy_var.get(),
            tesseract_path=dependency_info.get("tesseract_path"),
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

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self.btn_cancel.configure(state="disabled")
            self._log("Cancellation requested… finishing current file safely.", "warning")
            self._set_info(
                "Cancellation requested — waiting for the current OCR step to stop.",
                level="warning",
            )

    def _on_progress(self, progress: dict):
        current = progress["current"]
        total = progress["total"]
        pct = progress["percentage"] / 100.0
        filename = progress.get("filename", "")

        self.parent.set_status(f"OCR {current} / {total} — {filename}", pct)
        self._log(f"OCR: {filename}", "info")

    def _on_status(self, message: str):
        self.parent.set_status(message)
        if message.startswith((
            "Checking ",
            "Operation cancelled",
            "Scanning ",
            "Found ",
            "Skipped:",
            "Cancelled",
            "✅",
            "No supported",
        )):
            self._log(message, "info")

    def _on_error(self, filename: str, error_message: str):
        self.has_errors = True
        self._log(f"{filename} — {error_message}", "error")
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
            cancelled = results.get("cancelled", False)
            level = "warning" if self.has_errors or cancelled else "success"

            if cancelled:
                summary = (
                    f"Stopped — {results['success']} OCR'd, "
                    f"{results['skipped']} skipped, {results['failed']} failed."
                )
            else:
                summary = (
                    f"Done — {results['success']} OCR'd, "
                    f"{results['skipped']} skipped, {results['failed']} failed."
                )

            self._log(summary, level)
            self._set_info(
                (
                    f"✓  Complete — {results['success']} OCR'd  ·  "
                    f"{results['skipped']} skipped  ·  {results['failed']} failed"
                )
                if not cancelled
                else (
                    f"⚠  Cancelled — {results['success']} OCR'd  ·  "
                    f"{results['skipped']} skipped  ·  {results['failed']} failed"
                ),
                level=level,
            )

            if results.get("errors"):
                self._generate_error_report(results)
                self.btn_error_report.configure(state="normal")

        self.btn_start.configure(state="normal", text="  ▶  Start OCR")
        self.btn_cancel.configure(state="disabled")
        self.parent.operation_in_progress = False
        self.parent.set_status("Ready", 1.0)

    def _on_view_error_report(self):
        if not self.error_folder or not self.error_folder.exists():
            self._log("No OCR error folder found.", "warning")
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
            self._log(f"Opened OCR error folder: {self.error_folder}", "info")
        except Exception as exc:
            self._log(f"Failed to open error folder: {exc}", "error")

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _set_info(self, text: str, level: str = "info"):
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

    def _log(self, message: str, level: str = "info"):
        prefixes = {
            "info": "  ·  ",
            "success": "  ✓  ",
            "warning": "  ⚠  ",
            "error": "  ✕  ",
        }
        prefix = prefixes.get(level, "  ·  ")
        self.log_display.configure(state="normal")
        self.log_display.insert("end", f"{prefix}{message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    def _generate_error_report(self, results: dict):
        if not self.error_folder:
            return

        report_file = self.error_folder / "OCR_PDF_ERROR_REPORT.txt"
        lines = [
            "DPA Image Toolkit — OCR to PDF Error Report",
            "=" * 60,
            "",
            f"Total Errors: {len(results['errors'])}",
            "",
        ]
        for error in results["errors"]:
            lines += [
                f"File:  {error['file']}",
                f"Error: {error['error']}",
                "",
            ]

        lines += [
            "=" * 60,
            "Review the listed files and rerun OCR after fixing any input or dependency issues.",
        ]

        try:
            report_file.write_text("\n".join(lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as exc:
            self._log(f"Failed to save error report: {exc}", "error")
