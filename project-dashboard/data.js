window.DPA_DASHBOARD_DATA = {
  "project": {
    "name": "DPA Image Toolkit",
    "tagline": "Desktop toolkit for archival image cleanup and TIFF workflow management",
    "version": "1.0",
    "status": "Functional and actively refined",
    "summary": "A Windows-first desktop toolkit for archival imaging workflows. The app combines Auto Crop, Merge TIFFs, Split TIFFs, and Add Border in one GUI built with CustomTkinter."
  },
  "highlights": [
    {
      "label": "Tools",
      "value": "4",
      "detail": "Auto Crop, Merge TIFFs, Split TIFFs, Add Border"
    },
    {
      "label": "Primary Stack",
      "value": "Python",
      "detail": "CustomTkinter + Pillow + OpenCV"
    },
    {
      "label": "Target Use",
      "value": "Archival imaging",
      "detail": "Scanner cleanup, TIFF packaging, border prep"
    },
    {
      "label": "Current Focus",
      "value": "UI polish + verification",
      "detail": "Readability, workflow validation, packaging docs"
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
      "inputs": "Folder of TIFF files named like groupname_001.tif",
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
        "folder mode: selected_folder/extracted-pages/original_name/",
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
    }
  ],
  "workflow": [
    "Scan or collect images",
    "Run Auto Crop to remove scanner-created white space",
    "Optionally run Add Border to add consistent margins",
    "Merge correctly named TIFF page files into multi-page TIFFs",
    "Use Split TIFFs when existing multi-page TIFFs need to be broken apart"
  ],
  "architecture": [
    "main.py — entry point for the app",
    "dpa-image-toolkit.py — user-facing launcher wrapper",
    "image-toolkit.bat — Windows batch launcher",
    "gui/ — main window, panel controllers, theme system",
    "modules/auto_cropping/ — OpenCV and Pillow crop logic",
    "modules/tiff_combine/ — TIFF merge, grouping, validation",
    "modules/tiff_split/ — multi-page TIFF extraction",
    "modules/image_border/ — border generation logic",
    "utils/worker.py — background workers and progress callbacks"
  ],
  "languages": [
    {
      "name": "Python",
      "files": 39,
      "bytes": 211800,
      "percent": 73.8
    },
    {
      "name": "Markdown",
      "files": 11,
      "bytes": 53233,
      "percent": 18.5
    },
    {
      "name": "CSS",
      "files": 1,
      "bytes": 7177,
      "percent": 2.5
    },
    {
      "name": "HTML",
      "files": 1,
      "bytes": 6780,
      "percent": 2.4
    },
    {
      "name": "JavaScript",
      "files": 1,
      "bytes": 4930,
      "percent": 1.7
    },
    {
      "name": "Batchfile",
      "files": 5,
      "bytes": 2344,
      "percent": 0.8
    },
    {
      "name": "JSON",
      "files": 1,
      "bytes": 917,
      "percent": 0.3
    }
  ],
  "languageNote": "Language counts are based on tracked repository files and raw file sizes, not GitHub Linguist percentages.",
  "openIssues": [
    "Windows 10 / Windows 11 validation on the actual target environment",
    "High-DPI UI verification at 125%, 150%, and 200% scaling",
    "Replace script-style tests with real pytest coverage",
    "Per-page DPI preservation for TIFF merge",
    "Batch preview mode for Auto Crop"
  ],
  "futureIdeas": [
    "Configurable white threshold via UI slider",
    "Image straightening before crop",
    "Extract pages from existing multi-page TIFFs as a future split expansion",
    "PyInstaller standalone .exe build",
    "Drag-and-drop folder support"
  ],
  "limitations": [
    "Auto Crop assumes white or near-white scan backgrounds.",
    "TIFF merge currently writes merged DPI based on the first file in each group.",
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
      "name": "PROJECT.md",
      "path": "../PROJECT.md",
      "description": "Architecture, algorithms, design decisions, and limitations"
    },
    {
      "name": "TODO.md",
      "path": "../TODO.md",
      "description": "Open issues and future enhancements"
    },
    {
      "name": "CODEX_HANDOFF.md",
      "path": "../CODEX_HANDOFF.md",
      "description": "Agent handoff log and change context"
    }
  ],
  "sourceRepos": [
    "merged-repos/auto-cropping/",
    "merged-repos/tiff-combine/"
  ],
  "recentCommits": [
    "c08b0b4 Refine toolkit UI styling and layout",
    "4d361b0 Improve theme contrast and readability",
    "7bfb7ad Align home and sidebar navigation",
    "7bb8063 Add TIFF split and border tools",
    "61f1bcc Document scripts deployment layout",
    "210ea91 Flatten app layout for scripts deployment",
    "fca1d9e Fix runtime package imports for src launch",
    "14cf417 Fix main menu grid startup crash"
  ]
}
;
