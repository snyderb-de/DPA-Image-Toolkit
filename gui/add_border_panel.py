"""
Add border panel for DPA Image Toolkit.
"""

import customtkinter as ctk
from pathlib import Path

from utils.file_handler import pick_folder, validate_image_files
from utils.worker import AddBorderWorker
from modules.auto_cropping.core import (
    DEFAULT_PADDING_PERCENT,
    DEFAULT_PADDING_MIN,
    DEFAULT_PADDING_MAX,
)
from .styles import get_font, BUTTON, RADIUS


class AddBorderPanel:
    """Add border panel controller."""

    def __init__(self, parent_window):
        self.parent = parent_window
        self.theme = parent_window.current_theme
        self.selected_folder: Path = None
        self.output_folder: Path = None
        self.worker = None

        self.folder_label = None
        self.file_count_lbl = None
        self.info_lbl = None
        self.log_display = None
        self.btn_start = None

    def build(self, container):
        t = self.theme

        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_rowconfigure(3, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr,
            text="▣",
            font=("Segoe UI", 20),
            fg_color=t["accent_dim"],
            text_color=t["accent"],
            width=40, height=40,
            corner_radius=RADIUS["md"],
        ).grid(row=0, column=0, rowspan=2)

        ctk.CTkLabel(
            hdr,
            text="Add Border",
            font=get_font("title"),
            text_color=t["fg_primary"],
        ).grid(row=0, column=1, sticky="w", padx=(14, 0))

        ctk.CTkLabel(
            hdr,
            text="Add a white border using the same padding logic as auto-crop",
            font=get_font("small"),
            text_color=t["fg_secondary"],
        ).grid(row=1, column=1, sticky="w", padx=(14, 0))

        picker_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border"],
        )
        picker_card.grid(row=1, column=0, sticky="ew", padx=28, pady=(20, 0))
        picker_card.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            picker_card,
            text="  📁  Select Image Folder",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color="transparent",
            hover_color=t["bg_tertiary"],
            text_color=t["fg_primary"],
            border_width=1,
            border_color=t["border"],
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

        info_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=t["border_subtle"],
        )
        info_card.grid(row=2, column=0, sticky="ew", padx=28, pady=(10, 0))

        self.info_lbl = ctk.CTkLabel(
            info_card,
            text=(
                f"Padding uses auto-crop settings: {int(DEFAULT_PADDING_PERCENT * 100)}% "
                f"of image size, clamped to {DEFAULT_PADDING_MIN}-{DEFAULT_PADDING_MAX}px."
            ),
            font=get_font("small"),
            text_color=t["fg_secondary"],
            anchor="w",
        )
        self.info_lbl.pack(padx=14, pady=10, anchor="w")

        log_card = ctk.CTkFrame(
            panel,
            fg_color=t["bg_secondary"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=t["border"],
        )
        log_card.grid(row=3, column=0, sticky="nsew", padx=28, pady=(10, 0))
        log_card.grid_rowconfigure(2, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        log_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_hdr,
            text="Activity Log",
            font=get_font("subheading"),
            text_color=t["fg_secondary"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_hdr,
            text="Clear",
            font=get_font("micro"),
            height=22,
            corner_radius=RADIUS["sm"],
            fg_color="transparent",
            hover_color=t["bg_tertiary"],
            text_color=t["fg_tertiary"],
            border_width=1,
            border_color=t["border"],
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
        action_bar.grid(row=4, column=0, sticky="ew", padx=28, pady=(10, 20))
        action_bar.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            action_bar,
            text="  ▶  Add Border",
            font=get_font("normal"),
            height=BUTTON["height_md"],
            corner_radius=RADIUS["md"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color="white",
            command=self._on_start,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=1, sticky="e")

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
        self.folder_label.configure(text=str(folder), text_color=self.theme["fg_primary"])
        self.file_count_lbl.configure(text=f"  {len(files)} images  ")
        self.file_count_lbl.grid(row=0, column=2, padx=(0, 14))
        self.btn_start.configure(state="normal")
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

        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.btn_start.configure(state="disabled", text="  ⏳  Running…")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "border"

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
        self._log(f"{filename} — {error_message}", "error")

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.05)
            self.parent.after(100, self._poll_worker)
        else:
            results = self.worker.get_results() if self.worker else {}
            self._set_info(
                f"✓  Complete — {results.get('success', 0)} bordered  ·  "
                f"{results.get('failed', 0)} failed",
                "warning" if results.get("failed", 0) else "success",
            )
            self.btn_start.configure(state="normal", text="  ▶  Add Border")
            self.parent.operation_in_progress = False
            self.parent.set_status("Ready", 1.0)

    def _dispatch(self, callback, *args):
        self.parent.after(0, lambda: callback(*args))

    def _set_info(self, text, level="info"):
        t = self.theme
        color_map = {
            "info": t["fg_secondary"],
            "success": t["success"],
            "warning": t["warning"],
            "error": t["error"],
        }
        self.info_lbl.configure(text=text, text_color=color_map.get(level, t["fg_secondary"]))

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
