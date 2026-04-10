window.DPA_DASHBOARD_DATA = {
  "project": {
    "name": "DPA Image Toolkit",
    "tagline": "Desktop toolkit for archival image cleanup and TIFF workflow management",
    "version": "1.0",
    "status": "Functional and actively refined",
    "summary": "A Windows-first desktop toolkit for archival imaging workflows. The app combines Auto Crop, Merge TIFFs, Split TIFFs, Add Border, and OCR to PDF in one CustomTkinter GUI, with deploy-ready copies kept under deploy/."
  },
  "highlights": [
    {
      "label": "Tools",
      "value": "5",
      "detail": "Auto Crop, Merge TIFFs, Split TIFFs, Add Border, OCR to PDF"
    },
    {
      "label": "Primary Stack",
      "value": "Python",
      "detail": "CustomTkinter + Pillow + OpenCV"
    },
    {
      "label": "Target Use",
      "value": "Archival imaging",
      "detail": "Scanner cleanup, TIFF packaging, grouped OCR PDF output"
    },
    {
      "label": "Current Focus",
      "value": "Repo cleanup + verification",
      "detail": "Windows workflow validation, doc accuracy, testing organization"
    }
  ],
  "tools": [
    {
      "name": "Auto Crop",
      "icon": "✂",
      "summary": "Detects content and crops away scanner-created white space while retaining all meaningful detected content in one crop region.",
      "inputs": "Folder of TIFF, JPEG, PNG, BMP, or GIF images",
      "outputs": [
        "input_folder/cropped/",
        "input_folder/errored-files/"
      ],
      "notes": [
        "Best results come from scans on white or near-white backgrounds.",
        "Uses a 253 threshold and unions meaningful contours before padding.",
        "Padding rule: 2.5% of image size, clamped to 15-100px."
      ]
    },
    {
      "name": "Merge TIFFs",
      "icon": "⊞",
      "summary": "Builds multi-page TIFFs from page files grouped by naming pattern.",
      "inputs": "Folder of TIFF files named like {name}_{group}_{###}.tif or .tiff",
      "outputs": [
        "input_folder/merged/",
        "input_folder/errored-files/"
      ],
      "notes": [
        "Valid groups are merged in numeric order.",
        "Mixed folders are allowed; unmatched TIFFs are skipped with warnings.",
        "Current merged DPI comes from the first valid file in each group."
      ]
    },
    {
      "name": "Split TIFFs",
      "icon": "⇵",
      "summary": "Extracts each page of a multi-page TIFF into an individual single-page TIFF.",
      "inputs": "Selected TIFF files or a folder containing TIFF files",
      "outputs": [
        "folder mode: selected_folder/extracted-pages/",
        "file mode: original_name_pages/"
      ],
      "notes": [
        "Single-page TIFFs are skipped automatically.",
        "Useful when archives receive multi-page masters that need page-level access.",
        "Preserves DPI when source metadata is available."
      ]
    },
    {
      "name": "Add Border",
      "icon": "▣",
      "summary": "Adds a white border around every image in a selected folder using the same spacing logic as Auto Crop.",
      "inputs": "Folder of supported image files",
      "outputs": [
        "input_folder/bordered/"
      ],
      "notes": [
        "Intended for workflows such as book scans or presentation-ready images.",
        "Leaves original images untouched.",
        "Uses the same 2.5% padding rule as Auto Crop."
      ]
    },
    {
      "name": "OCR to PDF",
      "icon": "⎙",
      "summary": "Groups scan files by trailing four-digit sequence and creates searchable PDFs in a PDFs subfolder.",
      "inputs": "Folder of supported scan images named like {name}_####.<extension>",
      "outputs": [
        "input_folder/PDFs/",
        "input_folder/errored-files/ocr-pdf/"
      ],
      "notes": [
        "Valid single files are still processed as one-page PDFs.",
        "Defaults to English OCR on the local Tesseract install.",
        "Can skip grouped PDFs when the OCR quality precheck flags a page."
      ]
    }
  ],
  "workflow": [
    "Scan or collect images",
    "Run Auto Crop to remove scanner-created white space",
    "Optionally run Add Border to add consistent margins",
    "Merge correctly named TIFF page files into multi-page TIFFs",
    "Use Split TIFFs when existing multi-page TIFFs need to be broken apart",
    "Use OCR to PDF to build searchable grouped PDFs from page-image folders"
  ],
  "architecture": [
    "main.py — entry point for the app",
    "dpa-image-toolkit.py — user-facing launcher wrapper",
    "image-toolkit.bat — Windows batch launcher",
    "gui/ — main window, panel controllers, shared dependency sidebar, theme system",
    "modules/auto_cropping/ — OpenCV and Pillow crop logic",
    "modules/tiff_combine/ — TIFF merge, grouping, validation",
    "modules/tiff_split/ — multi-page TIFF extraction",
    "modules/image_border/ — border generation logic",
    "modules/ocr_pdf/ — OCR grouping, quality checks, searchable PDF generation",
    "utils/worker.py — background workers, cancel flow, and progress callbacks",
    "deploy/ — synchronized Windows deployment bundle",
    "testing/ — per-tool generators, smoke tests, and local test scratch space"
  ],
  "languages": [
    {
      "name": "Python",
      "files": 64,
      "bytes": 564992,
      "percent": 92.2
    },
    {
      "name": "Markdown",
      "files": 5,
      "bytes": 10156,
      "percent": 1.7
    },
    {
      "name": "CSS",
      "files": 3,
      "bytes": 5344,
      "percent": 0.9
    },
    {
      "name": "HTML",
      "files": 3,
      "bytes": 5332,
      "percent": 0.9
    },
    {
      "name": "JavaScript",
      "files": 4,
      "bytes": 11794,
      "percent": 1.9
    },
    {
      "name": "Batchfile",
      "files": 4,
      "bytes": 7738,
      "percent": 1.3
    },
    {
      "name": "JSON",
      "files": 3,
      "bytes": 7080,
      "percent": 1.2
    }
  ],
  "languageNote": "Language counts are based on the current repo tree excluding .git and testing/, using raw file sizes rather than GitHub Linguist percentages.",
  "openIssues": [
    "Continue Windows 10 / Windows 11 workflow validation on the target environment",
    "High-DPI UI verification at 125%, 150%, and 200% scaling",
    "Strengthen automated test coverage for crop, TIFF grouping, and OCR grouping",
    "Keep dashboard and docs aligned with shipped behavior",
    "Per-page DPI preservation for TIFF merge",
    "Batch preview mode for Auto Crop"
  ],
  "futureIdeas": [
    "Future multi-language OCR option once install/support workflow is settled",
    "Configurable white threshold via UI slider",
    "Image straightening before crop",
    "Handwriting-focused HCR tool investigation",
    "PyInstaller standalone .exe build",
    "Drag-and-drop folder support"
  ],
  "limitations": [
    "Auto Crop assumes white or near-white scan backgrounds.",
    "TIFF merge currently writes merged DPI based on the first file in each group.",
    "OCR to PDF depends on a local Tesseract install and English language data.",
    "No in-app undo is available yet.",
    "The batch launcher is Windows-specific even though the Python app can run cross-platform."
  ],
  "dependencies": [
    "customtkinter>=5.0.0",
    "Pillow>=10.0.0",
    "opencv-python>=4.8.0",
    "numpy>=1.24.0"
  ],
  "docs": [
    {
      "name": "README.md",
      "path": "../README.md",
      "description": "Setup, usage, workflow, and deployment notes"
    },
    {
      "name": "TODO.md",
      "path": "../TODO.md",
      "description": "Open issues and future enhancements"
    },
    {
      "name": "deploy/README.md",
      "path": "../deploy/README.md",
      "description": "Windows Scripts deployment notes"
    },
    {
      "name": "project-dashboard/data.json",
      "path": "./data.json",
      "description": "Dashboard content model for the HTML project view"
    }
  ],
  "sourceRepos": [
    "gui/",
    "modules/",
    "utils/",
    "deploy/",
    "testing/"
  ],
  "recentCommits": [
    "02c9206 Update naming rules and window placement",
    "d85876b Polish tool controls and dependency sidebars",
    "1a09ef9 Add shared dependency panels across tools",
    "2ae5e57 Refine OCR batch PDF grouping flow",
    "6c86c86 Stack sidebar app title vertically",
    "a1ff2ec Fix Windows TIFF group double counting",
    "16fc2be Refine TIFF group verification preview",
    "4138a26 Update app window, title, and disabled button styling"
  ]
}
;
