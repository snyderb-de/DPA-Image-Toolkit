"""
OCR-to-PDF panel for DPA Image Toolkit.

Convert a folder of images into searchable PDFs.
"""

import customtkinter as ctk
from pathlib import Path

from modules.ocr_pdf.core import (
    check_ocr_dependencies,
    find_ocr_input_files,
    get_ocr_dependency_statuses,
    group_ocr_input_files,
    summarize_ocr_documents,
)
from utils.file_handler import create_error_folder, create_output_folder, pick_folder
from utils.tool_dependencies import show_dependency_warning
from utils.worker import OcrPdfWorker
from .dependency_sidebar import create_status_icon_canvas, draw_status_icon
from .styles import BUTTON, RADIUS, get_font

DEFAULT_OCR_LANGUAGE = "eng"


class OcrPdfPanel:
    """OCR-to-PDF panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.worker: OcrPdfWorker = None
        self.selected_folder: Path = None
        self.output_folder: Path = None
        self.error_folder: Path = None
        self.selected_files: list[Path] = []
        self.has_errors = False

        self.skip_existing_var = ctk.BooleanVar(value=True)
        self.skip_messy_var = ctk.BooleanVar(value=True)

        self.folder_label = None
        self.file_count_lbl = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_cancel = None
        self.btn_error_report = None
        self.btn_new_job = None
        self.dependency_rows = []

    def build(self, container):
        t = self.theme

        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(5, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=0)

        hdr_row = ctk.CTkFrame(panel, fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))
        hdr_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr_row,
            text="Convert a folder of images to OCR'd PDF",
            font=get_font("title"),
            text_color=t["fg_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="sw")

        ctk.CTkLabel(
            hdr_row,
            text="OCR every image in one folder, combine matching sequence sets into multi-page PDFs, and save all results into a PDFs subfolder.",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            anchor="w",
            justify="left",
            wraplength=560,
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
            text="  📁  Select Scan Folder",
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
            text="Select a folder of images to begin.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        side_panel = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["xl"],
            border_width=1,
            border_color=t["border_subtle"],
            width=300,
        )
        side_panel.grid(row=1, column=1, rowspan=5, sticky="nsew", padx=(0, 36), pady=(24, 0))
        side_panel.grid_propagate(False)

        side_inner = ctk.CTkFrame(side_panel, fg_color="transparent")
        side_inner.pack(fill="both", expand=True, padx=20, pady=20)
        side_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            side_inner,
            text="DEPENDENCY CHECK",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            side_inner,
            text="OCR readiness for this machine",
            font=get_font("normal"),
            text_color=t["fg_primary"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 12))

        dep_frame = ctk.CTkFrame(
            side_inner,
            fg_color=t["bg_glass"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        dep_frame.grid(row=2, column=0, sticky="ew")
        dep_frame.grid_columnconfigure(0, weight=1)

        initial_statuses = get_ocr_dependency_statuses(
            language=DEFAULT_OCR_LANGUAGE,
            require_pdfa=False,
        )

        self.dependency_rows = []
        for index in range(len(initial_statuses)):
            row = ctk.CTkFrame(dep_frame, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", padx=14, pady=(10 if index == 0 else 4, 8))
            row.grid_columnconfigure(1, weight=1)

            icon = create_status_icon_canvas(
                row,
                background=t["bg_glass"],
            )
            icon.grid(row=0, column=0, sticky="nw", padx=(0, 6), pady=(1, 0))

            label = ctk.CTkLabel(
                row,
                text="",
                font=get_font("small"),
                text_color=t["fg_primary"],
                anchor="w",
                justify="left",
                wraplength=220,
            )
            label.grid(row=0, column=1, sticky="w")

            detail = ctk.CTkLabel(
                row,
                text="",
                font=get_font("micro"),
                text_color=t["fg_tertiary"],
                anchor="w",
                justify="left",
                wraplength=220,
            )
            detail.grid(row=1, column=1, sticky="w", pady=(2, 0))
            self.dependency_rows.append((icon, label, detail))

        support_card = ctk.CTkFrame(
            side_inner,
            fg_color=t["accent_dim"],
            corner_radius=RADIUS["lg"],
            border_width=0,
        )
        support_card.grid(row=3, column=0, sticky="ew", pady=(16, 0))

        ctk.CTkLabel(
            support_card,
            text="WHAT THIS MEANS",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(14, 2))

        for line in (
            "✅ means the dependency is ready.",
            "❌ means the tool cannot use that dependency right now.",
            "Searchable PDFs only need the standard OCR stack.",
            "If a dependency is missing, contact support for installation on this machine.",
        ):
            line_row = ctk.CTkFrame(support_card, fg_color="transparent")
            line_row.pack(fill="x", padx=14, pady=(0, 6), anchor="w")
            line_row.grid_columnconfigure(2, weight=1)

            ctk.CTkLabel(
                line_row,
                text="•",
                font=get_font("small"),
                text_color=t["fg_secondary"],
                anchor="n",
                width=10,
            ).grid(row=0, column=0, sticky="nw")

            leading_icon, body = self._split_status_line(line)
            if leading_icon:
                icon = create_status_icon_canvas(
                    line_row,
                    background=t["accent_dim"],
                )
                draw_status_icon(icon, leading_icon == "✅")
                icon.grid(row=0, column=1, sticky="nw", padx=(4, 6), pady=(1, 0))

            ctk.CTkLabel(
                line_row,
                text=body,
                font=get_font("small"),
                text_color=t["fg_secondary"],
                justify="left",
                wraplength=190 if leading_icon else 228,
                anchor="w",
            ).grid(row=0, column=2 if leading_icon else 1, sticky="w")

        options_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        options_card.grid(row=3, column=0, sticky="ew", padx=36, pady=(12, 0))
        options_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            options_card,
            text="PDF OPTIONS",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        top_options_row = ctk.CTkFrame(options_card, fg_color="transparent")
        top_options_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        top_options_row.grid_columnconfigure(0, weight=1)

        ctk.CTkCheckBox(
            top_options_row,
            text="Skip existing output PDF",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.skip_existing_var,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkCheckBox(
            options_card,
            text="Skip OCR if any page fails the quality precheck",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.skip_messy_var,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 14))

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
            "Files ending in _### are grouped into one PDF and ordered by that sequence number.",
            "Files without a trailing sequence become single-page PDFs.",
            "All output PDFs are saved into a PDFs subfolder inside the selected folder.",
            "OCR currently runs in English only.",
            "Output PDFs keep filename-based titles with no extra metadata step.",
            "Searchable PDF is the standard output.",
            "The quality precheck may skip a PDF when its pages look too messy to produce trustworthy OCR text.",
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
            text="  ▶  Start OCR",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            text_color_disabled=t["button_disabled_text"],
            command=self._on_start_ocr,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=3, sticky="e")

        self._refresh_dependency_panel()
        self._log("Ready — select a folder of images to create OCR'd PDFs.", "info")

    def _on_select_folder(self):
        folder = pick_folder("Select folder containing scan images to OCR into PDFs")
        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        files = find_ocr_input_files(folder)
        if not files:
            self._set_info(
                f"✕  No supported image files found in '{folder.name}'.",
                level="error",
            )
            self._log("No supported image files found for the selected folder.", "error")
            self.btn_start.configure(state="disabled")
            return

        self.selected_folder = folder
        self.selected_files = files
        document_groups = group_ocr_input_files(folder)
        summary = summarize_ocr_documents(document_groups)
        self.folder_label.configure(text=str(folder), text_color=self.theme["fg_primary"])
        self.file_count_lbl.configure(
            text=f"  {summary['page_count']} pages / {summary['document_count']} PDFs  "
        )
        self.file_count_lbl.grid(row=0, column=2, padx=(0, 14))

        self._log(f"Folder: {folder}", "info")
        self._log(
            (
                f"Found {summary['page_count']} page image(s) that will become "
                f"{summary['document_count']} PDF(s)."
            ),
            "success",
        )
        self._refresh_dependency_panel()
        self.btn_start.configure(state="normal")
        self._set_info(
            (
                f"✓  Ready to OCR {summary['page_count']} page(s) into "
                f"{summary['document_count']} PDF(s)."
            ),
            level="success",
        )
        self._log("OCR PDF batch is ready to start.", "success")

    def _refresh_dependency_panel(self):
        statuses = get_ocr_dependency_statuses(
            language=DEFAULT_OCR_LANGUAGE,
            require_pdfa=False,
        )

        for (icon_widget, label_widget, detail_widget), status in zip(self.dependency_rows, statuses):
            draw_status_icon(icon_widget, status["ok"])
            label_widget.configure(text=status["label"])
            detail_widget.configure(text=status["detail"])

    def _on_start_ocr(self):
        if not self.selected_folder:
            self._log("Select a folder before starting OCR.", "error")
            return

        language = DEFAULT_OCR_LANGUAGE

        ok, error_msg, dependency_info = check_ocr_dependencies(
            language=language,
            require_pdfa=False,
        )
        self._refresh_dependency_panel()
        if not ok:
            show_dependency_warning(self.parent, "OCR to PDF", error_msg)
            self._set_info(
                "⚠  OCR to PDF dependencies are missing. Contact support for installation.",
                level="warning",
            )
            self._log(error_msg, "warning")
            self._log("Contact support for dependency installation on this machine.", "warning")
            return
        if error_msg:
            self._log(error_msg, "warning")
            self._set_info(f"⚠  {error_msg}", level="warning")

        document_summary = summarize_ocr_documents(group_ocr_input_files(self.selected_folder))

        self.output_folder = create_output_folder(self.selected_folder, "PDFs")
        error_root = create_error_folder(self.selected_folder)
        if not self.output_folder or not error_root:
            self._set_info("✕  Failed to create OCR output folders.", level="error")
            self._log("Failed to create OCR output folders.", "error")
            return

        self.error_folder = error_root / "ocr-pdf"
        self.error_folder.mkdir(parents=True, exist_ok=True)

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.btn_new_job.configure(state="normal")
        self.btn_cancel.configure(state="normal")
        self.btn_error_report.configure(state="disabled")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "ocr_pdf"
        self.has_errors = False

        self.parent.set_status("Starting OCR to PDF…", 0.0)
        self._set_info(
            (
                f"Running OCR on {document_summary['page_count']} page(s) into "
                f"{document_summary['document_count']} PDF(s). "
                f"Quality precheck is {'on' if self.skip_messy_var.get() else 'off'}."
            ),
            level="info",
        )
        self._log("Starting OCR PDF batch…", "info")
        self._log(f"Using Tesseract at: {dependency_info.get('tesseract_path')}", "info")
        self._log(f"Output folder: {self.output_folder}", "info")

        self.worker = OcrPdfWorker(
            input_folder=self.selected_folder,
            output_folder=self.output_folder,
            error_folder=self.error_folder,
            language=language,
            skip_existing=self.skip_existing_var.get(),
            save_pdfa=False,
            skip_messy=self.skip_messy_var.get(),
            metadata=None,
            tesseract_path=dependency_info.get("tesseract_path"),
        )
        self.worker.set_progress_callback(lambda p: self._dispatch(self._on_progress, p))
        self.worker.set_status_callback(lambda m: self._dispatch(self._on_status, m))
        self.worker.set_error_callback(lambda f, e: self._dispatch(self._on_error, f, e))

        self.worker.start()
        self._poll_worker()

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self.btn_cancel.configure(state="disabled")
            self._log("Cancellation requested… waiting for the current document step to stop.", "warning")
            self._set_info(
                "Cancellation requested — waiting for the current PDF OCR step to stop.",
                level="warning",
            )

    def _on_progress(self, progress: dict):
        current = progress["current"]
        total = progress["total"]
        pct = progress["percentage"] / 100.0
        filename = progress.get("filename", "")

        self.parent.set_status(f"OCR {current} / {total} — {filename}", pct)

    def _on_status(self, message: str):
        self.parent.set_status(message)
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
                summary = "Stopped — OCR batch was cancelled."
            elif results["success"]:
                summary = (
                    f"Done — {results['success']} PDF(s) OCR'd successfully."
                )
            elif results["skipped"]:
                summary = "Stopped — all PDFs were skipped."
            else:
                summary = "Done — OCR batch failed."

            self._log(summary, level)
            self._set_info(
                (
                    f"✓  Complete — created {results['success']} OCR PDF(s)."
                    if results["success"]
                    else (
                        "⚠  Cancelled — OCR batch stopped before completion."
                        if cancelled
                        else (
                            "⚠  Skipped — all PDFs were skipped by current rules."
                            if results["skipped"] and not results["failed"]
                            else "✕  Failed — OCR batch did not complete."
                        )
                    )
                ),
                level=level,
            )

            if results.get("errors") or results.get("skip_reasons"):
                self._generate_error_report(results)
                self.btn_error_report.configure(state="normal")

        self.btn_start.configure(
            state="normal" if self.selected_folder else "disabled",
            text="  ▶  Start OCR",
        )
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
        self.selected_files = []
        self.has_errors = False

        self.folder_label.configure(text="No folder selected", text_color=self.theme["fg_tertiary"])
        self.file_count_lbl.grid_remove()
        self.btn_start.configure(state="disabled", text="  ▶  Start OCR")
        self.btn_cancel.configure(state="disabled")
        self.btn_error_report.configure(state="disabled")
        self.btn_new_job.configure(state="normal")
        self._set_info("Select a folder of images to begin.", level="info")
        self._clear_log()
        self._refresh_dependency_panel()
        self.parent.operation_in_progress = False
        self.parent.operation_type = None
        self.parent.set_status("Ready", 1.0)
        self._log("Ready — select a folder of images to create OCR'd PDFs.", "info")

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
        ]

        if results.get("errors"):
            lines += [f"Errors: {len(results['errors'])}", ""]
            for error in results["errors"]:
                lines += [
                    f"File:  {error['file']}",
                    f"Error: {error['error']}",
                    "",
                ]

        if results.get("skip_reasons"):
            lines += [f"Skip Reasons: {len(results['skip_reasons'])}", ""]
            for item in results["skip_reasons"]:
                lines += [
                    f"Item:   {item['file']}",
                    f"Reason: {item['reason']}",
                    "",
                ]

        try:
            report_file.write_text("\n".join(lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as exc:
            self._log(f"Failed to save error report: {exc}", "error")

    def _split_status_line(self, text: str):
        if text.startswith("✅ "):
            return "✅", text[2:].lstrip()
        if text.startswith("❌ "):
            return "❌", text[2:].lstrip()
        return None, text
