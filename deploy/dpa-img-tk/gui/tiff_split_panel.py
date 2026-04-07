"""
TIFF split panel for DPA Image Toolkit.
"""

import customtkinter as ctk
from pathlib import Path

from utils.file_handler import pick_folder, pick_files
from utils.tool_dependencies import (
    check_tool_dependencies,
    get_tool_dependency_panel_content,
    get_tool_dependency_statuses,
    show_dependency_warning,
)
from utils.worker import TiffSplitWorker
from .dependency_sidebar import build_dependency_sidebar, refresh_dependency_sidebar
from .styles import get_font, BUTTON, RADIUS


class TiffSplitPanel:
    """TIFF split panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme

        self.selection_mode = None
        self.selected_folder: Path = None
        self.selected_files = []
        self.worker = None

        self.selection_label = None
        self.count_label = None
        self.info_card = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None
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
            text="Split Multi-Page TIFFs",
            font=get_font("title"),
            text_color=t["fg_primary"],
        ).grid(row=0, column=0, sticky="sw")

        ctk.CTkLabel(
            hdr,
            text="Extract each page of a multi-page TIFF into individual single-page TIFF files",
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
        picker_card.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            picker_card,
            text="  🗂  Select TIFF Files",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["bg_glass"],
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border_subtle"],
            command=self._on_select_files,
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
            text="No files or folder selected",
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
        self.info_card.grid(row=2, column=0, sticky="ew", padx=36, pady=(12, 0))

        self.info_lbl = ctk.CTkLabel(
            self.info_card,
            text="Choose TIFF files or a folder. Folder mode skips single-page TIFFs automatically.",
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=16, pady=12, anchor="w")

        dependency_content = get_tool_dependency_panel_content("tiff_split")
        side_panel, self.dependency_rows = build_dependency_sidebar(
            panel,
            t,
            heading=dependency_content["heading"],
            statuses=get_tool_dependency_statuses("tiff_split"),
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
            "Split TIFFs accepts either selected TIFF files or a folder containing TIFFs.",
            "Only multi-page TIFFs are extracted into single-page files; single-page TIFFs are skipped.",
            "Folder mode writes output into extracted-pages/ so the source folder stays organized.",
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
        action_bar.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            action_bar,
            text="  ▶  Start Split",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["accent_text"],
            text_color_disabled=t["button_disabled_text"],
            command=self._on_start_split,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=1, sticky="e")

        self._refresh_dependency_panel()
        self._log("Ready — choose TIFF files or a TIFF folder.", "info")

    def _on_select_files(self):
        files = pick_files(
            "Select TIFF files to split",
            filetypes=[("TIFF files", "*.tif *.tiff *.TIF *.TIFF")],
        )
        if not files:
            self._log("File selection cancelled.", "info")
            return

        self.selection_mode = "files"
        self.selected_folder = None
        self.selected_files = [Path(file_path) for file_path in files]
        self.selection_label.configure(
            text=f"{len(self.selected_files)} file(s) selected",
            text_color=self.theme["fg_primary"],
        )
        self.count_label.configure(text=f"  {len(self.selected_files)} TIFFs  ")
        self.count_label.grid(row=0, column=3, padx=(0, 14))
        self.btn_start.configure(state="normal")
        self._set_info(
            "✓  Selected TIFF files. Each file will be extracted into a sibling *_pages folder.",
            "success",
        )
        self._log(f"Selected {len(self.selected_files)} TIFF file(s).", "success")

    def _on_select_folder(self):
        folder = pick_folder("Select folder with TIFF files to split")
        if not folder:
            self._log("Folder selection cancelled.", "info")
            return

        files = sorted(
            [
                file_path for file_path in Path(folder).iterdir()
                if file_path.is_file() and file_path.suffix.lower() in {".tif", ".tiff"}
            ],
            key=lambda file_path: file_path.name.lower(),
        )

        if not files:
            message = f"No .tif or .tiff files found in {folder}"
            self._log(message, "error")
            self._set_info(f"✕  {message}", "error")
            return

        self.selection_mode = "folder"
        self.selected_folder = folder
        self.selected_files = list(files)
        self.selection_label.configure(text=str(folder), text_color=self.theme["fg_primary"])
        self.count_label.configure(text=f"  {len(self.selected_files)} TIFFs  ")
        self.count_label.grid(row=0, column=3, padx=(0, 14))
        self.btn_start.configure(state="normal")
        self._set_info(
            f"✓  Found {len(self.selected_files)} TIFF file(s). Multi-page TIFFs will be extracted directly into extracted-pages/.",
            "success",
        )
        self._log(f"Folder: {folder}", "info")
        self._log(f"Found {len(self.selected_files)} TIFF file(s).", "success")

    def _on_start_split(self):
        if not self.selected_files:
            self._log("No TIFF files selected.", "error")
            return

        ok, error_msg, _details = check_tool_dependencies("tiff_split")
        self._refresh_dependency_panel()
        if not ok:
            show_dependency_warning(self.parent, "Split Multi-Page TIFFs", error_msg)
            self._set_info(
                "⚠  TIFF split dependencies are missing. Contact support for installation.",
                "warning",
            )
            self._log(error_msg, "warning")
            self._log("Contact support for dependency installation on this machine.", "warning")
            self.parent.set_status("TIFF split dependencies are missing", 1.0)
            return

        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "split"

        output_root = None
        use_root_output = False
        if self.selection_mode == "folder":
            output_root = self.selected_folder / "extracted-pages"
            output_root.mkdir(parents=True, exist_ok=True)
            use_root_output = True

        self.parent.set_status("Starting TIFF split…", 0.0)
        self._log("Starting TIFF split operation…", "info")

        self.worker = TiffSplitWorker(
            self.selected_files,
            output_root=output_root,
            use_root_output=use_root_output,
        )
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
        self.parent.set_status(f"Splitting {current} / {total} — {filename}", pct)
        self._log(f"Processing: {filename}", "info")

    def _on_status(self, message):
        self.parent.set_status(message)
        self._log(message, "success" if "✅" in message else "info")

    def _on_error(self, filename, error_message):
        self._log(f"{filename} — {error_message}", "error")

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.05)
            self.parent.after(100, self._poll_worker)
        else:
            results = self.worker.get_results() if self.worker else {}
            self._set_info(
                f"✓  Complete — {results.get('success', 0)} split  ·  "
                f"{results.get('skipped', 0)} skipped  ·  {results.get('failed', 0)} failed",
                "warning" if results.get("failed", 0) else "success",
            )
            self.btn_start.configure(state="normal", text="  ▶  Start Split")
            self.parent.operation_in_progress = False
            self.parent.set_status("Ready", 1.0)

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _refresh_dependency_panel(self):
        refresh_dependency_sidebar(
            self.dependency_rows,
            get_tool_dependency_statuses("tiff_split"),
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
