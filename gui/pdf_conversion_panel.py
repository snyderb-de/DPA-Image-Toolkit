"""
PDF conversion panel for DPA Image Toolkit.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

import customtkinter as ctk

from modules.pdf_tools.compression_profiles import (
    DEFAULT_PROFILE_KEY,
    get_profile_key_from_label,
    get_profile_label,
    get_profile_labels,
)
from modules.pdf_tools.core import (
    DEFAULT_PDFA_PROFILE_KEY,
    check_pdf_conversion_dependencies,
    get_pdf_conversion_dependency_statuses,
    get_pdfa_profile_key_from_label,
    get_pdfa_profile_label,
    get_pdfa_profile_labels,
)
from utils.file_handler import create_error_folder, pick_files, pick_folder
from utils.tool_dependencies import show_dependency_warning
from utils.worker import PdfConversionWorker
from .dependency_sidebar import build_dependency_sidebar, refresh_dependency_sidebar
from .styles import BUTTON, RADIUS, get_font


class PdfConversionPanel:
    """PDF conversion panel controller."""

    OPERATION_OPTIONS = {
        "Reduce Size": "reduce_size",
        "Split PDF": "split_pdf",
        "Extract Pages": "extract_pages",
        "PDF/A (Preview)": "pdfa",
    }

    SPLIT_OUTPUT_OPTIONS = {
        "Single-page PDFs": "pdfs",
        "JPEG Images": "jpeg",
        "PNG Images": "png",
        "TIFF Images": "tiff",
    }

    REMOVE_MODE_OPTIONS = {
        "Create remaining PDF": "safe",
    }

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.worker: PdfConversionWorker = None
        self.selection_mode = None
        self.selected_file: Path = None
        self.selected_folder: Path = None
        self.error_folder: Path = None

        self.operation_var = ctk.StringVar(value="Reduce Size")
        self.reduce_pdf_var = ctk.BooleanVar(value=True)
        self.compression_mode_var = ctk.StringVar(value=get_profile_label(DEFAULT_PROFILE_KEY))
        self.split_output_var = ctk.StringVar(value="Single-page PDFs")
        self.extract_pages_var = ctk.StringVar(value="")
        self.extract_pages_var.trace_add("write", lambda *_: self._refresh_start_state())
        self.remove_extracted_var = ctk.BooleanVar(value=False)
        self.remove_mode_var = ctk.StringVar(value="Create remaining PDF")
        self.pdfa_mode_var = ctk.StringVar(value=get_pdfa_profile_label(DEFAULT_PDFA_PROFILE_KEY))

        self.selection_label = None
        self.count_label = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
        self.btn_cancel = None
        self.btn_new_job = None
        self.btn_error_report = None
        self.dependency_rows = []

        self.reduce_options_frame = None
        self.split_options_frame = None
        self.extract_options_frame = None
        self.pdfa_options_frame = None
        self.remove_mode_menu = None
        self.compression_mode_menu = None
        self.pdfa_mode_menu = None

    def build(self, container):
        t = self.theme

        panel = ctk.CTkScrollableFrame(container, fg_color="transparent", corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(4, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=0)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=36, pady=(22, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="PDF Conversion",
            font=get_font("title"),
            text_color=t["fg_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="sw")

        ctk.CTkLabel(
            header,
            text="Reduce PDF size, split one PDF into pages/images, and extract page ranges.",
            font=get_font("normal"),
            text_color=t["fg_secondary"],
            anchor="w",
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
        picker_card.grid(row=1, column=0, sticky="ew", padx=36, pady=(14, 0))
        picker_card.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            picker_card,
            text="  📄  Select PDF File",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=self._on_select_file,
        ).grid(row=0, column=0, padx=(14, 10), pady=14, sticky="w")

        ctk.CTkButton(
            picker_card,
            text="  📁  Select Folder",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=self._on_select_folder,
        ).grid(row=0, column=1, padx=(0, 10), pady=14, sticky="w")

        self.selection_label = ctk.CTkLabel(
            picker_card,
            text="No PDF file or folder selected",
            font=get_font("small"),
            text_color=t["fg_tertiary"],
            anchor="w",
        )
        self.selection_label.grid(row=0, column=2, padx=(0, 14), pady=14, sticky="ew")

        self.count_label = ctk.CTkLabel(
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
        self.info_card.grid(row=2, column=0, sticky="ew", padx=36, pady=(10, 0))

        self.info_lbl = ctk.CTkLabel(
            self.info_card,
            text="Select a PDF file or a folder to begin.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        side_panel, self.dependency_rows = build_dependency_sidebar(
            panel,
            t,
            heading="PDF conversion readiness for this machine",
            statuses=get_pdf_conversion_dependency_statuses(operation="reduce_size"),
            support_lines=(
                "✅ means the dependency is ready.",
                "❌ means the active operation cannot use that dependency right now.",
                "pypdfium2 is only required for JPEG/PNG/TIFF page export.",
                "If a dependency is missing, contact support for installation on this machine.",
            ),
            process_notes=(
                "Reduce Size can run on one PDF file or an entire folder of PDFs.",
                "Split PDF and Extract Pages are single-file operations only.",
                "Extract Pages writes new PDFs and never changes the source PDF.",
                "PDF/A mode is shown now and will be fully enabled after rule documentation is finalized.",
            ),
        )
        side_panel.grid(row=1, column=1, rowspan=5, sticky="nsew", padx=(0, 36), pady=(14, 0))

        options_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        options_card.grid(row=3, column=0, sticky="ew", padx=36, pady=(10, 0))
        options_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            options_card,
            text="PDF OPTIONS",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        operation_row = ctk.CTkFrame(options_card, fg_color="transparent")
        operation_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        operation_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            operation_row,
            text="Operation",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkOptionMenu(
            operation_row,
            values=list(self.OPERATION_OPTIONS.keys()),
            variable=self.operation_var,
            command=lambda _value: self._on_operation_changed(),
            font=get_font("small"),
            dropdown_font=get_font("small"),
            width=240,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        ).grid(row=0, column=1, sticky="e")

        self.reduce_options_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.reduce_options_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.reduce_options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkCheckBox(
            self.reduce_options_frame,
            text="Reduce PDF size",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.reduce_pdf_var,
            command=self._toggle_compression_mode,
        ).grid(row=0, column=0, sticky="w")

        self.compression_mode_menu = ctk.CTkOptionMenu(
            self.reduce_options_frame,
            values=get_profile_labels(),
            variable=self.compression_mode_var,
            font=get_font("small"),
            dropdown_font=get_font("small"),
            width=240,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        )
        self.compression_mode_menu.grid(row=0, column=1, sticky="e")

        self.split_options_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.split_options_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.split_options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.split_options_frame,
            text="Split Output",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkOptionMenu(
            self.split_options_frame,
            values=list(self.SPLIT_OUTPUT_OPTIONS.keys()),
            variable=self.split_output_var,
            command=lambda _value: self._refresh_dependency_panel(),
            font=get_font("small"),
            dropdown_font=get_font("small"),
            width=240,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        ).grid(row=0, column=1, sticky="e")

        self.extract_options_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.extract_options_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.extract_options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.extract_options_frame,
            text="Page Selection",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkEntry(
            self.extract_options_frame,
            textvariable=self.extract_pages_var,
            font=get_font("small"),
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            placeholder_text="e.g., 1,3,5-8",
            placeholder_text_color=t["fg_tertiary"],
            justify="left",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkCheckBox(
            self.extract_options_frame,
            text="Write remaining-pages copy",
            font=get_font("small"),
            text_color=t["fg_primary"],
            variable=self.remove_extracted_var,
            command=self._toggle_extract_remove_mode,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 6))

        self.remove_mode_menu = ctk.CTkOptionMenu(
            self.extract_options_frame,
            values=list(self.REMOVE_MODE_OPTIONS.keys()),
            variable=self.remove_mode_var,
            font=get_font("small"),
            dropdown_font=get_font("small"),
            width=300,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        )
        self.remove_mode_menu.grid(row=2, column=0, columnspan=2, sticky="w")

        self.pdfa_options_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        self.pdfa_options_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.pdfa_options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.pdfa_options_frame,
            text="Conformance",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.pdfa_mode_menu = ctk.CTkOptionMenu(
            self.pdfa_options_frame,
            values=get_pdfa_profile_labels(),
            variable=self.pdfa_mode_var,
            font=get_font("small"),
            dropdown_font=get_font("small"),
            width=240,
            height=BUTTON["height_sm"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            button_color=t["bg_tertiary"],
            button_hover_color=t["border_subtle"],
            text_color=t["fg_primary"],
            dropdown_fg_color=t["bg_secondary"],
            dropdown_text_color=t["fg_primary"],
            dropdown_hover_color=t["bg_tertiary"],
        )
        self.pdfa_mode_menu.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            self.pdfa_options_frame,
            text="Use VeraPDF to validate resulting PDF/A compliance when needed.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
            justify="left",
            wraplength=700,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        log_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        log_card.grid(row=4, column=0, sticky="nsew", padx=36, pady=(10, 0))
        log_card.grid_rowconfigure(2, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        log_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_header,
            text="ACTIVITY LOG",
            font=get_font("eyebrow"),
            text_color=t["fg_tertiary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_header,
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
        action_bar.grid(row=5, column=0, sticky="ew", padx=36, pady=(10, 18))
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
            text="  ▶  Start",
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

        self._toggle_compression_mode()
        self._toggle_extract_remove_mode()
        self._on_operation_changed()
        self._log("Ready — select a PDF file or folder.", "info")

    # Selection
    def _on_select_file(self):
        files = pick_files(
            "Select one PDF file",
            filetypes=[("PDF files", "*.pdf *.PDF")],
            initial_dir=self.parent.get_last_source_directory(),
        )
        if not files:
            self._log("File selection cancelled.", "info")
            return

        pdf_files = [path for path in files if path.suffix.lower() == ".pdf"]
        if not pdf_files:
            self._set_info("✕  No PDF file selected.", "error")
            self._log("No valid PDF file selected.", "error")
            return

        self.selection_mode = "file"
        self.selected_file = pdf_files[0]
        self.selected_folder = None
        self.parent.set_last_source_directory(self.selected_file.parent)
        self.error_folder = self._prepare_error_folder(self.selected_file.parent)

        self.selection_label.configure(text=str(self.selected_file), text_color=self.theme["fg_primary"])
        self.count_label.configure(text="  1 PDF file  ")
        self.count_label.grid(row=0, column=3, padx=(0, 14))
        self._set_info("✓  PDF file selected.", "success")
        self._log(f"Selected file: {self.selected_file.name}", "success")
        self._refresh_start_state()
        self._refresh_dependency_panel()

    def _on_select_folder(self):
        folder = pick_folder(
            "Select folder containing PDFs",
            initial_dir=self.parent.get_last_source_directory(),
        )
        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        self.parent.set_last_source_directory(folder)
        pdf_files = sorted(
            [
                path for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() == ".pdf"
            ],
            key=lambda path: path.name.lower(),
        )
        if not pdf_files:
            self._set_info(f"✕  No PDF files found in '{folder.name}'.", "error")
            self._log("No PDF files found in selected folder.", "error")
            return

        self.selection_mode = "folder"
        self.selected_folder = folder
        self.selected_file = None
        self.error_folder = self._prepare_error_folder(folder)

        self.selection_label.configure(text=str(folder), text_color=self.theme["fg_primary"])
        self.count_label.configure(text=f"  {len(pdf_files)} PDF files  ")
        self.count_label.grid(row=0, column=3, padx=(0, 14))
        self._set_info(f"✓  Folder selected with {len(pdf_files)} PDF file(s).", "success")
        self._log(f"Selected folder: {folder}", "info")
        self._log(f"Found {len(pdf_files)} PDF file(s).", "success")
        self._refresh_start_state()
        self._refresh_dependency_panel()

    # Option controls
    def _on_operation_changed(self):
        operation = self._active_operation_key()
        self.reduce_options_frame.grid_remove()
        self.split_options_frame.grid_remove()
        self.extract_options_frame.grid_remove()
        self.pdfa_options_frame.grid_remove()

        if operation == "reduce_size":
            self.reduce_options_frame.grid()
            self.btn_start.configure(text="  ▶  Start Reduce")
        elif operation == "split_pdf":
            self.split_options_frame.grid()
            self.btn_start.configure(text="  ▶  Start Split")
        elif operation == "extract_pages":
            self.extract_options_frame.grid()
            self.btn_start.configure(text="  ▶  Start Extract")
        else:
            self.pdfa_options_frame.grid()
            self.btn_start.configure(text="  ▶  Start PDF/A")

        self._refresh_start_state()
        self._refresh_dependency_panel()

    def _toggle_compression_mode(self):
        if not self.compression_mode_menu:
            return
        state = "normal" if self.reduce_pdf_var.get() else "disabled"
        self.compression_mode_menu.configure(state=state)

    def _toggle_extract_remove_mode(self):
        if not self.remove_mode_menu:
            return
        state = "normal" if self.remove_extracted_var.get() else "disabled"
        self.remove_mode_menu.configure(state=state)

    # Dependencies
    def _dependency_operation_key(self) -> str:
        operation = self._active_operation_key()
        if operation == "split_pdf" and self._split_output_key() in {"jpeg", "png", "tiff"}:
            return "split_images"
        if operation == "extract_pages":
            return "extract_pages"
        return operation

    def _refresh_dependency_panel(self):
        statuses = get_pdf_conversion_dependency_statuses(
            operation=self._dependency_operation_key(),
        )
        refresh_dependency_sidebar(self.dependency_rows, statuses)

    # Actions
    def _on_start(self):
        operation = self._active_operation_key()
        if not self.selection_mode:
            self._set_info("✕  Select a PDF file or folder first.", "error")
            self._log("No source selected.", "error")
            return

        if operation in {"split_pdf", "extract_pages"} and self.selection_mode != "file":
            self._set_info("✕  This operation requires one PDF file.", "error")
            self._log("Selected operation requires a single file.", "warning")
            return

        if operation == "extract_pages" and not self.extract_pages_var.get().strip():
            self._set_info("✕  Enter page selection (e.g., 1,3,5-8).", "error")
            self._log("Page selection is required for extract.", "error")
            return

        dependency_operation = self._dependency_operation_key()
        ok, error_msg = check_pdf_conversion_dependencies(dependency_operation)
        self._refresh_dependency_panel()
        if not ok:
            show_dependency_warning(self.parent, "PDF Conversion", error_msg or "Missing dependency.")
            self._set_info(f"⚠  {error_msg}", "warning")
            self._log(error_msg or "Missing dependency.", "warning")
            return

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.btn_cancel.configure(state="normal", text="  ■  Cancel")
        self.btn_error_report.configure(state="disabled")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "pdf_conversion"

        input_path = self.selected_file if self.selection_mode == "file" else self.selected_folder
        self.worker = PdfConversionWorker(
            selection_mode=self.selection_mode,
            input_path=input_path,
            operation=operation,
            reduce_size_enabled=self.reduce_pdf_var.get(),
            compression_profile_key=get_profile_key_from_label(self.compression_mode_var.get()),
            split_output_type=self._split_output_key(),
            extract_page_spec=self.extract_pages_var.get().strip(),
            remove_extracted_pages=self.remove_extracted_var.get(),
            extract_removal_mode=self._remove_mode_key(),
            pdfa_profile_key=get_pdfa_profile_key_from_label(self.pdfa_mode_var.get()),
        )
        self.worker.set_progress_callback(lambda p: self._dispatch(self._on_progress, p))
        self.worker.set_status_callback(lambda m: self._dispatch(self._on_status, m))
        self.worker.set_error_callback(lambda f, e: self._dispatch(self._on_error, f, e))
        if operation == "reduce_size":
            if self.reduce_pdf_var.get():
                self._log(f"Reduce profile: {self.compression_mode_var.get()}", "info")
            else:
                self._log("Reduce size: Off (copy only)", "info")
        elif operation == "pdfa":
            self._log(f"PDF/A profile: {self.pdfa_mode_var.get()}", "info")
        self.worker.start()
        self._log(f"Starting {self.operation_var.get()}...", "info")
        self._poll_worker()

    def _on_cancel(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self.btn_cancel.configure(state="disabled", text="  ⏳  Stopping…")
            self._set_info("Cancellation requested — finishing active step.", "warning")
            self._log("Cancellation requested.", "warning")

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.05)
            self.parent.after(100, self._poll_worker)
            return
        self._on_worker_done()

    def _on_worker_done(self):
        results = self.worker.get_results() if self.worker else {}
        cancelled = results.get("cancelled", False)
        level = "warning" if cancelled or results.get("failed", 0) else "success"

        if cancelled:
            self._set_info(
                f"⚠  Cancelled — {results.get('success', 0)} complete  ·  {results.get('failed', 0)} failed",
                "warning",
            )
            self._log("Operation cancelled by user.", "warning")
        else:
            self._set_info(
                f"✓  Complete — {results.get('success', 0)} complete  ·  {results.get('failed', 0)} failed",
                level,
            )
            self._log(
                f"Done — {results.get('success', 0)} complete, {results.get('failed', 0)} failed.",
                level,
            )

        if results.get("errors"):
            self._generate_error_report(results)
            self.btn_error_report.configure(state="normal")

        self.btn_start.configure(state="normal")
        self._on_operation_changed()
        self.btn_cancel.configure(state="disabled", text="  ■  Cancel")
        self.parent.operation_in_progress = False
        self.parent.operation_type = None
        self.parent.set_status("Ready", 1.0)

    def _on_progress(self, progress: dict):
        current = progress.get("current", 0)
        total = progress.get("total", 1)
        pct = progress.get("percentage", 0.0) / 100.0
        filename = progress.get("filename", "")
        self.parent.set_status(f"{self.operation_var.get()} {current}/{total} — {filename}", pct)

    def _on_status(self, message: str):
        self.parent.set_status(message)
        level = "warning" if "cancel" in message.lower() else "info"
        if "✅" in message:
            level = "success"
        if "error" in message.lower():
            level = "error"
        self._log(message, level)

    def _on_error(self, filename: str, error_message: str):
        self._log(f"{filename} — {error_message}", "error")

    def _on_view_error_report(self):
        if not self.error_folder or not self.error_folder.exists():
            self._log("No error folder found.", "warning")
            return
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

    def _on_clear_new_job(self):
        if self.worker and self.worker.is_alive():
            return

        self.worker = None
        self.selection_mode = None
        self.selected_file = None
        self.selected_folder = None
        self.error_folder = None
        self.selection_label.configure(text="No PDF file or folder selected", text_color=self.theme["fg_tertiary"])
        self.count_label.grid_remove()
        self.extract_pages_var.set("")
        self.remove_extracted_var.set(False)
        self._toggle_extract_remove_mode()
        self.btn_error_report.configure(state="disabled")
        self._refresh_start_state()
        self._set_info("Select a PDF file or folder to begin.", "info")
        self._clear_log()
        self._refresh_dependency_panel()
        self.parent.operation_in_progress = False
        self.parent.operation_type = None
        self.parent.set_status("Ready", 1.0)
        self._log("Ready — select a PDF file or folder.", "info")

    # Helpers
    def _active_operation_key(self) -> str:
        return self.OPERATION_OPTIONS.get(self.operation_var.get(), "reduce_size")

    def _split_output_key(self) -> str:
        return self.SPLIT_OUTPUT_OPTIONS.get(self.split_output_var.get(), "pdfs")

    def _remove_mode_key(self) -> str:
        return self.REMOVE_MODE_OPTIONS.get(self.remove_mode_var.get(), "safe")

    def _refresh_start_state(self):
        if not self.btn_start:
            return
        state = "normal" if self.selection_mode else "disabled"
        operation = self._active_operation_key()
        if operation in {"split_pdf", "extract_pages"} and self.selection_mode != "file":
            state = "disabled"
            if self.selection_mode == "folder":
                self._set_info(
                    f"{self.operation_var.get()} works on one PDF file at a time.",
                    "warning",
                )
        if operation == "extract_pages" and self.selection_mode == "file" and not self.extract_pages_var.get().strip():
            state = "disabled"
        self.btn_start.configure(state=state)

    def _prepare_error_folder(self, base_folder: Path):
        error_root = create_error_folder(base_folder)
        if not error_root:
            return None
        error_folder = error_root / "pdf-conversion"
        error_folder.mkdir(parents=True, exist_ok=True)
        return error_folder

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
        self.log_display.configure(state="normal")
        self.log_display.insert("end", f"{prefixes.get(level, '  ·  ')}{message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _generate_error_report(self, results: dict):
        if not self.error_folder:
            return
        report_file = self.error_folder / "PDF_CONVERSION_ERROR_REPORT.txt"
        lines = [
            "DPA Image Toolkit — PDF Conversion Error Report",
            "=" * 60,
            "",
            f"Total Errors: {len(results.get('errors', []))}",
            "",
        ]
        for error in results.get("errors", []):
            lines.extend(
                [
                    f"File:  {error.get('file', 'unknown')}",
                    f"Error: {error.get('error', 'unknown error')}",
                    "",
                ]
            )
        lines.extend(
            [
                "=" * 60,
                "Review these files and rerun as needed.",
            ]
        )
        try:
            report_file.write_text("\n".join(lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as exc:
            self._log(f"Failed to save error report: {exc}", "error")
