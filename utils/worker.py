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


class TiffSplitWorker(OperationWorker):
    """Worker for TIFF split operations."""

    def __init__(
        self,
        input_files: List[Path],
        output_root: Optional[Path] = None,
        use_root_output: bool = False,
    ):
        super().__init__(name="TiffSplitWorker")
        self.input_files = [Path(file_path) for file_path in input_files]
        self.output_root = Path(output_root) if output_root else None
        self.use_root_output = use_root_output
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(self.input_files),
            "errors": [],
        }

    def run(self):
        """Execute TIFF split operation."""
        from modules.tiff_split.core import split_tiff_file

        try:
            total = len(self.input_files)
            if total == 0:
                self.update_status("No TIFF files selected")
                return

            for idx, file_path in enumerate(self.input_files, 1):
                if self.cancelled:
                    self.update_status("Operation cancelled")
                    break

                self.update_progress(idx, total, file_path.name)
                self.update_status(f"Splitting: {file_path.name}")

                if self.use_root_output and self.output_root:
                    output_folder = self.output_root / file_path.stem
                else:
                    output_folder = None

                success, output_paths, error_msg, stats = split_tiff_file(
                    file_path,
                    output_folder=output_folder,
                    skip_single_page=True,
                )

                if not success:
                    self.results["failed"] += 1
                    self.results["errors"].append({
                        "file": file_path.name,
                        "error": error_msg,
                    })
                    self.report_error(file_path.name, error_msg)
                    continue

                if stats.get("skipped"):
                    self.results["skipped"] += 1
                else:
                    self.results["success"] += 1

            summary = (
                f"✅ Split: {self.results['success']} | "
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


class AddBorderWorker(OperationWorker):
    """Worker for add-border operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
    ):
        super().__init__(name="AddBorderWorker")
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.results = {
            "success": 0,
            "failed": 0,
            "total": 0,
            "errors": [],
        }

    def run(self):
        """Execute add-border operation."""
        from modules.image_border.core import add_border_to_image

        try:
            image_extensions = ('.tif', '.tiff', '.jpg', '.jpeg', '.png', '.bmp', '.gif')
            image_files = [
                f for f in self.input_folder.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            if not image_files:
                self.update_status("No images found")
                return

            image_files.sort()
            total = len(image_files)
            self.results["total"] = total

            for idx, image_file in enumerate(image_files, 1):
                if self.cancelled:
                    self.update_status("Operation cancelled")
                    break

                self.update_progress(idx, total, image_file.name)
                self.update_status(f"Adding border: {image_file.name}")

                output_path, error_msg, _stats = add_border_to_image(
                    image_file,
                    self.output_folder,
                    preserve_dpi=True,
                )

                if error_msg:
                    self.results["failed"] += 1
                    self.results["errors"].append({
                        "file": image_file.name,
                        "error": error_msg,
                    })
                    self.report_error(image_file.name, error_msg)
                else:
                    self.results["success"] += 1

            summary = (
                f"✅ Bordered: {self.results['success']} | "
                f"❌ Failed: {self.results['failed']}"
            )
            self.update_status(summary)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results


class OcrPdfWorker(OperationWorker):
    """Worker for OCR-to-PDF operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        error_folder: Path,
        recurse: bool = False,
        language: str = "eng",
        skip_existing: bool = True,
        save_pdfa: bool = True,
        skip_messy: bool = True,
        tesseract_path: Optional[Path] = None,
    ):
        super().__init__(name="OcrPdfWorker")
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.error_folder = Path(error_folder)
        self.recurse = recurse
        self.language = language
        self.skip_existing = skip_existing
        self.save_pdfa = save_pdfa
        self.skip_messy = skip_messy
        self.tesseract_path = Path(tesseract_path) if tesseract_path else None
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "cancelled": False,
            "errors": [],
            "skip_reasons": [],
            "outputs": [],
        }

    def run(self):
        """Execute OCR-to-PDF operation."""
        from modules.ocr_pdf.core import (
            check_ocr_dependencies,
            find_ocr_input_files,
            ocr_image_to_pdf,
        )

        try:
            self.update_status("Checking OCR dependencies...")
            ok, error_msg, dependency_info = check_ocr_dependencies(
                language=self.language,
                tesseract_path=self.tesseract_path,
                require_pdfa=self.save_pdfa,
            )
            if not ok:
                self.update_status("OCR dependencies are missing")
                self.results["errors"].append({
                    "file": "dependency",
                    "error": error_msg,
                })
                self.report_error("dependency", error_msg)
                return

            resolved_tesseract = dependency_info.get("tesseract_path")

            self.update_status("Scanning folder for OCR input files...")
            image_files = find_ocr_input_files(
                self.input_folder,
                recurse=self.recurse,
            )

            if not image_files:
                self.update_status("No supported image files found")
                return

            total = len(image_files)
            self.results["total"] = total
            self.update_status(f"Found {total} image file(s) to OCR")

            for idx, image_file in enumerate(image_files, 1):
                if self.cancelled:
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    break

                display_name = image_file.name
                try:
                    display_name = str(image_file.relative_to(self.input_folder))
                except ValueError:
                    pass

                self.update_progress(idx, total, display_name)
                self.update_status(f"OCR: {display_name}")

                result = ocr_image_to_pdf(
                    image_path=image_file,
                    input_folder=self.input_folder,
                    output_folder=self.output_folder,
                    recurse=self.recurse,
                    language=self.language,
                    skip_existing=self.skip_existing,
                    save_pdfa=self.save_pdfa,
                    skip_messy=self.skip_messy,
                    tesseract_path=resolved_tesseract,
                    cancel_check=lambda: self.cancelled,
                )

                if result["status"] == "success":
                    self.results["success"] += 1
                    self.results["outputs"].append(str(result["output_path"]))
                elif result["status"] == "skipped":
                    self.results["skipped"] += 1
                    skip_reason = result.get("error") or "Skipped"
                    self.results["skip_reasons"].append({
                        "file": display_name,
                        "reason": skip_reason,
                    })
                    self.update_status(f"Skipped: {display_name} — {skip_reason}")
                elif result["status"] == "cancelled":
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    break
                else:
                    self.results["failed"] += 1
                    error_msg = result.get("error") or "OCR failed"
                    self.results["errors"].append({
                        "file": display_name,
                        "error": error_msg,
                    })
                    self.report_error(display_name, error_msg)

            summary = (
                f"✅ OCR'd: {self.results['success']} | "
                f"⚠️ Skipped: {self.results['skipped']} | "
                f"❌ Failed: {self.results['failed']}"
            )
            if self.results["cancelled"]:
                summary = (
                    f"Cancelled — OCR'd: {self.results['success']} | "
                    f"Skipped: {self.results['skipped']} | "
                    f"Failed: {self.results['failed']}"
                )
            self.update_status(summary)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results
