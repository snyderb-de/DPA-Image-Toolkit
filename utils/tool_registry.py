"""
The toolkit's seven tools, described in one place.

Each ToolSpec owns everything that varies between tools: its id, display name,
how its dependencies are reported and gated, how an input selection is
validated (prepare), and how a worker is built for it (start). Callers work
through `prepare_tool` / `start_tool` and never need to know which tool they
hold.

Adding a tool means adding one ToolSpec.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from modules.auto_cropping.core import DEFAULT_WHITE_THRESHOLD
from modules.ocr_pdf.core import (
    check_ocr_dependencies,
    get_ocr_dependency_statuses,
    group_ocr_input_files,
    summarize_ocr_documents,
)
from modules.pdf_tools.compression_profiles import DEFAULT_PROFILE_KEY
from modules.pdf_tools.core import (
    DEFAULT_PDFA_PROFILE_KEY,
    check_pdf_conversion_dependencies,
    get_pdf_conversion_dependency_statuses,
)
from modules.tiff_combine.compression import DEFAULT_COMPRESSION as MERGE_DEFAULT_COMPRESSION
from modules.tiff_combine.naming import validate_naming_convention
from utils.job_result import write_error_report
from utils.file_handler import (
    create_error_folder,
    validate_image_files,
    validate_tif_files,
)
from utils.tool_dependencies import (
    check_tool_dependencies,
    get_tool_dependency_statuses,
)
from utils.worker import (
    AddBorderWorker,
    AutoCropWorker,
    OcrPdfWorker,
    PdfConversionWorker,
    StraightenWorker,
    TiffMergeWorker,
    TiffSplitWorker,
)


class ToolError(Exception):
    """A tool rejected the request. The message is shown to the user."""


@dataclass(frozen=True)
class Prepared:
    """What a prepare step produced: state to keep, and a payload for the UI."""

    data: dict
    payload: dict


@dataclass(frozen=True)
class Started:
    """A worker ready to run, and the folders its job will use.

    `output_folder` is the boundary an undo is allowed to delete within, and
    `input_folder` the folder it must refuse. A tool that leaves
    `output_folder` unset cannot be undone, which is the safe default.
    """

    worker: object
    input_folder: Optional[Path] = None
    error_folder: Optional[Path] = None
    output_folder: Optional[Path] = None


@dataclass(frozen=True)
class ToolSpec:
    id: str
    display_name: str
    prepare: Callable[[dict], Prepared]
    start: Callable[[dict, dict], Started]
    statuses: Callable[[dict], list]
    check: Callable[[dict], tuple]


# ── Shared helpers ─────────────────────────────────────────────────────────

def _require_folder(body: dict, key: str = "folder") -> Path:
    raw = body.get(key)
    if not raw or not Path(raw).is_dir():
        raise ToolError("Invalid folder")
    return Path(raw)


def _prepared_folder(data: dict) -> Path:
    # An empty string becomes Path("."), which is a real directory — without
    # this guard an unprepared start would run against the working directory.
    raw = str(data.get("folder") or "").strip()
    if not raw:
        raise ToolError("No folder prepared")
    folder = Path(raw)
    if not folder.is_dir():
        raise ToolError("No folder prepared")
    return folder


def _prepare_image_folder(body: dict) -> Prepared:
    """Shared by every tool that consumes a folder of images."""
    folder = _require_folder(body)
    valid, files, error = validate_image_files(folder)
    if not valid:
        raise ToolError(error or "No image files found")
    return Prepared(
        data={"folder": str(folder), "file_count": len(files)},
        payload={"file_count": len(files)},
    )


def _make_output(folder: Path, name: str) -> Path:
    output = folder / name
    output.mkdir(parents=True, exist_ok=True)
    return output


def _make_error_folder(base: Path, subfolder: str | None = None) -> Path:
    # A job that cannot record its failures refuses to start rather than run
    # and drop them, so the message reaches the user as a tool error.
    try:
        errors = create_error_folder(base)
        if subfolder:
            errors = errors / subfolder
            errors.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ToolError(f"Could not create the errored-files folder: {exc}") from exc
    return errors


def _statuses_by_key(tool_key: str) -> Callable[[dict], list]:
    return lambda _body: get_tool_dependency_statuses(tool_key)


def _check_by_key(tool_key: str) -> Callable[[dict], tuple]:
    def check(_body: dict) -> tuple:
        ok, message, _details = check_tool_dependencies(tool_key)
        return ok, message

    return check


# ── Auto Crop ──────────────────────────────────────────────────────────────

# Below 200 the core floors it, above the default it is ignored, so anything
# outside this range is a no-op the user would read as a broken control.
WHITE_THRESHOLD_MIN = 200
WHITE_THRESHOLD_MAX = DEFAULT_WHITE_THRESHOLD


def _white_threshold(body: dict) -> int:
    raw = body.get("white_threshold", DEFAULT_WHITE_THRESHOLD)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_WHITE_THRESHOLD
    return max(WHITE_THRESHOLD_MIN, min(WHITE_THRESHOLD_MAX, value))


def _start_auto_crop(body: dict, data: dict) -> Started:
    folder = _prepared_folder(data)
    errors = _make_error_folder(folder)
    output = _make_output(folder, "cropped")
    return Started(
        worker=AutoCropWorker(
            folder, output,
            straighten=bool(body.get("straighten", False)),
            white_threshold=_white_threshold(body),
        ),
        input_folder=folder,
        error_folder=errors,
        output_folder=output,
    )


# ── Straighten Images ──────────────────────────────────────────────────────

def _start_straighten(_body: dict, data: dict) -> Started:
    folder = _prepared_folder(data)
    errors = _make_error_folder(folder, "straighten")
    output = _make_output(folder, "straightened")
    return Started(
        worker=StraightenWorker(folder, output),
        input_folder=folder,
        error_folder=errors,
        output_folder=output,
    )


# ── Add Border ─────────────────────────────────────────────────────────────

def _start_add_border(_body: dict, data: dict) -> Started:
    folder = _prepared_folder(data)
    errors = _make_error_folder(folder, "add-border")
    output = _make_output(folder, "bordered")
    return Started(
        worker=AddBorderWorker(folder, output),
        input_folder=folder,
        error_folder=errors,
        output_folder=output,
    )


# ── Merge TIFFs ────────────────────────────────────────────────────────────

def _prepare_merge_tiffs(body: dict) -> Prepared:
    folder = _require_folder(body)
    valid, files, error = validate_tif_files(folder)
    if not valid:
        raise ToolError(error or "No TIFF files found")
    groups, _is_valid, warnings = validate_naming_convention(folder)
    return Prepared(
        data={
            "folder": str(folder),
            "groups": {name: [str(p) for p in paths] for name, paths in groups.items()},
            "warnings": warnings,
        },
        payload={
            "group_count": len(groups),
            "file_count": len(files),
            "warnings": warnings,
        },
    )


def _start_merge_tiffs(body: dict, data: dict) -> Started:
    folder = _prepared_folder(data)
    groups_raw = data.get("groups", {})
    if not groups_raw:
        raise ToolError("No folder/groups prepared")
    groups = {name: [Path(p) for p in paths] for name, paths in groups_raw.items()}
    errors = _make_error_folder(folder)
    output = _make_output(folder, "merged")
    return Started(
        worker=TiffMergeWorker(
            folder, output, groups,
            compression=str(body.get("compression") or MERGE_DEFAULT_COMPRESSION),
        ),
        input_folder=folder,
        error_folder=errors,
        output_folder=output,
    )


# ── Split TIFFs ────────────────────────────────────────────────────────────

def _prepare_split_tiffs(body: dict) -> Prepared:
    mode = body.get("mode", "folder")
    if mode == "folder":
        folder = _require_folder(body)
        valid, tif_files, error = validate_tif_files(folder)
        if not valid:
            raise ToolError(error or "No TIFF files found")
        file_paths = [str(p) for p in tif_files]
    else:
        folder = body.get("folder")
        file_paths = [f for f in body.get("files", []) if Path(f).is_file()]
        if not file_paths:
            raise ToolError("No valid TIFF files")

    return Prepared(
        data={
            "mode": mode,
            "folder": str(folder) if folder else None,
            "files": file_paths,
            "file_count": len(file_paths),
        },
        payload={"file_count": len(file_paths)},
    )


def _start_split_tiffs(body: dict, data: dict) -> Started:
    file_paths = [Path(p) for p in data.get("files", [])]
    if not file_paths:
        raise ToolError("No files prepared")

    folder = data.get("folder")
    if data.get("mode", "folder") == "folder" and folder:
        output_root = _make_output(Path(folder), "extracted-pages")
        error_base = Path(folder)
        use_root = True
    else:
        output_root = None
        error_base = file_paths[0].parent
        use_root = False

    operation = str(body.get("operation") or "split").strip().lower()
    if operation not in ("split", "select"):
        raise ToolError(f"Unknown operation: {operation}")

    page_spec = str(body.get("page_spec") or "").strip()
    if operation == "select":
        if not page_spec:
            raise ToolError("Enter which pages to keep, for example 1-3 or 3,1,2.")
        # Fail here rather than per file, so a typo is one clear message
        # instead of one error for every TIFF in the selection.
        from modules.tiff_combine.pages import count_pages, parse_page_order

        try:
            parse_page_order(page_spec, count_pages(file_paths[0]))
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(f"Could not read {file_paths[0].name}: {exc}") from exc

    errors = _make_error_folder(error_base, "split-tiffs")
    return Started(
        worker=TiffSplitWorker(
            file_paths, output_root, use_root,
            operation=operation,
            page_spec=page_spec,
            compression=str(body.get("compression") or MERGE_DEFAULT_COMPRESSION),
        ),
        input_folder=Path(folder) if folder else None,
        error_folder=errors,
        # File mode scatters <name>_pages/ folders beside each source, so there
        # is no single root an undo could be bounded to.
        output_folder=output_root if use_root else None,
    )


# ── OCR to PDF ─────────────────────────────────────────────────────────────

def _prepare_ocr_pdf(body: dict) -> Prepared:
    folder = _require_folder(body)
    try:
        documents = group_ocr_input_files(folder)
    except Exception as exc:
        raise ToolError(str(exc)) from exc
    if not documents:
        raise ToolError("No supported image files found")

    summary = summarize_ocr_documents(documents)
    return Prepared(
        data={
            "folder": str(folder),
            "document_count": summary["document_count"],
            "page_count": summary["page_count"],
        },
        payload={
            "document_count": summary["document_count"],
            "page_count": summary["page_count"],
        },
    )


def _start_ocr_pdf(body: dict, data: dict) -> Started:
    folder = _prepared_folder(data)
    retry = bool(body.get("only_documents"))
    errors = _make_error_folder(folder, "ocr-pdf")
    output = _make_output(folder, "PDFs")
    return Started(
        worker=OcrPdfWorker(
            input_folder=folder,
            output_folder=output,
            language="eng",
            skip_existing=bool(body.get("skip_existing", True)),
            save_pdfa=True,
            # A retry names the documents to redo and turns the gate off for
            # them; nothing else in the folder is touched.
            skip_messy=bool(body.get("skip_messy", True)) and not retry,
            only_documents=body.get("only_documents") or None,
            reduce_size_enabled=bool(body.get("reduce_size", True)),
            compression_profile_key=str(
                body.get("compression_profile", DEFAULT_PROFILE_KEY)
            ),
        ),
        input_folder=folder,
        error_folder=errors,
        output_folder=output,
    )


def _check_ocr_pdf(_body: dict) -> tuple:
    ok, message, _info = check_ocr_dependencies(language="eng", require_pdfa=True)
    return ok, message


# ── PDF Conversion ─────────────────────────────────────────────────────────

def _prepare_pdf_conversion(body: dict) -> Prepared:
    raw_path = body.get("path")
    if not raw_path:
        raise ToolError("No path provided")

    path = Path(raw_path)
    mode = body.get("mode", "file")
    if mode == "folder":
        if not path.is_dir():
            raise ToolError("Not a valid folder")
        count = len(
            [f for f in path.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]
        )
        if count == 0:
            raise ToolError("No PDF files in folder")
        payload = {"file_count": count}
    else:
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise ToolError("Not a valid PDF file")
        payload = {"filename": path.name}

    return Prepared(
        data={
            "path": str(path),
            "mode": mode,
            "operation": body.get("operation", "reduce_size"),
        },
        payload=payload,
    )


# split_pdf and extract_pages rewrite or take apart one document, so a folder
# selection has no meaning for them. The UI hides the folder toggle for both,
# which makes this reachable only by posting to the route directly.
_PDF_SINGLE_FILE_ONLY = ("split_pdf", "extract_pages")


def _pdf_output_root(
    operation: str, input_path: Path, split_output_type: str
) -> Optional[Path]:
    """The one folder this job writes into, or None when it has no single one.

    This is the folder an undo is allowed to delete within, so it is decided
    here rather than inside the worker thread. extract_pages writes beside its
    source, and the source folder is never a folder an undo may touch, so it
    gets nothing and cannot be undone.
    """
    if operation == "reduce_size":
        base = input_path if input_path.is_dir() else input_path.parent
        return _make_output(base, "reduced-pdfs")
    if operation == "pdfa":
        base = input_path if input_path.is_dir() else input_path.parent
        return _make_output(base, "pdfa-pdfs")
    if operation == "split_pdf":
        suffix = "_split_pdfs" if split_output_type == "pdfs" else "_images"
        return _make_output(input_path.parent, f"{input_path.stem}{suffix}")
    return None


def _start_pdf_conversion(body: dict, data: dict) -> Started:
    if not data.get("path"):
        raise ToolError("No path prepared")

    operation = data["operation"]
    if operation not in PdfConversionWorker.OPERATIONS:
        raise ToolError(f"Unknown operation: {operation}")

    input_path = Path(data["path"])
    if operation in _PDF_SINGLE_FILE_ONLY and data["mode"] != "file":
        raise ToolError("This operation requires one PDF file.")

    extract_page_spec = str(body.get("extract_page_spec", "")).strip()
    if operation == "extract_pages" and not extract_page_spec:
        raise ToolError("Page selection is required.")

    split_output_type = str(body.get("split_output_type", "pdfs"))
    error_base = input_path if input_path.is_dir() else input_path.parent
    errors = _make_error_folder(error_base, "pdf-conversion")
    output_root = _pdf_output_root(operation, input_path, split_output_type)
    return Started(
        worker=PdfConversionWorker(
            selection_mode=data["mode"],
            input_path=input_path,
            operation=operation,
            output_root=output_root,
            reduce_size_enabled=bool(body.get("reduce_size", True)),
            compression_profile_key=str(
                body.get("compression_profile", DEFAULT_PROFILE_KEY)
            ),
            split_output_type=split_output_type,
            extract_page_spec=extract_page_spec,
            remove_extracted_pages=bool(body.get("write_remaining_pages", False)),
            extract_removal_mode="safe",
            pdfa_profile_key=str(body.get("pdfa_profile", DEFAULT_PDFA_PROFILE_KEY)),
        ),
        input_folder=input_path,
        error_folder=errors,
        output_folder=output_root,
    )


def _statuses_pdf_conversion(body: dict) -> list:
    return get_pdf_conversion_dependency_statuses(
        operation=body.get("operation", "reduce_size")
    )


def _check_pdf_conversion(body: dict) -> tuple:
    return check_pdf_conversion_dependencies(
        body.get("operation", "reduce_size")
    )


# ── The registry ───────────────────────────────────────────────────────────

TOOL_SPECS: dict[str, ToolSpec] = {
    spec.id: spec
    for spec in (
        ToolSpec(
            id="auto_crop",
            display_name="Auto Crop",
            prepare=_prepare_image_folder,
            start=_start_auto_crop,
            statuses=_statuses_by_key("auto_crop"),
            check=_check_by_key("auto_crop"),
        ),
        ToolSpec(
            id="straighten_images",
            display_name="Straighten Images",
            prepare=_prepare_image_folder,
            start=_start_straighten,
            statuses=_statuses_by_key("straighten_images"),
            check=_check_by_key("straighten_images"),
        ),
        ToolSpec(
            id="merge_tiffs",
            display_name="Merge TIFF Files",
            prepare=_prepare_merge_tiffs,
            start=_start_merge_tiffs,
            statuses=_statuses_by_key("merge_tiffs"),
            check=_check_by_key("merge_tiffs"),
        ),
        ToolSpec(
            id="split_tiffs",
            display_name="Split Multi-Page TIFFs",
            prepare=_prepare_split_tiffs,
            start=_start_split_tiffs,
            statuses=_statuses_by_key("split_tiffs"),
            check=_check_by_key("split_tiffs"),
        ),
        ToolSpec(
            id="add_border",
            display_name="Add Border",
            prepare=_prepare_image_folder,
            start=_start_add_border,
            statuses=_statuses_by_key("add_border"),
            check=_check_by_key("add_border"),
        ),
        ToolSpec(
            id="ocr_pdf",
            display_name="OCR to PDF",
            prepare=_prepare_ocr_pdf,
            start=_start_ocr_pdf,
            statuses=lambda _body: get_ocr_dependency_statuses(),
            check=_check_ocr_pdf,
        ),
        ToolSpec(
            id="pdf_conversion",
            display_name="PDF Conversion",
            prepare=_prepare_pdf_conversion,
            start=_start_pdf_conversion,
            statuses=_statuses_pdf_conversion,
            check=_check_pdf_conversion,
        ),
    )
}

TOOL_IDS: tuple[str, ...] = tuple(TOOL_SPECS)


def get_spec(tool_id: str) -> ToolSpec:
    """Look up a tool. Raises KeyError for an unknown id."""
    return TOOL_SPECS[tool_id]
