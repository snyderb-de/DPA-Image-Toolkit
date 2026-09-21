"""
Background worker threads for long-running operations.

Handles long-running toolkit operations with progress callbacks.
"""

import threading
from pathlib import Path
from typing import Callable, Optional, List

from modules.auto_cropping.core import DEFAULT_WHITE_THRESHOLD
from modules.tiff_combine.compression import DEFAULT_COMPRESSION as MERGE_DEFAULT_COMPRESSION
from modules.pdf_tools.compression_profiles import DEFAULT_PROFILE_KEY
from modules.pdf_tools.core import DEFAULT_PDFA_PROFILE_KEY
from utils.batch import (
    GroupOutcome,
    ItemOutcome,
    find_image_files,
    run_file_batch,
    run_group_batch,
)
from utils.job_result import JobError, JobResult

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
        straighten: bool = False,
        white_threshold: int = DEFAULT_WHITE_THRESHOLD,
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
        self.straighten = straighten
        # Ceiling on what counts as background. crop_image may choose a lower
        # value for a given page; it never goes above this.
        self.white_threshold = int(white_threshold)

        self.results = JobResult(verb="Cropped")

    def _crop_one(self, image_file: Path) -> ItemOutcome:
        from modules.auto_cropping.core import (
            CROP_SKIPPED,
            CROP_SUCCESS,
            crop_image,
        )

        output_path, error_msg, status = crop_image(
            image_file,
            self.output_folder,
            white_threshold=self.white_threshold,
            preserve_dpi=True,
            straighten=self.straighten,
        )
        if status == CROP_SUCCESS:
            return ItemOutcome.ok(output_path)
        if status == CROP_SKIPPED:
            # Inputs are never moved; the source stays available for review.
            self.results.errors.append(JobError(image_file.name, error_msg))
            return ItemOutcome.skip(error_msg)
        return ItemOutcome.fail(error_msg)

    def run(self):
        """Execute auto-crop operation."""
        try:
            run_file_batch(
                find_image_files(self.input_folder),
                result=self.results,
                process=self._crop_one,
                reporter=self,
                gerund="Cropping",
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


class StraightenWorker(OperationWorker):
    """Worker for standalone image straightening operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        error_folder: Path,
    ):
        super().__init__(name="StraightenWorker")
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.error_folder = Path(error_folder)
        self.results = JobResult(verb="Straightened", extra={"angles": []})

    def _straighten_one(self, image_file: Path) -> ItemOutcome:
        from modules.auto_cropping.core import straighten_image

        output_path, error_msg, stats = straighten_image(
            image_file,
            self.output_folder,
            preserve_dpi=True,
        )
        if error_msg:
            return ItemOutcome.fail(error_msg)

        self.results.extra["angles"].append({
            "file": image_file.name,
            "angle": stats.get("angle", 0.0),
            "output": output_path,
        })
        return ItemOutcome.ok(output_path)

    def run(self):
        """Execute standalone straighten operation."""
        try:
            run_file_batch(
                find_image_files(self.input_folder),
                result=self.results,
                process=self._straighten_one,
                reporter=self,
                gerund="Straightening",
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


class TiffMergeWorker(OperationWorker):
    """Worker for TIFF merge operations."""

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        error_folder: Path,
        groups: dict,
        compression: str = MERGE_DEFAULT_COMPRESSION,
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
        self.compression = compression

        self.results = JobResult(verb="Merged")
        self.force_cancel_requested = False

    def _merge_one(self, group_name: str) -> GroupOutcome:
        """Merge one TIFF group."""
        from modules.tiff_combine.core import merge_tiff_group

        success, output_path, errors = merge_tiff_group(
            group_name,
            self.input_folder,
            self.output_folder,
            dpi_per_file=True,
            should_cancel=lambda: self.force_cancel_requested,
            compression=self.compression,
        )
        errors = errors or []

        # merge_tiff_group flags a cancellation on the error it records, so the
        # flag is authoritative — no need to read the message text.
        if any(error.get("cancelled") for error in errors):
            return GroupOutcome.abort()

        if success:
            return GroupOutcome.ok(output_path)
        return GroupOutcome.fail(
            (error.get("file", group_name), error.get("error", "Unknown error"))
            for error in errors
        )

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
            run_group_batch(
                sorted(self.groups),
                result=self.results,
                process=self._merge_one,
                reporter=self,
                empty_message="No groups to merge",
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


class TiffSplitWorker(OperationWorker):
    """Worker for TIFF split operations."""

    def __init__(
        self,
        input_files: List[Path],
        output_root: Optional[Path] = None,
        use_root_output: bool = False,
        operation: str = "split",
        page_spec: str = "",
        compression: str = MERGE_DEFAULT_COMPRESSION,
    ):
        super().__init__(name="TiffSplitWorker")
        self.input_files = [Path(file_path) for file_path in input_files]
        self.output_root = Path(output_root) if output_root else None
        self.use_root_output = use_root_output
        # "split" writes one file per page; "select" writes one document holding
        # the chosen pages in the chosen order. Same loop, different per-file work.
        self.operation = operation
        self.page_spec = page_spec
        self.compression = compression
        verb = "Split" if operation == "split" else "Extracted"
        self.results = JobResult(verb=verb, total=len(self.input_files))
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

    def _select_pages_one(self, file_path: Path) -> ItemOutcome:
        """Write the chosen pages of one source into a single document."""
        from modules.tiff_combine.pages import select_pages

        if self.use_root_output and self.output_root:
            destination = self.output_root / f"{file_path.stem}_selected.tif"
        else:
            destination = file_path.parent / f"{file_path.stem}_selected.tif"

        ok, output, error, stats = select_pages(
            file_path,
            destination,
            self.page_spec,
            compression=self.compression,
            should_cancel=lambda: self.force_cancel_requested,
        )
        if stats.get("cancelled"):
            return ItemOutcome.abort()
        if not ok:
            return ItemOutcome.fail(error or "Could not extract pages")
        return ItemOutcome.ok(output)

    def _split_one(self, file_path: Path) -> ItemOutcome:
        from modules.tiff_split.core import split_tiff_file

        output_folder = self.output_root if (self.use_root_output and self.output_root) else None
        success, output_paths, error_msg, stats = split_tiff_file(
            file_path,
            output_folder=output_folder,
            skip_single_page=True,
            should_cancel=lambda: self.force_cancel_requested,
        )

        if not success:
            if stats.get("cancelled"):
                return ItemOutcome.abort()
            return ItemOutcome.fail(error_msg or "Split failed")

        if stats.get("skipped"):
            return ItemOutcome.skip(stats.get("reason") or "Single-page TIFF")
        return ItemOutcome.ok(output_paths)

    def run(self):
        """Execute TIFF split operation."""
        try:
            selecting = self.operation == "select"
            run_file_batch(
                self.input_files,
                result=self.results,
                process=self._select_pages_one if selecting else self._split_one,
                reporter=self,
                gerund="Extracting from" if selecting else "Splitting",
                empty_message="No TIFF files selected",
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


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
        self.results = JobResult(verb="Bordered")

    def _border_one(self, image_file: Path) -> ItemOutcome:
        from modules.image_border.core import add_border_to_image

        output_path, error_msg, _stats = add_border_to_image(
            image_file,
            self.output_folder,
            preserve_dpi=True,
        )
        return ItemOutcome.fail(error_msg) if error_msg else ItemOutcome.ok(output_path)

    def run(self):
        """Execute add-border operation."""
        try:
            run_file_batch(
                find_image_files(self.input_folder),
                result=self.results,
                process=self._border_one,
                reporter=self,
                gerund="Adding border",
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


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
        only_documents=None,
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
        # When set, only these documents are processed. Used to re-run the
        # documents a previous job flagged, without redoing the whole folder.
        self.only_documents = set(only_documents) if only_documents else None
        self.force_cancel_requested = False
        self.results = JobResult(verb="OCR'd", extra={"total_pages": 0, "flagged_documents": []})

    def cancel(self, force: bool = False):
        """
        Request cancellation.

        First request performs a graceful stop after the current document.
        A force request attempts to stop mid-document.
        """
        self.cancelled = True
        if force:
            self.force_cancel_requested = True

    def _ocr_options(self):
        """The OCR settings for this run, as one value."""
        from modules.ocr_pdf.core import OcrOptions

        return OcrOptions(
            language=self.language,
            skip_existing=self.skip_existing,
            save_pdfa=self.save_pdfa,
            skip_messy=self.skip_messy,
            metadata=self.metadata,
            tesseract_path=self.tesseract_path,
            reduce_size_enabled=self.reduce_size_enabled,
            compression_profile_key=self.compression_profile_key,
        )

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
                self.results.record_failure("dependency", error_msg)
                self.report_error("dependency", error_msg)
                return
            if error_msg:
                self.results.note(error_msg)
                self.update_status(error_msg)

            self.update_status("Scanning folder for OCR page images...")
            documents = group_ocr_input_files(self.input_folder)
            if self.only_documents is not None:
                documents = [d for d in documents if d["name"] in self.only_documents]
                self.update_status(
                    f"Re-running {len(documents)} flagged document(s) with the quality gate off"
                )

            if not documents:
                self.update_status("No supported image files found")
                return

            summary = summarize_ocr_documents(documents)
            self.results.total = summary["document_count"]
            self.results.extra["total_pages"] = summary["page_count"]
            self.update_status(
                "Found "
                f"{summary['page_count']} page image(s) across "
                f"{summary['document_count']} output PDF(s)"
            )

            if self.cancelled:
                self.results.mark_cancelled()
                self.update_status("Operation cancelled")
                return

            pdfa_warning_added = False
            total_documents = len(documents)
            total_pages = max(summary["page_count"], 0)
            completed_pages = 0
            for index, document in enumerate(documents, start=1):
                if self.cancelled:
                    self.results.mark_cancelled()
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
                        return

                    if event_name == "skip_ocr_page":
                        message = (
                            f"Skipping OCR for pg {page_current} of {page_total} - "
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
                    options=self._ocr_options(),
                    progress_callback=_on_document_progress,
                    should_cancel=lambda: self.force_cancel_requested,
                )

                if result["status"] == "success":
                    self.results.record_success(result["output_path"])
                    details = result.get("details") or {}
                    for warning in details.get("warnings", []):
                        self.results.note(warning)
                        self.update_status(warning)
                    flagged = details.get("flagged_pages", [])
                    for flagged_page in flagged:
                        reason_text = ", ".join(flagged_page.get("reasons", [])) or "flagged by quality precheck"
                        page_number = flagged_page.get("page_number")
                        page_label = flagged_page.get("file") or "page"
                        if page_number is not None:
                            self.update_status(
                                f"Skipped OCR text on pg {page_number}: {page_label} ({reason_text})"
                            )
                        else:
                            self.update_status(
                                f"Skipped OCR text on {page_label} ({reason_text})"
                            )
                    # Pages are assessed whether or not the gate is on, so
                    # details lists them either way. Only record them when the
                    # gate actually withheld OCR text — otherwise a retry would
                    # offer to redo pages that already have a text layer.
                    if flagged and self.skip_messy:
                        # Keep the document, not just the log line, so the run
                        # can be repeated for these pages with the gate off.
                        self.results.extra.setdefault("flagged_documents", []).append({
                            "document": document_name,
                            "output": output_pdf_path.name,
                            "pages": [
                                {
                                    "file": page.get("file", "page"),
                                    "page_number": page.get("page_number"),
                                    "reasons": list(page.get("reasons", [])),
                                }
                                for page in flagged
                            ],
                        })
                    if self.save_pdfa and not result.get("used_pdfa") and not pdfa_warning_added:
                        warning = (
                            "PDF/A was unavailable or incompatible with selected options — "
                            "created standard searchable PDFs instead."
                        )
                        self.results.note(warning)
                        self.update_status(warning)
                        pdfa_warning_added = True
                elif result["status"] == "skipped":
                    skip_reason = result.get("error") or "Skipped"
                    self.results.record_skip(output_pdf_path.name, skip_reason)
                    self.update_status(f"Skipped: {output_pdf_path.name} — {skip_reason}")
                    details = result.get("details") or {}
                    for page in details.get("flagged_pages", []):
                        reason_text = ", ".join(page.get("reasons", [])) or "flagged by precheck"
                        self.report_error(page.get("file", "page"), f"OCR quality flag: {reason_text}")
                elif result["status"] == "cancelled":
                    self.results.mark_cancelled()
                    self.update_status("Operation cancelled by user")
                    break
                else:
                    doc_error = result.get("error") or "OCR failed"
                    self.results.record_failure(output_pdf_path.name, doc_error)
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

            self.update_status(self.results.summary())

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.report_error("operation", str(e))

    def get_results(self) -> dict:
        """Get operation results."""
        return self.results.to_dict()


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
        self.results = JobResult(verb="Converted")

    def _set_cancelled(self):
        self.results.mark_cancelled()
        self.update_status("Operation cancelled")

    def _record_error(self, filename: str, error: str):
        self.results.record_failure(filename, error)
        self.report_error(filename, error)

    def _pdf_files(self) -> List[Path]:
        """Every PDF the selection covers, in stable order."""
        if self.selection_mode != "folder":
            return [self.input_path]
        return sorted(
            (path for path in self.input_path.iterdir()
             if path.is_file() and path.suffix.lower() == ".pdf"),
            key=lambda path: path.name.lower(),
        )

    def _output_root(self, name: str) -> Path:
        base = self.input_path if self.selection_mode == "folder" else self.input_path.parent
        root = base / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _outcome(status: str, error: Optional[str], output: Path, fallback: str) -> ItemOutcome:
        """Map the (status, error, stats) shape every pdf_tools op returns."""
        if status == "cancelled":
            return ItemOutcome.abort()
        if status != "success":
            return ItemOutcome.fail(error or fallback)
        return ItemOutcome.ok(output)

    def _reduce_one(self, pdf_path: Path) -> ItemOutcome:
        from modules.pdf_tools.core import reduce_pdf_size
        import shutil

        output_pdf_path = self._reduce_root / pdf_path.name
        if not self.reduce_size_enabled:
            shutil.copy2(pdf_path, output_pdf_path)
            return ItemOutcome.ok(output_pdf_path)

        status, error, _stats = reduce_pdf_size(
            input_pdf_path=pdf_path,
            output_pdf_path=output_pdf_path,
            reduce_size_enabled=True,
            compression_profile_key=self.compression_profile_key,
            should_cancel=lambda: self.cancelled,
        )
        return self._outcome(status, error, output_pdf_path, "Reduce size failed")

    def _pdfa_one(self, pdf_path: Path) -> ItemOutcome:
        from modules.pdf_tools.core import convert_pdf_to_pdfa

        output_pdf_path = self._pdfa_root / pdf_path.name
        status, error, _stats = convert_pdf_to_pdfa(
            input_pdf_path=pdf_path,
            output_pdf_path=output_pdf_path,
            pdfa_profile_key=self.pdfa_profile_key,
            should_cancel=lambda: self.cancelled,
        )
        return self._outcome(status, error, output_pdf_path, "PDF/A conversion failed")

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

        # One result type, but each operation describes itself differently.
        self.results.verb = {
            "reduce_size": "Reduced",
            "pdfa": "PDF/A Converted",
            "split_pdf": "Split",
            "extract_pages": "Extracted",
        }.get(self.operation, "Converted")

        try:
            if self.operation in ("reduce_size", "pdfa"):
                if self.operation == "reduce_size":
                    self._reduce_root = self._output_root("reduced-pdfs")
                    process, gerund = self._reduce_one, "Reducing"
                else:
                    self._pdfa_root = self._output_root("pdfa-pdfs")
                    process, gerund = self._pdfa_one, "Converting to PDF/A"

                run_file_batch(
                    self._pdf_files(),
                    result=self.results,
                    process=process,
                    reporter=self,
                    gerund=gerund,
                    empty_message="No PDF files found",
                )
                return

            if self.selection_mode != "file":
                self._record_error("operation", "This operation requires one PDF file.")
                self.update_status("Operation requires a single file selection")
                return

            self.results.total = 1
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

                self.results.record_success(output_folder)
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

                self.results.record_success(extracted_output)
                if stats.get("remaining_output"):
                    self.results.outputs.append(str(stats["remaining_output"]))
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
        """Get operation results."""
        return self.results.to_dict()
