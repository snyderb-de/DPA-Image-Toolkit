"""
Background worker threads for long-running operations.

Handles auto-crop and TIFF merge operations with progress callbacks.
"""

import threading
from pathlib import Path
from typing import Callable, Optional, List


class OperationWorker(threading.Thread):
    """Base worker thread for operations."""

    def __init__(self, name="Worker"):
        """
        Initialize worker.

        Args:
            name (str): Thread name
        """
        super().__init__(daemon=True, name=name)
        self.cancelled = False
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self.progress_callback = callback

    def set_status_callback(self, callback: Callable):
        """Set callback for status updates."""
        self.status_callback = callback

    def set_error_callback(self, callback: Callable):
        """Set callback for error notifications."""
        self.error_callback = callback

    def cancel(self):
        """Request cancellation."""
        self.cancelled = True

    def update_progress(self, current: int, total: int, filename: str = ""):
        """
        Update progress.

        Args:
            current (int): Current file number
            total (int): Total files
            filename (str): Current filename
        """
        if self.progress_callback:
            percentage = (current / total * 100) if total > 0 else 0
            self.progress_callback({
                "current": current,
                "total": total,
                "percentage": percentage,
                "filename": filename,
            })

    def update_status(self, message: str):
        """
        Update status message.

        Args:
            message (str): Status message
        """
        if self.status_callback:
            self.status_callback(message)

    def report_error(self, filename: str, error_message: str):
        """
        Report an error.

        Args:
            filename (str): File that had the error
            error_message (str): Error description
        """
        if self.error_callback:
            self.error_callback(filename, error_message)


class AutoCropWorker(OperationWorker):
    """Worker for auto-crop operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        error_folder: Path,
    ):
        """
        Initialize auto-crop worker.

        Args:
            input_folder (Path): Folder with images to crop
            output_folder (Path): Folder for cropped images
            error_folder (Path): Folder for failed images
        """
        super().__init__(name="AutoCropWorker")

        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.error_folder = Path(error_folder)

        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "errors": [],
        }

    def run(self):
        """Execute auto-crop operation."""
        from modules.auto_cropping.core import crop_image
        import shutil

        try:
            # Find all image files
            image_extensions = ('.tif', '.tiff', '.jpg', '.jpeg', '.png', '.bmp', '.gif')
            image_files = [
                f for f in self.input_folder.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            if not image_files:
                self.update_status("No images found")
                return

            # Sort for consistent processing
            image_files.sort()
            total = len(image_files)
            self.results["total"] = total

            for idx, image_file in enumerate(image_files, 1):
                if self.cancelled:
                    self.update_status("Operation cancelled")
                    break

                self.update_progress(idx, total, image_file.name)
                self.update_status(f"Cropping: {image_file.name}")

                # Crop image
                output_path, error_msg = crop_image(
                    image_file,
                    self.output_folder,
                    preserve_dpi=True,
                )

                if error_msg:
                    # Failed or skipped
                    self.results["errors"].append({
                        "file": image_file.name,
                        "error": error_msg,
                    })

                    # Move file to error folder if it's a real error (not just blank/white)
                    if "too small" not in error_msg and "blank" not in error_msg and "white" not in error_msg:
                        try:
                            error_folder = self.error_folder / "failed"
                            error_folder.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(image_file), str(error_folder / image_file.name))
                            self.results["failed"] += 1
                            self.report_error(image_file.name, error_msg)
                        except Exception as e:
                            self.report_error(image_file.name, f"Move failed: {str(e)}")
                    else:
                        self.results["skipped"] += 1
                else:
                    self.results["success"] += 1

            # Generate summary
            summary = (
                f"✅ Cropped: {self.results['success']} | "
                f"⚠️ Skipped: {self.results['skipped']} | "
                f"❌ Failed: {self.results['failed']}"
            )
            self.update_status(summary)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results


class TiffMergeWorker(OperationWorker):
    """Worker for TIFF merge operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        error_folder: Path,
        groups: dict,
    ):
        """
        Initialize TIFF merge worker.

        Args:
            input_folder (Path): Folder with TIFF files
            output_folder (Path): Folder for merged TIFFs
            error_folder (Path): Folder for failed files
            groups (dict): Groups detected by naming validation
        """
        super().__init__(name="TiffMergeWorker")

        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.error_folder = Path(error_folder)
        self.groups = groups

        self.results = {
            "success": 0,
            "failed": 0,
            "total": 0,
            "errors": [],
        }

    def run(self):
        """Execute TIFF merge operation."""
        from modules.tiff_combine.core import merge_tiff_group
        import shutil

        try:
            group_names = list(self.groups.keys())
            total_groups = len(group_names)

            if total_groups == 0:
                self.update_status("No groups to merge")
                return

            self.results["total"] = total_groups

            for idx, group_name in enumerate(group_names, 1):
                if self.cancelled:
                    self.update_status("Operation cancelled")
                    break

                self.update_progress(idx, total_groups, group_name)
                self.update_status(f"Merging: {group_name}")

                try:
                    # Merge the group
                    success, output_path, errors = merge_tiff_group(
                        group_name,
                        self.input_folder,
                        self.output_folder,
                        dpi_per_file=True,
                    )

                    if success:
                        self.results["success"] += 1
                    else:
                        self.results["failed"] += 1
                        for error_info in errors:
                            self.results["errors"].append(error_info)
                            self.report_error(
                                error_info.get("file", group_name),
                                error_info.get("error", "Unknown error"),
                            )

                except Exception as e:
                    self.results["failed"] += 1
                    error_msg = f"Merge failed: {str(e)}"
                    self.results["errors"].append({
                        "file": group_name,
                        "error": error_msg,
                    })
                    self.report_error(group_name, error_msg)

            # Generate summary
            summary = (
                f"✅ Merged: {self.results['success']} | "
                f"❌ Failed: {self.results['failed']}"
            )
            self.update_status(summary)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results
