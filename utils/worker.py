"""
Background worker threads for long-running operations.

Handles auto-crop and TIFF merge operations with progress callbacks.
"""

import os
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Optional, List

from modules.pdf_tools.compression_profiles import DEFAULT_PROFILE_KEY
from modules.pdf_tools.core import DEFAULT_PDFA_PROFILE_KEY

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
            "cancelled": False,
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
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    return

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
            "cancelled": False,
            "errors": [],
        }
        self.force_cancel_requested = False

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
                should_cancel=lambda: self.force_cancel_requested,
            )
            cancelled = any(
                bool(error.get("cancelled"))
                or "cancelled" in str(error.get("error", "")).lower()
                for error in (errors or [])
            )
            return {
                "group": group_name,
                "success": success,
                "output_path": output_path,
                "errors": errors or [],
                "cancelled": cancelled,
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
                "cancelled": False,
            }

    def cancel(self, force: bool = False):
        """
        Request cancellation.

        First request stops scheduling new groups and lets active merges finish.
        A force request attempts to stop active merges mid-group.
        """
        self.cancelled = True
        if force:
            self.force_cancel_requested = True

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
                running_futures = {}
                next_index = 0

                def _submit_more_groups():
                    nonlocal next_index
                    while (
                        not self.cancelled
                        and next_index < total_groups
                        and len(running_futures) < worker_count
                    ):
                        group_name = group_names[next_index]
                        next_index += 1
                        future = executor.submit(self._merge_single_group, group_name)
                        running_futures[future] = group_name

                _submit_more_groups()

                while running_futures:
                    done, _pending = wait(
                        set(running_futures.keys()),
                        timeout=0.1,
                        return_when=FIRST_COMPLETED,
                    )
                    if not done:
                        continue

                    for future in done:
                        group_name = running_futures.pop(future)
                        result = future.result()
                        completed += 1
                        self.update_progress(completed, total_groups, group_name)

                        if result.get("cancelled"):
                            self.results["cancelled"] = True
                            self.cancelled = True
                            continue

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

                    _submit_more_groups()

            if self.cancelled:
                self.results["cancelled"] = True
                self.update_status(
                    f"Cancelled — Merged: {self.results['success']} | "
                    f"Failed: {self.results['failed']}"
                )
                return

            self.update_status(
                f"✅ Merged: {self.results['success']} | "
                f"❌ Failed: {self.results['failed']}"
            )

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
            "cancelled": False,
            "errors": [],
        }
        self.force_cancel_requested = False

    def cancel(self, force: bool = False):
        """
        Request cancellation.

        First request stops after the current TIFF file.
        A force request attempts to stop mid-file.
        """
        self.cancelled = True
        if force:
            self.force_cancel_requested = True

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
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    return

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
                    should_cancel=lambda: self.force_cancel_requested,
                )

                if not success:
                    if stats.get("cancelled"):
                        self.results["cancelled"] = True
                        self.update_status("Operation cancelled")
                        return
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
            "cancelled": False,
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
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    return

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
        reduce_size_enabled: bool = True,
        compression_profile_key: str = DEFAULT_PROFILE_KEY,
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
        self.reduce_size_enabled = bool(reduce_size_enabled)
        self.compression_profile_key = str(compression_profile_key or DEFAULT_PROFILE_KEY)
        self.metadata = metadata or {}
        self.tesseract_path = Path(tesseract_path) if tesseract_path else None
        self.force_cancel_requested = False
        self.results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "total_pages": 0,
            "cancelled": False,
            "errors": [],
            "skip_reasons": [],
            "warnings": [],
            "outputs": [],
        }

    def cancel(self, force: bool = False):
        """
        Request cancellation.

        First request performs a graceful stop after the current document.
        A force request attempts to stop mid-document.
        """
        self.cancelled = True
        if force:
            self.force_cancel_requested = True

    def _emit_ocr_progress(
        self,
        *,
        stage: str,
        message: str,
        current_pdf: int,
        total_pdfs: int,
        current_page: int,
        total_pages_in_pdf: int,
        completed_job_pages: int,
        total_job_pages: int,
        filename: str,
    ):
        """Emit structured OCR progress payload for UI progress bars."""
        if not self.progress_callback:
            return

        safe_pdf_total = max(total_pages_in_pdf, 1)
        safe_job_total = max(total_job_pages, 1)
        pdf_percent = (current_page / safe_pdf_total) * 100.0
        job_page_current = min(completed_job_pages + current_page, total_job_pages)
        job_percent = (job_page_current / safe_job_total) * 100.0

        self.progress_callback(
            {
                "stage": stage,
                "message": message,
                "current_pdf": current_pdf,
                "total_pdfs": total_pdfs,
                "current_page": current_page,
                "total_pages_in_pdf": total_pages_in_pdf,
                "pdf_percent": pdf_percent,
                "job_page_current": job_page_current,
                "job_page_total": total_job_pages,
                "job_percent": job_percent,
                "filename": filename,
                # Backward-compatible keys used by other panels.
                "current": current_pdf,
                "total": total_pdfs,
                "percentage": job_percent,
            }
        )

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
            self.results["total_pages"] = summary["page_count"]
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
            total_pages = max(summary["page_count"], 0)
            completed_pages = 0
            for index, document in enumerate(documents, start=1):
                if self.cancelled:
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled")
                    break

                document_name = document["name"]
                output_pdf_path = self.output_folder / f"{document_name}.pdf"
                document_pages = max(int(document.get("page_count", 0)), 1)

                self._emit_ocr_progress(
                    stage="document_start",
                    message=(
                        f"Analyzing pages for {output_pdf_path.name} "
                        f"({document_pages} page(s))"
                    ),
                    current_pdf=index,
                    total_pdfs=total_documents,
                    current_page=0,
                    total_pages_in_pdf=document_pages,
                    completed_job_pages=completed_pages,
                    total_job_pages=total_pages,
                    filename=output_pdf_path.name,
                )
                self.update_status(
                    f"OCR PDF {index}/{total_documents}: {output_pdf_path.name} "
                    f"({document_pages} page(s))"
                )

                def _on_document_progress(event: dict):
                    event_name = event.get("event")
                    page_current = int(event.get("page_current") or 0)
                    page_total = int(event.get("page_total") or document_pages)
                    page_label = event.get("page_label") or output_pdf_path.name

                    if event_name == "analyzing_page":
                        message = (
                            "Analyzing pages, determining pages to OCR, "
                            f"page {page_current} of {page_total} - "
                            f"{(page_current / max(page_total, 1)) * 100.0:.2f}%"
                        )
                        self._emit_ocr_progress(
                            stage="analyzing",
                            message=message,
                            current_pdf=index,
                            total_pdfs=total_documents,
                            current_page=0,
                            total_pages_in_pdf=page_total,
                            completed_job_pages=completed_pages,
                            total_job_pages=total_pages,
                            filename=output_pdf_path.name,
                        )
                        return

                    if event_name == "ocr_page":
                        message = (
                            f"Processing pg {page_current} of {page_total} - "
                            f"{(page_current / max(page_total, 1)) * 100.0:.2f}% "
                            f"({page_label})"
                        )
                        self._emit_ocr_progress(
                            stage="processing",
                            message=message,
                            current_pdf=index,
                            total_pdfs=total_documents,
                            current_page=page_current,
                            total_pages_in_pdf=page_total,
                            completed_job_pages=completed_pages,
                            total_job_pages=total_pages,
                            filename=output_pdf_path.name,
                        )

                result = ocr_document_to_pdf(
                    input_files=document["files"],
                    output_pdf_path=output_pdf_path,
                    document_name=document_name,
                    language=self.language,
                    skip_existing=self.skip_existing,
                    save_pdfa=self.save_pdfa,
                    skip_messy=self.skip_messy,
                    reduce_size_enabled=self.reduce_size_enabled,
                    compression_profile_key=self.compression_profile_key,
                    metadata=self.metadata,
                    tesseract_path=self.tesseract_path,
                    progress_callback=_on_document_progress,
                    should_cancel=lambda: self.force_cancel_requested,
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
                elif result["status"] == "cancelled":
                    self.results["cancelled"] = True
                    self.update_status("Operation cancelled by user")
                    break
                else:
                    self.results["failed"] += 1
                    doc_error = result.get("error") or "OCR failed"
                    self.results["errors"].append({
                        "file": output_pdf_path.name,
                        "error": doc_error,
                    })
                    self.report_error(output_pdf_path.name, doc_error)

                completed_pages += document_pages
                self._emit_ocr_progress(
                    stage="document_done",
                    message=(
                        f"Job Progress - PDF {index} of {total_documents} - "
                        f"{(completed_pages / max(total_pages, 1)) * 100.0:.2f}%"
                    ),
                    current_pdf=index,
                    total_pdfs=total_documents,
                    current_page=document_pages,
                    total_pages_in_pdf=document_pages,
                    completed_job_pages=completed_pages - document_pages,
                    total_job_pages=total_pages,
                    filename=output_pdf_path.name,
                )

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


class PdfConversionWorker(OperationWorker):
    """Worker for PDF conversion operations."""

    def __init__(
        self,
        *,
        selection_mode: str,
        input_path: Path,
        operation: str,
        reduce_size_enabled: bool = True,
        compression_profile_key: str = DEFAULT_PROFILE_KEY,
        split_output_type: str = "pdfs",
        extract_page_spec: str = "",
        remove_extracted_pages: bool = False,
        extract_removal_mode: str = "safe",
        pdfa_profile_key: str = DEFAULT_PDFA_PROFILE_KEY,
    ):
        super().__init__(name="PdfConversionWorker")
        self.selection_mode = str(selection_mode or "file")
        self.input_path = Path(input_path)
        self.operation = str(operation or "reduce_size")
        self.reduce_size_enabled = bool(reduce_size_enabled)
        self.compression_profile_key = str(compression_profile_key or DEFAULT_PROFILE_KEY)
        self.split_output_type = str(split_output_type or "pdfs")
        self.extract_page_spec = str(extract_page_spec or "").strip()
        self.remove_extracted_pages = bool(remove_extracted_pages)
        self.extract_removal_mode = str(extract_removal_mode or "safe")
        self.pdfa_profile_key = str(pdfa_profile_key or DEFAULT_PDFA_PROFILE_KEY)
        self.results = {
            "success": 0,
            "failed": 0,
            "total": 0,
            "cancelled": False,
            "errors": [],
            "outputs": [],
            "warnings": [],
        }

    def _set_cancelled(self):
        self.results["cancelled"] = True
        self.update_status("Operation cancelled")

    def _record_error(self, filename: str, error: str):
        self.results["failed"] += 1
        self.results["errors"].append({"file": filename, "error": error})
        self.report_error(filename, error)

    def run(self):
        """Execute selected PDF conversion operation."""
        from modules.pdf_tools.core import (
            convert_pdf_to_pdfa,
            extract_pdf_pages,
            reduce_pdf_size,
            split_pdf_to_images,
            split_pdf_to_single_page_pdfs,
        )
        import shutil

        try:
            if self.operation == "reduce_size":
                if self.selection_mode == "folder":
                    pdf_files = sorted(
                        [
                            path for path in self.input_path.iterdir()
                            if path.is_file() and path.suffix.lower() == ".pdf"
                        ],
                        key=lambda path: path.name.lower(),
                    )
                else:
                    pdf_files = [self.input_path]

                if not pdf_files:
                    self.update_status("No PDF files found")
                    return

                self.results["total"] = len(pdf_files)
                output_root = (
                    self.input_path / "reduced-pdfs"
                    if self.selection_mode == "folder"
                    else self.input_path.parent / "reduced-pdfs"
                )
                output_root.mkdir(parents=True, exist_ok=True)

                for index, pdf_path in enumerate(pdf_files, start=1):
                    if self.cancelled:
                        self._set_cancelled()
                        return

                    self.update_progress(index, len(pdf_files), pdf_path.name)
                    self.update_status(f"Reducing: {pdf_path.name}")
                    output_pdf_path = output_root / pdf_path.name

                    if not self.reduce_size_enabled:
                        try:
                            shutil.copy2(pdf_path, output_pdf_path)
                            self.results["success"] += 1
                            self.results["outputs"].append(str(output_pdf_path))
                        except Exception as exc:
                            self._record_error(pdf_path.name, str(exc))
                        continue

                    status, error, _stats = reduce_pdf_size(
                        input_pdf_path=pdf_path,
                        output_pdf_path=output_pdf_path,
                        reduce_size_enabled=True,
                        compression_profile_key=self.compression_profile_key,
                        should_cancel=lambda: self.cancelled,
                    )
                    if status == "cancelled":
                        self._set_cancelled()
                        return
                    if status != "success":
                        self._record_error(pdf_path.name, error or "Reduce size failed")
                        continue

                    self.results["success"] += 1
                    self.results["outputs"].append(str(output_pdf_path))

                self.update_status(
                    f"✅ Reduced: {self.results['success']} | ❌ Failed: {self.results['failed']}"
                )
                return

            if self.operation == "pdfa":
                if self.selection_mode == "folder":
                    pdf_files = sorted(
                        [
                            path for path in self.input_path.iterdir()
                            if path.is_file() and path.suffix.lower() == ".pdf"
                        ],
                        key=lambda path: path.name.lower(),
                    )
                else:
                    pdf_files = [self.input_path]

                if not pdf_files:
                    self.update_status("No PDF files found")
                    return

                self.results["total"] = len(pdf_files)
                output_root = (
                    self.input_path / "pdfa-pdfs"
                    if self.selection_mode == "folder"
                    else self.input_path.parent / "pdfa-pdfs"
                )
                output_root.mkdir(parents=True, exist_ok=True)

                for index, pdf_path in enumerate(pdf_files, start=1):
                    if self.cancelled:
                        self._set_cancelled()
                        return

                    self.update_progress(index, len(pdf_files), pdf_path.name)
                    self.update_status(f"Converting to PDF/A: {pdf_path.name}")
                    output_pdf_path = output_root / pdf_path.name
                    status, error, _stats = convert_pdf_to_pdfa(
                        input_pdf_path=pdf_path,
                        output_pdf_path=output_pdf_path,
                        pdfa_profile_key=self.pdfa_profile_key,
                        should_cancel=lambda: self.cancelled,
                    )
                    if status == "cancelled":
                        self._set_cancelled()
                        return
                    if status != "success":
                        self._record_error(pdf_path.name, error or "PDF/A conversion failed")
                        continue

                    self.results["success"] += 1
                    self.results["outputs"].append(str(output_pdf_path))

                self.update_status(
                    f"✅ PDF/A Converted: {self.results['success']} | ❌ Failed: {self.results['failed']}"
                )
                return

            if self.selection_mode != "file":
                self._record_error("operation", "This operation requires one PDF file.")
                self.update_status("Operation requires a single file selection")
                return

            self.results["total"] = 1
            source_pdf = self.input_path

            if self.operation == "split_pdf":
                self.update_progress(1, 1, source_pdf.name)
                self.update_status(f"Splitting: {source_pdf.name}")
                if self.split_output_type == "pdfs":
                    output_folder = source_pdf.parent / f"{source_pdf.stem}_split_pdfs"
                    status, error, stats = split_pdf_to_single_page_pdfs(
                        input_pdf_path=source_pdf,
                        output_folder=output_folder,
                        should_cancel=lambda: self.cancelled,
                    )
                else:
                    output_folder = source_pdf.parent / f"{source_pdf.stem}_images"
                    format_map = {
                        "jpeg": "JPEG",
                        "png": "PNG",
                        "tiff": "TIFF",
                    }
                    status, error, stats = split_pdf_to_images(
                        input_pdf_path=source_pdf,
                        output_folder=output_folder,
                        image_format=format_map.get(self.split_output_type, "JPEG"),
                        jpeg_quality=90,
                        dpi=200,
                        should_cancel=lambda: self.cancelled,
                    )

                if status == "cancelled":
                    self._set_cancelled()
                    return
                if status != "success":
                    self._record_error(source_pdf.name, error or "Split failed")
                    self.update_status(f"Error: {error or 'Split failed'}")
                    return

                self.results["success"] = 1
                self.results["outputs"].append(str(output_folder))
                output_count = int(stats.get("output_count", 0))
                self.update_status(f"✅ Created {output_count} output file(s)")
                return

            if self.operation == "extract_pages":
                if not self.extract_page_spec:
                    self._record_error(source_pdf.name, "Page selection is required.")
                    self.update_status("Page selection is required")
                    return

                self.update_progress(1, 1, source_pdf.name)
                self.update_status(f"Extracting pages: {source_pdf.name}")
                extracted_output = source_pdf.parent / f"{source_pdf.stem}_extracted.pdf"
                remaining_output = source_pdf.parent / f"{source_pdf.stem}_remaining.pdf"
                status, error, stats = extract_pdf_pages(
                    input_pdf_path=source_pdf,
                    extracted_output_path=extracted_output,
                    page_spec=self.extract_page_spec,
                    remove_extracted_pages=self.remove_extracted_pages,
                    removal_mode=self.extract_removal_mode,
                    remaining_output_path=remaining_output,
                    should_cancel=lambda: self.cancelled,
                )
                if status == "cancelled":
                    self._set_cancelled()
                    return
                if status != "success":
                    self._record_error(source_pdf.name, error or "Extract pages failed")
                    self.update_status(f"Error: {error or 'Extract pages failed'}")
                    return

                self.results["success"] = 1
                self.results["outputs"].append(str(extracted_output))
                if stats.get("remaining_output"):
                    self.results["outputs"].append(str(stats["remaining_output"]))
                self.update_status(
                    f"✅ Extracted {stats.get('extracted_pages', 0)} page(s)"
                )
                return

            self._record_error("operation", f"Unknown operation: {self.operation}")
            self.update_status(f"Unknown operation: {self.operation}")

        except Exception as exc:
            self.update_status(f"Error: {exc}")
            self.report_error("operation", str(exc))

    def get_results(self) -> dict:
        return self.results
