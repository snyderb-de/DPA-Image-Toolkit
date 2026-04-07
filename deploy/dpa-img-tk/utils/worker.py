"""
Background worker threads for long-running operations.

Handles auto-crop and TIFF merge operations with progress callbacks.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def _get_worker_count(self, total_groups: int) -> int:
        """Choose a modest worker count for parallel group merges."""
        if total_groups <= 1:
            return 1

        cpu_count = os.cpu_count() or 2
        return max(1, min(total_groups, cpu_count, 4))

    def _merge_single_group(self, group_name: str) -> dict:
        """Merge one TIFF group and return a structured result."""
        from modules.tiff_combine.core import merge_tiff_group

        try:
            success, output_path, errors = merge_tiff_group(
                group_name,
                self.input_folder,
                self.output_folder,
                dpi_per_file=True,
            )
            return {
                "group": group_name,
                "success": success,
                "output_path": output_path,
                "errors": errors or [],
            }
        except Exception as e:
            return {
                "group": group_name,
                "success": False,
                "output_path": None,
                "errors": [{
                    "file": group_name,
                    "error": f"Merge failed: {str(e)}",
                }],
            }

    def run(self):
        """Execute TIFF merge operation."""
        try:
            group_names = sorted(self.groups.keys())
            total_groups = len(group_names)

            if total_groups == 0:
                self.update_status("No groups to merge")
                return

            self.results["total"] = total_groups
            worker_count = self._get_worker_count(total_groups)
            completed = 0

            if worker_count > 1:
                self.update_status(
                    f"Running {total_groups} groups with {worker_count} parallel workers"
                )
            else:
                self.update_status(f"Running {total_groups} group(s) sequentially")

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(self._merge_single_group, group_name): group_name
                    for group_name in group_names
                }

                for future in as_completed(futures):
                    if self.cancelled:
                        self.update_status("Operation cancelled")
                        break

                    result = future.result()
                    group_name = result["group"]
                    completed += 1

                    self.update_progress(completed, total_groups, group_name)

                    if result["success"]:
                        self.results["success"] += 1
                        self.update_status(f"Merged: {group_name}")
                    else:
                        self.results["failed"] += 1
                        self.update_status(f"Failed: {group_name}")
                        for error_info in result["errors"]:
                            self.results["errors"].append(error_info)
                            self.report_error(
                                error_info.get("file", group_name),
                                error_info.get("error", "Unknown error"),
                            )

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
                    output_folder = self.output_root
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
        language: str = "eng",
        skip_existing: bool = True,
        save_pdfa: bool = True,
        skip_messy: bool = True,
        metadata: Optional[dict] = None,
        tesseract_path: Optional[Path] = None,
    ):
        super().__init__(name="OcrPdfWorker")
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.error_folder = Path(error_folder)
        self.language = language
        self.skip_existing = skip_existing
        self.save_pdfa = save_pdfa
        self.skip_messy = skip_messy
        self.metadata = metadata or {}
        self.tesseract_path = Path(tesseract_path) if tesseract_path else None
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "cancelled": False,
            "errors": [],
            "skip_reasons": [],
            "warnings": [],
            "outputs": [],
        }

    def run(self):
        """Execute OCR-to-PDF operation."""
        from modules.ocr_pdf.core import (
            check_ocr_dependencies,
            group_ocr_input_files,
            ocr_document_to_pdf,
            summarize_ocr_documents,
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
            if error_msg:
                self.results["warnings"].append(error_msg)
                self.update_status(error_msg)

            self.update_status("Scanning folder for OCR page images...")
            documents = group_ocr_input_files(self.input_folder)

            if not documents:
                self.update_status("No supported image files found")
                return

            summary = summarize_ocr_documents(documents)
            self.results["total"] = summary["document_count"]
            self.update_status(
                "Found "
                f"{summary['page_count']} page image(s) across "
                f"{summary['document_count']} output PDF(s)"
            )

            if self.cancelled:
                self.results["cancelled"] = True
                self.update_status("Operation cancelled")
                return

            pdfa_warning_added = False
            total_documents = len(documents)
            for index, document in enumerate(documents, start=1):
                if self.cancelled:
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    break

                document_name = document["name"]
                output_pdf_path = self.output_folder / f"{document_name}.pdf"
                self.update_progress(index, total_documents, output_pdf_path.name)
                self.update_status(
                    f"OCR {index}/{total_documents}: {output_pdf_path.name} "
                    f"from {document['page_count']} page(s)"
                )

                result = ocr_document_to_pdf(
                    input_files=document["files"],
                    output_pdf_path=output_pdf_path,
                    document_name=document_name,
                    language=self.language,
                    skip_existing=self.skip_existing,
                    save_pdfa=self.save_pdfa,
                    skip_messy=self.skip_messy,
                    metadata=self.metadata,
                )

                if result["status"] == "success":
                    self.results["success"] += 1
                    self.results["outputs"].append(str(result["output_path"]))
                    if self.save_pdfa and not result.get("used_pdfa") and not pdfa_warning_added:
                        warning = "PDF/A was unavailable on this machine — created standard searchable PDFs instead."
                        self.results["warnings"].append(warning)
                        self.update_status(warning)
                        pdfa_warning_added = True
                elif result["status"] == "skipped":
                    self.results["skipped"] += 1
                    skip_reason = result.get("error") or "Skipped"
                    self.results["skip_reasons"].append({
                        "file": output_pdf_path.name,
                        "reason": skip_reason,
                    })
                    self.update_status(f"Skipped: {output_pdf_path.name} — {skip_reason}")
                    details = result.get("details") or {}
                    for page in details.get("flagged_pages", []):
                        reason_text = ", ".join(page.get("reasons", [])) or "flagged by precheck"
                        self.report_error(page.get("file", "page"), f"OCR quality flag: {reason_text}")
                else:
                    self.results["failed"] += 1
                    doc_error = result.get("error") or "OCR failed"
                    self.results["errors"].append({
                        "file": output_pdf_path.name,
                        "error": doc_error,
                    })
                    self.report_error(output_pdf_path.name, doc_error)

            summary = (
                f"✅ OCR'd: {self.results['success']} PDF(s) | "
                f"⚠️ Skipped: {self.results['skipped']} | "
                f"❌ Failed: {self.results['failed']}"
            )
            if self.results["cancelled"]:
                summary = (
                    f"Cancelled — OCR'd: {self.results['success']} PDF(s) | "
                    f"Skipped: {self.results['skipped']} | Failed: {self.results['failed']}"
                )
            self.update_status(summary)

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results
