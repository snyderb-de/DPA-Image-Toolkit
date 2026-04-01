"""
Auto-crop panel for DPA Image Toolkit.

Folder selection, progress tracking, live logging, background processing.
"""

import customtkinter as ctk
from pathlib import Path
from ..utils.file_handler import pick_folder, validate_image_files, create_error_folder
from ..utils.worker import AutoCropWorker
from .styles import get_theme, get_font


class AutoCropPanel:
    """Auto-crop panel manager."""

    def __init__(self, parent_window):
        """
        Initialize auto-crop panel.

        Args:
            parent_window: Main window reference
        """
        self.parent = parent_window
        self.theme = parent_window.current_theme
        self.worker: AutoCropWorker = None
        self.selected_folder = None
        self.output_folder = None
        self.error_folder = None

    def _dispatch_to_ui(self, callback, *args):
        """Run a callback on the Tk main thread."""
        self.parent.after(0, lambda: callback(*args))

    def build(self, container):
        """
        Build auto-crop panel UI.

        Args:
            container: Parent CTkFrame to build in
        """
        panel = ctk.CTkFrame(container, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        panel.grid_rowconfigure(3, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            panel,
            text="📷 Auto Crop Images",
            font=("Arial", 20, "bold"),
            text_color=self.theme["fg_primary"],
        )
        header.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Controls frame
        controls = ctk.CTkFrame(
            panel,
            fg_color=self.theme["bg_secondary"],
            corner_radius=8,
        )
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        controls.grid_columnconfigure(1, weight=1)

        # Folder button
        btn_folder = ctk.CTkButton(
            controls,
            text="📁 Select Image Folder",
            font=get_font("normal"),
            height=40,
            fg_color=self.theme["accent"],
            text_color="white",
            command=self._on_select_folder,
        )
        btn_folder.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        # Selected folder label
        self.folder_label = ctk.CTkLabel(
            controls,
            text="No folder selected",
            font=get_font("small"),
            text_color=self.theme["fg_tertiary"],
            anchor="e",
        )
        self.folder_label.grid(row=0, column=1, padx=12, pady=12, sticky="e")

        # Info frame
        info_frame = ctk.CTkFrame(
            panel,
            fg_color=self.theme["bg_secondary"],
            corner_radius=8,
        )
        info_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))

        self.info_label = ctk.CTkLabel(
            info_frame,
            text="Select a folder containing images to begin auto-cropping.",
            font=get_font("small"),
            text_color=self.theme["fg_secondary"],
            wraplength=700,
        )
        self.info_label.pack(padx=12, pady=8, anchor="w")

        # Log display
        log_frame = ctk.CTkFrame(
            panel,
            fg_color=self.theme["bg_secondary"],
            corner_radius=8,
        )
        log_frame.grid(row=3, column=0, sticky="nsew")

        self.log_display = ctk.CTkTextbox(
            log_frame,
            fg_color=self.theme["bg_primary"],
            text_color=self.theme["fg_primary"],
            border_width=0,
            corner_radius=8,
            font=get_font("monospace"),
        )
        self.log_display.pack(fill="both", expand=True, padx=12, pady=12)
        self.log_display.configure(state="disabled")

        # Button frame at bottom
        button_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        button_frame.grid(row=4, column=0, sticky="ew", pady=(20, 0))
        button_frame.grid_columnconfigure(1, weight=1)

        # Error report button (disabled by default)
        self.btn_error_report = ctk.CTkButton(
            button_frame,
            text="📋 View Error Report",
            font=get_font("small"),
            height=32,
            fg_color=self.theme["error"],
            text_color="white",
            command=self._on_view_error_report,
            state="disabled",
        )
        self.btn_error_report.grid(row=0, column=0, padx=12, pady=0, sticky="w")

        # Start button
        self.btn_start = ctk.CTkButton(
            button_frame,
            text="▶ Start Auto Crop",
            font=get_font("normal"),
            height=32,
            fg_color=self.theme["accent"],
            text_color="white",
            command=self._on_start_crop,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=2, padx=12, pady=0, sticky="e")

        self.btn_cancel = None  # Will be created during operation
        self.has_errors = False

        self._log("Ready to auto-crop images", "info")

    def _on_select_folder(self):
        """Handle folder selection."""
        folder = pick_folder("Select folder with images to auto-crop")

        if not folder:
            self._log("Folder selection cancelled", "info")
            return

        # Validate folder contains images
        is_valid, files, error = validate_image_files(folder)

        if not is_valid:
            self._log(f"No images found: {error}", "error")
            return

        self.selected_folder = folder
        self.error_folder = create_error_folder(folder)

        # Update UI
        self.folder_label.configure(text=str(folder.name))
        self.info_label.configure(
            text=f"✅ Found {len(files)} image(s). Click 'Start Auto Crop' to begin.",
        )
        self.btn_start.configure(state="normal")

        self._log(f"Selected folder: {folder}", "success")
        self._log(f"Found {len(files)} image file(s)", "info")

    def _on_start_crop(self):
        """Handle start crop button."""
        if not self.selected_folder:
            self._log("No folder selected", "error")
            return

        # Create output folders
        self.output_folder = create_error_folder(self.selected_folder).parent / "cropped"
        self.output_folder.mkdir(parents=True, exist_ok=True)

        error_folder = create_error_folder(self.selected_folder)

        # Disable button and set operation state
        self.btn_start.configure(state="disabled")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "crop"
        self.has_errors = False

        self._log("Starting auto-crop operation...", "info")

        # Create and start worker
        self.worker = AutoCropWorker(
            input_folder=self.selected_folder,
            output_folder=self.output_folder,
            error_folder=error_folder,
        )

        # Set up callbacks
        self.worker.set_progress_callback(
            lambda progress: self._dispatch_to_ui(self._on_progress, progress)
        )
        self.worker.set_status_callback(
            lambda message: self._dispatch_to_ui(self._on_status, message)
        )
        self.worker.set_error_callback(
            lambda filename, error_message: self._dispatch_to_ui(
                self._on_error,
                filename,
                error_message,
            )
        )

        # Create cancel button
        self._create_cancel_button()

        # Start worker
        self.worker.start()

        # Wait for completion
        self._wait_for_worker()

    def _on_progress(self, progress: dict):
        """Handle progress update."""
        current = progress["current"]
        total = progress["total"]
        percentage = progress["percentage"] / 100.0
        filename = progress["filename"]

        # Update main window progress
        status = f"Cropping: {current} / {total}"
        self.parent.set_status(status, percentage)

        # Log file being processed
        self._log(f"Processing: {filename}", "info")

    def _on_status(self, message: str):
        """Handle status update."""
        self.parent.set_status(message)
        self._log(message, "success")

    def _on_error(self, filename: str, error_message: str):
        """Handle error notification."""
        self.has_errors = True
        self._log(f"Error: {filename} — {error_message}", "error")

        # Enable error report button
        if self.btn_error_report:
            self.btn_error_report.configure(state="normal")

    def _create_cancel_button(self):
        """Create cancel button during operation."""
        # This would be added to the button frame during operation
        # For now, cancellation happens when worker.cancel() is called
        pass

    def _on_cancel_crop(self):
        """Handle cancel button."""
        if self.worker:
            self._log("Cancelling operation...", "warning")
            self.worker.cancel()
            self.btn_start.configure(state="normal")
            self.parent.operation_in_progress = False

    def _wait_for_worker(self):
        """Wait for worker to complete and finalize."""
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=0.1)
            self.parent.after(100, self._wait_for_worker)
        else:
            # Worker complete
            if self.worker:
                results = self.worker.get_results()
                self._log(
                    f"Operation complete: {results['success']} cropped, "
                    f"{results['skipped']} skipped, {results['failed']} failed",
                    "success" if not self.has_errors else "warning",
                )

                # Generate error report if needed
                if results["errors"]:
                    self._generate_error_report(results)

            # Re-enable start button
            self.btn_start.configure(state="normal")
            self.parent.operation_in_progress = False

    def _generate_error_report(self, results: dict):
        """Generate error report file."""
        report_file = self.error_folder / "CROP_ERROR_REPORT.txt"
        report_lines = [
            "DPA Image Toolkit - Auto Crop Error Report",
            "=" * 60,
            "",
            f"Total Errors: {len(results['errors'])}",
            "",
        ]

        for error_info in results["errors"]:
            report_lines.append(f"File: {error_info['file']}")
            report_lines.append(f"Error: {error_info['error']}")
            report_lines.append("")

        report_lines.extend([
            "=" * 60,
            "These files have been moved to the errored-files/ folder.",
            "Check file format and try again.",
        ])

        try:
            report_file.write_text("\n".join(report_lines))
            self._log(f"Error report saved: {report_file.name}", "info")
        except Exception as e:
            self._log(f"Failed to save error report: {e}", "error")

    def _on_view_error_report(self):
        """Handle view error report button."""
        if not self.error_folder or not self.error_folder.exists():
            self._log("No error folder found", "warning")
            return

        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{self.error_folder}"')
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", str(self.error_folder)])
            else:  # Linux
                subprocess.Popen(["xdg-open", str(self.error_folder)])

            self._log(f"Opened error folder: {self.error_folder}", "info")
        except Exception as e:
            self._log(f"Failed to open error folder: {e}", "error")

    def _log(self, message, level="info"):
        """Add message to log display."""
        emojis = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        emoji = emojis.get(level, "📝")
        formatted = f"{emoji} {message}\n"

        self.log_display.configure(state="normal")
        self.log_display.insert("end", formatted)
        self.log_display.see("end")
        self.log_display.configure(state="disabled")
