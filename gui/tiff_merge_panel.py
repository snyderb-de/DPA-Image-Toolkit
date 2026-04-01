"""
TIFF merge panel for DPA Image Toolkit.

Folder selection, naming validation with spot-check, progress tracking, live logging.
"""

import customtkinter as ctk
from pathlib import Path
from utils.file_handler import pick_folder, validate_tif_files, create_error_folder
from modules.tiff_combine.naming import validate_naming_convention
from .styles import get_theme, get_font


class TiffMergePanel:
    """TIFF merge panel manager."""

    def __init__(self, parent_window):
        """
        Initialize TIFF merge panel.

        Args:
            parent_window: Main window reference
        """
        self.parent = parent_window
        self.theme = parent_window.current_theme

    def _dispatch_to_ui(self, callback, *args):
        """Run a callback on the Tk main thread."""
        self.parent.after(0, lambda: callback(*args))

    def build(self, container):
        """
        Build TIFF merge panel UI.

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
            text="🔗 Merge TIFF Files",
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
            text="📁 Select TIFF Folder",
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
            text="Select a folder containing TIFF files named as: groupname_###.tif",
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
            text="▶ Start Merge",
            font=get_font("normal"),
            height=32,
            fg_color=self.theme["accent"],
            text_color="white",
            command=self._on_start_merge,
            state="disabled",
        )
        self.btn_start.grid(row=0, column=2, padx=12, pady=0, sticky="e")

        self.selected_folder = None
        self.error_folder = None
        self.groups = None

        self._log("Ready to merge TIFF files", "info")

    def _on_select_folder(self):
        """Handle folder selection."""
        folder = pick_folder("Select folder with TIFF files to merge")

        if not folder:
            self._log("Folder selection cancelled", "info")
            return

        # Validate folder contains TIFFs
        is_valid, files, error = validate_tif_files(folder)

        if not is_valid:
            self._log(f"No TIFF files found: {error}", "error")
            return

        # Validate naming convention
        groups, naming_valid, issues = validate_naming_convention(folder)

        if not groups:
            self._log("No valid TIFF groups found", "error")
            for issue in issues:
                self._log(f"  - {issue}", "warning")
            return

        if not naming_valid:
            self._log(f"⚠️ Naming validation failed - {len(issues)} file(s)", "warning")
            for issue in issues:
                self._log(f"  - {issue}", "warning")

        self.selected_folder = folder
        self.error_folder = create_error_folder(folder)
        self.groups = groups

        # Update UI
        self.folder_label.configure(text=str(folder.name))

        # Count single files (not matching pattern)
        total_valid_files = sum(len(files) for files in groups.values())
        single_files = len(files) - total_valid_files

        info_text = f"✅ Found {len(groups)} group(s) with {total_valid_files} TIFF file(s)"
        if single_files > 0:
            info_text += f", {single_files} single file(s) (will be skipped)"
        info_text += ". Click 'Start Merge' to begin."

        self.info_label.configure(text=info_text)
        self.btn_start.configure(state="normal")

        self._log(f"Selected folder: {folder}", "success")
        self._log(f"Found {len(groups)} group(s): ", "info")

        for group_name, group_files in groups.items():
            self._log(f"  • {group_name}: {len(group_files)} file(s)", "info")

        if single_files > 0:
            self._log(f"Skipping: {single_files} file(s) without matching pattern", "info")

        self._log("Ready to validate naming convention", "info")
        self._show_validation_dialog()

    def _show_validation_dialog(self):
        """Show validation dialog with spot-check groups."""
        if not self.groups or len(self.groups) == 0:
            return

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Confirm File Groups")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        # Title
        title = ctk.CTkLabel(
            dialog,
            text="🔍 Verify File Groups",
            font=("Arial", 16, "bold"),
            text_color=self.theme["fg_primary"],
        )
        title.pack(pady=(20, 10), padx=20)

        # Info
        info = ctk.CTkLabel(
            dialog,
            text="Showing sample groups (first, middle, last)...",
            font=get_font("small"),
            text_color=self.theme["fg_tertiary"],
        )
        info.pack(pady=(0, 20), padx=20)

        # Scroll frame for groups
        scroll_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=self.theme["bg_secondary"],
            corner_radius=8,
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Get sample groups (first, middle, last)
        group_names = list(self.groups.keys())
        sample_indices = [0]  # First

        if len(group_names) > 2:
            sample_indices.append(len(group_names) // 2)  # Middle

        if len(group_names) > 1:
            sample_indices.append(len(group_names) - 1)  # Last

        sample_indices = sorted(set(sample_indices))

        for idx in sample_indices:
            group_name = group_names[idx]
            files = self.groups[group_name]

            # Group label
            group_label = ctk.CTkLabel(
                scroll_frame,
                text=f"📁 {group_name}",
                font=get_font("normal"),
                text_color=self.theme["fg_primary"],
            )
            group_label.pack(anchor="w", padx=12, pady=(12, 4))

            # Files list (with ellipsis if many)
            if len(files) <= 3:
                files_text = "\n".join(files)
            else:
                files_text = f"{files[0]}\n...\n{files[-1]}"

            files_label = ctk.CTkLabel(
                scroll_frame,
                text=files_text,
                font=get_font("monospace"),
                text_color=self.theme["fg_secondary"],
                justify="left",
            )
            files_label.pack(anchor="w", padx=24, pady=(0, 8))

            # Divider
            if idx != sample_indices[-1]:
                divider = ctk.CTkFrame(
                    scroll_frame,
                    fg_color=self.theme["border"],
                    height=1,
                )
                divider.pack(fill="x", padx=12, pady=12)

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20, padx=20, fill="x")
        button_frame.grid_columnconfigure(1, weight=1)

        btn_cancel = ctk.CTkButton(
            button_frame,
            text="Cancel",
            font=get_font("normal"),
            height=32,
            fg_color=self.theme["bg_tertiary"],
            text_color=self.theme["fg_primary"],
            command=dialog.destroy,
        )
        btn_cancel.grid(row=0, column=0, padx=5)

        btn_confirm = ctk.CTkButton(
            button_frame,
            text="✅ Confirm & Proceed",
            font=get_font("normal"),
            height=32,
            fg_color=self.theme["accent"],
            text_color="white",
            command=lambda: (dialog.destroy(), self._log("Naming confirmed by user", "success")),
        )
        btn_confirm.grid(row=0, column=2, padx=5, sticky="e")

    def _on_start_merge(self):
        """Handle start merge button."""
        if not self.selected_folder or not self.groups:
            self._log("No folder selected", "error")
            return

        # Disable button and set operation state
        self.btn_start.configure(state="disabled")
        self.parent.operation_in_progress = True
        self.parent.operation_type = "merge"

        self._log("Starting TIFF merge operation...", "info")

        # Create output folder
        output_folder = self.selected_folder / "merged"
        output_folder.mkdir(parents=True, exist_ok=True)

        # Initialize worker with threading
        from utils.worker import TiffMergeWorker

        self.worker = TiffMergeWorker(
            self.selected_folder,
            output_folder,
            self.error_folder,
            self.groups,
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

        # Start worker
        self.worker.start()
        self._log(f"Merging {len(self.groups)} group(s)...", "success")

    def _on_progress(self, progress_dict):
        """Handle progress updates from worker."""
        current = progress_dict.get("current", 0)
        total = progress_dict.get("total", 1)
        percentage = progress_dict.get("percentage", 0)
        filename = progress_dict.get("filename", "")

        self.parent.set_status(f"Merging TIFFs: {current}/{total}", percentage)

        if filename:
            self._log(f"Processing group: {filename}", "info")

    def _on_status(self, message: str):
        """Handle status message from worker."""
        self._log(message, "info")

        # Check if operation is complete
        if "✅" in message or "❌" in message or "cancelled" in message.lower():
            self.btn_start.configure(state="normal")
            self.parent.operation_in_progress = False

            # Show error report if there were failures
            results = getattr(self.worker, "get_results", lambda: {})()
            if results.get("failed", 0) > 0:
                self.btn_error_report.configure(state="normal")
                self._log("⚠️ Some groups failed to merge. Click 'View Error Report' for details.", "warning")

    def _on_error(self, filename: str, error_message: str):
        """Handle error from worker."""
        self._log(f"❌ {filename}: {error_message}", "error")

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
